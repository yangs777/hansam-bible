"""Pick the next batch of verses: canonical order, skipping published and held verses.

2026-11-27: Gen 8:7 was blocked on critical-apparatus access and the hourly automation kept
re-selecting 8:6-10, so nothing was adopted. Held verses (automation/held-verses.json) are
skipped and the batch continues with the following verses of the same chapter. A batch never
crosses a chapter boundary. Model-free and read-only.

  python tools/next_scope.py [--count 5]
"""
import argparse
import json
import pathlib
import xml.etree.ElementTree as ET

R = pathlib.Path(__file__).resolve().parents[1]
OSIS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'
BOOKS = ['Gen', 'Exod', 'Lev', 'Num', 'Deut']


def published_ids(editorial):
    return {v['source'] for p in editorial['passages'] for v in p['verses']}


def held_ids(held):
    return {v['id'] for v in held.get('verses', []) if v.get('status', 'held') == 'held'}


def canonical_ids(books=BOOKS, cache=None, commit=None):
    """Verse IDs in order from the pinned WLC cache; falls back to automation/cloud-queue.json."""
    cache = pathlib.Path(cache or R/'private/upstream_cache')
    commit = commit or json.loads((R/'config.json').read_text(encoding='utf-8'))['source_commit']
    ids = []
    for book in books:
        path = cache/(commit+'-'+book+'.xml')
        if not path.exists():
            continue
        ids += [v.get('osisID') for v in ET.fromstring(path.read_bytes()).iter(OSIS+'verse')]
    if ids:
        return ids
    queue = json.loads((R/'automation/cloud-queue.json').read_text(encoding='utf-8'))
    return [v['id'] for job in queue for v in job['verses']]


def next_scope(order, published, held, count=5):
    remaining = [i for i in order if i not in published]
    skipped = []
    scope = []
    for verse in remaining:
        chapter = verse.rsplit('.', 1)[0]
        if scope and chapter != scope[0].rsplit('.', 1)[0]:
            break
        if verse in held:
            skipped.append(verse)
            continue
        scope.append(verse)
        if len(scope) == count:
            break
    return {'scope': scope, 'skipped_held': [s for s in skipped if not scope or s.rsplit('.', 1)[0] == scope[0].rsplit('.', 1)[0]],
            'note': 'Held verses stay unadopted with their records; the passage may show a gap until they are released.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--count', type=int, default=5)
    args = ap.parse_args()
    editorial = json.loads((R/'data/editorial.json').read_text(encoding='utf-8'))
    held_path = R/'automation/held-verses.json'
    held = json.loads(held_path.read_text(encoding='utf-8')) if held_path.exists() else {}
    result = next_scope(canonical_ids(), published_ids(editorial), held_ids(held), max(1, min(5, args.count)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
