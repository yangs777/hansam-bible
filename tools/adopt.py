"""Adopt a new current edition while preserving the superseded verse dataset."""
import argparse, copy, json, pathlib, re

R = pathlib.Path(__file__).resolve().parents[1]
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def adopt(decision_file, version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise ValueError('Use a numeric edition version')
    config = read(R/'config.json'); editorial = read(R/'data/editorial.json')
    decisions = read(pathlib.Path(decision_file)); old_version = config['version']
    if version == old_version: raise ValueError('Use a NEW version; never overwrite an edition in place')
    if tuple(map(int,version.split('.'))) < tuple(map(int,old_version.split('.'))): raise ValueError('Version must increase')
    if (R/f'data/releases/v{version}.json').exists(): raise ValueError('Version already archived')
    if decisions['version'] != version: raise ValueError('Decision version mismatch')
    selected = {d['id']: d for d in decisions['verses']}
    if len(selected)!=len(decisions['verses']): raise ValueError('Duplicate verse decisions')
    previous_verses = [v for p in editorial['passages'] for v in p['verses']]
    additions=decisions.get('new_passages',[])
    proposed_passages=additions+copy.deepcopy(editorial['passages'])
    updated=set()
    for update in decisions.get('passage_updates',[]):
        if set(update)-{'id','verses','reference','title','subtitle','intro','notes','glosses'}:
            raise ValueError('Unsupported passage update field; IDs and URLs must remain stable')
        matches=[p for p in proposed_passages if p['id']==update['id']]
        if len(matches)!=1 or update['id'] in updated:
            raise ValueError('Passage update must target one existing passage exactly once')
        updated.add(update['id']); passage=matches[0]
        passage['verses'].extend(update.get('verses',[]))
        passage.update({k:v for k,v in update.items() if k not in ('id','verses')})
    verses = [v for p in proposed_passages for v in p['verses']]
    if len({v['id'] for v in verses})!=len(verses): raise ValueError('Duplicate existing/new verse IDs')
    if len(selected) != len(verses) or set(selected) != {v['id'] for v in verses}:
        raise ValueError('Supply exactly one selection for every current verse')
    for d in selected.values():
        if d['version']!=version: raise ValueError('Per-verse version mismatch')
        if set(d['translations']) != {'ko','en','es'} or any(not x.strip() for x in d['translations'].values()):
            raise ValueError('A current best translation is required in every language')
        if not d.get('reason_ko') or not d.get('basis'): raise ValueError('Decision needs reason and basis')
    current = read(R/'dist/data/hansam-bible.json')
    if current['metadata']['version'] != old_version: raise ValueError('Build the current version before archiving it')
    by_id = {v['id']: v for v in previous_verses}
    if {r['id'] for r in current['records']} != set(by_id) or len(current['records']) != len(by_id):
        raise ValueError('Published dataset must contain every previous verse exactly once')
    for record in current['records']:
        if record['translations'] != {k:by_id[record['id']][k] for k in ('ko','en','es')}:
            raise ValueError('Published dataset differs from current source; archive would be unreliable')
    archive = R/f'data/releases/v{old_version}.json'
    if archive.exists():
        if read(archive)['records'] != current['records']: raise ValueError('Archived edition is immutable')
    else:
        published=R/f'dist/data/releases/v{old_version}.json'
        if published.exists():
            snapshot=read(published)
            if snapshot['version']!=old_version or snapshot['records']!=current['records']:
                raise ValueError('Published version snapshot differs from current dataset')
            archive.parent.mkdir(parents=True,exist_ok=True)
            archive.write_bytes(published.read_bytes())
        else:
            save(archive, {'version':old_version,'title':config['title'],'state':'superseded',**current})
    editorial['passages']=proposed_passages
    for p in editorial['passages']:
        for v in p['verses']:
            d = selected[v['id']]
            v.update(d['translations']); v['selection_status'] = 'current_best_provisional'
            v['selection_version'] = version; v['source_basis'] = d['basis']
        if len(p['verses']) == 1:
            p['basis'] = selected[p['verses'][0]['id']]['basis']
    config['version'] = version
    save(R/'data/editorial.json',editorial); save(R/'config.json',config)
    save(R/'data/decisions.json', {k:v for k,v in decisions.items() if k not in ('new_passages','passage_updates')})
    citation=R/'CITATION.cff'
    if citation.exists():
        citation.write_text(re.sub(r'^version: .+$','version: '+version,citation.read_text(encoding='utf-8'),flags=re.M),encoding='utf-8')
    package=R/'package.json'
    if package.exists():
        metadata=read(package); metadata['version']=version; save(package,metadata)
    print(json.dumps({'previous':old_version,'current':version,'archived':str(archive),'selected_verses':len(verses)}))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decisions'); parser.add_argument('--version',required=True)
    args=parser.parse_args(); adopt(args.decisions,args.version)
