"""Durable public update records. Never import private account or quota snapshots."""
import copy, json, pathlib, re
from datetime import datetime, timezone

def read_log(root):
    path=pathlib.Path(root)/'data/updates.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version':1,'entries':[]}

def timestamp(value):
    moment=datetime.fromisoformat(value.replace('Z','+00:00'))
    if moment.tzinfo is None:raise ValueError('Update timestamps need an explicit timezone')
    return moment

def append_entry(root, entry):
    log=read_log(root);entry=copy.deepcopy(entry)
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*',entry['id']):raise ValueError('Invalid update ID')
    timestamp(entry['recorded_at'])
    if not entry.get('title_ko') or not entry.get('summary_ko'):raise ValueError('Explain the public change')
    for old in log['entries']:
        if old['id']==entry['id']:
            if old!=entry:raise ValueError('Existing update records are immutable; append a correction')
            return False
    log['entries'].append(entry)
    log['entries'].sort(key=lambda x:(timestamp(x['recorded_at']),x['id']),reverse=True)
    path=pathlib.Path(root)/'data/updates.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return True

def edition_entry(version, previous, passages, decisions, root, now=None):
    old={v['id']:v for v in previous};current=[v for p in passages for v in p['verses']]
    added=[v for v in current if v['id'] not in old]
    changed=[v for v in current if v['id'] in old and any(v[k]!=old[v['id']][k] for k in ('ko','en','es'))]
    models=set()
    for f in (pathlib.Path(root)/'data/model-reviews'/('v'+version)).glob('*.round1.json'):
        item=json.loads(f.read_text(encoding='utf-8'));models.add(item['model'])
    return {'id':'edition-'+version,'kind':'edition','version':version,
            'recorded_at':(now or datetime.now(timezone.utc)).isoformat(),
            'time_basis':'edition_adopted_at','title_ko':f'번역판 v{version} · {len(added)}절 추가, {len(changed)}절 수정',
            'summary_ko':[f'현재 선택 본문 {len(current)}절 · 한국어·영어·스페인어 {len(current)*3}개 번역.',
                          '이전 판본과 실제 모델 제안·의견을 보존합니다. 이 시각은 판본 채택 기록이며 실제 배포 완료 시각과 구분합니다.'],
            'total_verses':len(current),'translation_count':len(current)*3,
            'added_references':[v['source'] for v in added],
            'revised_ids':[v['id'] for v in changed],'models':sorted(models),
            'links':[{'label':'현재 본문','url':'/read/'},{'label':'판본 데이터','url':f'/data/releases/v{version}.json'}]}
