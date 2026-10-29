"""Prepare one priority hard-review unit; preserve raw pinned Hebrew markup."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request
import uuid
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parents[1]
NS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def git(*args):
    return subprocess.check_output(['git', *args], cwd=R, text=True, encoding='utf-8')


def claimed_units():
    claimed = set()
    manifests = []
    for path in (R / 'automation/hard-review-runs').glob('*.json'):
        manifests.append(read(path))
    refs = git('for-each-ref', '--format=%(refname)', 'refs/remotes/').splitlines()
    for ref in refs:
        if '/claude/' not in ref:
            continue
        paths = git('ls-tree', '-r', '--name-only', ref, '--', 'automation/hard-review-runs/').splitlines()
        for path in paths:
            manifests.append(json.loads(git('show', f'{ref}:{path}')))
    resolved = {m['run_id'] for m in manifests if m['status'] != 'claimed_pending_review'}
    now = dt.datetime.now(dt.timezone.utc)
    active = []
    for manifest in manifests:
        claimed.add(manifest['unit_id'])
        created = dt.datetime.fromisoformat(manifest['created_at'])
        if created.tzinfo is None:
            raise SystemExit('Claim timestamp lacks timezone')
        if manifest['run_id'] not in resolved and now - created < dt.timedelta(minutes=60):
            active.append(manifest['run_id'])
    return claimed, sorted(set(active))


def prepare(check_only=False, standalone_cloud=False):
    policy = read(R / 'automation/claude-cloud-policy.json')
    now = dt.datetime.now(dt.timezone.utc)
    if not policy['enabled'] or now >= dt.datetime.fromisoformat(policy['stop_new_translation_at']):
        raise SystemExit('Hard-review policy disabled or past stop time')
    if policy['new_cash_budget_usd'] != 0:
        raise SystemExit('Unexpected cash policy')
    if policy.get('require_standalone_cloud_marker') and not standalone_cloud:
        raise SystemExit('Standalone cloud launch required; Routine/Project/local execution is not authorized')
    queue = read(R / 'automation/hard-review-queue.json')['units']
    ids = [unit['id'] for unit in queue]
    if len(ids) != len(set(ids)):
        raise SystemExit('Duplicate review unit IDs')
    claimed, active = claimed_units()
    if active:
        print(json.dumps({'status': 'another_review_in_progress', 'run_ids': active}))
        return
    unit = next((u for u in queue if u['id'] not in claimed), None)
    if unit is None:
        print(json.dumps({'status': 'queue_exhausted'}))
        return
    refs = unit['refs']
    if not 1 <= len(refs) <= 20 or len(refs) != len(set(refs)):
        raise SystemExit('Invalid target coverage')
    commit = read(R / 'config.json')['source_commit']
    verses = []
    cache = R / 'private/upstream_cache'
    cache.mkdir(parents=True, exist_ok=True)
    for book in dict.fromkeys(ref.split('.')[0] for ref in refs):
        url = f'https://raw.githubusercontent.com/openscriptures/morphhb/{commit}/wlc/{book}.xml'
        path = cache / f'{commit}-{book}.xml'
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(url, timeout=45).read())
        raw = path.read_bytes()
        source = ET.fromstring(raw)
        index = {v.get('osisID'): v for v in source.iter(NS + 'verse')}
        source_xml = raw.decode('utf-8-sig')
        for ref in refs:
            if not ref.startswith(book + '.'):
                continue
            if ref not in index:
                raise SystemExit(f'Missing source verse: {ref}')
            # Pinned WLC uses container verses. Preserve verbatim comments,
            # markup and whitespace rather than reserializing ElementTree.
            pattern = r'<verse\b[^>]*\bosisID=[\"\x27]' + re.escape(ref) + r'[\"\x27][^>]*>(.*?)</verse\s*>'
            matches = list(re.finditer(pattern, source_xml, re.DOTALL))
            if len(matches) != 1 or not list(index[ref]):
                raise SystemExit(f'Unsupported/missing container verse: {ref}')
            fragment = matches[0].group(0)
            verses.append({'id': ref, 'raw_xml': fragment,
                           'raw_xml_format': 'verbatim UTF-8 fragment from pinned WLC container verse',
                           'namespace_context': {'default': NS[1:-1]},
                           'fragment_sha256': hashlib.sha256(fragment.encode('utf-8')).hexdigest(),
                           'source_url': url, 'source_commit': commit,
                           'source_file_sha256': hashlib.sha256(raw).hexdigest()})
    selected = {v['source']: v for p in read(R / 'data/editorial.json')['passages'] for v in p['verses']}
    run_id = now.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    packet_path = f'automation/hard-review-packets/{run_id}.json'
    packet = {'state': 'source_input_only', 'run_id': run_id, 'unit': unit,
              'source_verses': verses, 'current_selected': [selected[r] for r in refs if r in selected],
              'rights': {'text': 'WLC public domain', 'morphology': 'OSHB CC BY 4.0',
                         'credit': 'https://github.com/openscriptures/morphhb'},
              'warning': 'Preserve raw markup. No complete manuscript collation is asserted.'}
    if not check_only:
        manifest = {'run_id': run_id, 'unit_id': unit['id'], 'verse_ids': refs,
                    'created_at': now.isoformat(), 'status': 'claimed_pending_review',
                    'source_packet': packet_path, 'state': 'unadopted_model_review',
                    'execution_path_declared': 'standalone_cloud' if standalone_cloud else 'legacy_unspecified',
                    'execution_marker_is_billing_proof': False}
        for rel, value in [(packet_path, packet), (f'automation/hard-review-runs/{run_id}.json', manifest)]:
            dest = R / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'validated' if check_only else 'claim_prepared', 'unit_id': unit['id'],
                      'verse_ids': refs, 'source_packet': None if check_only else packet_path}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate first pending unit without claiming it')
    parser.add_argument('--standalone-cloud', action='store_true', help='Caller marker for a controller-launched standalone cloud session; not proof of billing')
    args = parser.parse_args()
    prepare(args.check, args.standalone_cloud)
