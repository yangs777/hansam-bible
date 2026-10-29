"""Prepare native Claude cloud input without paid API calls or fabricated model results."""
import argparse,datetime as dt,json,pathlib,subprocess,uuid
R=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def guard(policy,now):
    deadline=dt.datetime.fromisoformat(policy['stop_new_translation_at'])
    return policy.get('enabled') is True and policy.get('new_cash_budget_usd')==0 and now<deadline
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True,encoding='utf-8').strip()
def claimed_sources():
    ids=set();paths=set((R/'automation/cloud-runs').glob('*.json'))
    for p in paths:ids.update(read(p).get('verse_ids',[]))
    refs=git('for-each-ref','--format=%(refname)','refs/remotes/origin/claude','refs/remotes/github/claude').splitlines()
    for ref in refs:
        for name in git('ls-tree','-r','--name-only',ref,'--','automation/cloud-runs/').splitlines():
            if not name.endswith('.json'):continue
            item=json.loads(git('show',ref+':'+name));ids.update(item.get('verse_ids',[]))
    return ids
def prepare(limit):
    policy=read(R/'automation/claude-cloud-policy.json');now=dt.datetime.now(dt.timezone.utc)
    if not guard(policy,now):return {'status':'stopped_by_date_or_policy','paid_api_calls':0}
    if policy.get('work_mode') == 'difficult_passage_review':
        return {'status':'bulk_drafting_paused_use_claude_hard_review','paid_api_calls':0}
    if not 1<=limit<=policy['initial_verse_limit_per_run']:raise ValueError('Batch exceeds configured limit')
    adopted={v['source'] for p in read(R/'data/editorial.json')['passages'] for v in p['verses']}
    claimed=claimed_sources();selected=[]
    for job in read(R/'automation/cloud-queue.json'):
        for verse in job['verses']:
            if verse['id'] in adopted|claimed:continue
            selected.append({**verse,'source_url':job['source_url'],'source_file_sha256':job['source_file_sha256'],'source_commit':job['source_commit'],'rights':job['rights']})
            if len(selected)==limit:break
        if len(selected)==limit:break
    if not selected:return {'status':'no_unclaimed_sources','paid_api_calls':0}
    run_id=now.strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    packet='automation/cloud-packets/'+run_id+'.json';manifest='automation/cloud-runs/'+run_id+'.json'
    contents={packet:{'run_id':run_id,'state':'source_input_only','verses':selected},manifest:{'run_id':run_id,'created_at':now.isoformat(),'status':'claimed_pending_generation','verse_ids':[v['id'] for v in selected],'source_packet':packet,'provider':'Claude Code native cloud','source_claim_note':'Push assigned branch before generation; includes visible previous claims, not an atomic lock'}}
    for name,item in contents.items():
        p=R/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return {'status':'prepared','run_id':run_id,'verse_count':len(selected),'source_packet':packet,'manifest':manifest,'first_id':selected[0]['id'],'last_id':selected[-1]['id'],'next_action':'commit/push assigned branch before drafting','paid_api_calls':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=100);a=p.parse_args();print(json.dumps(prepare(a.limit),ensure_ascii=False))
