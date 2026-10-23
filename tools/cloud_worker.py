"""Bounded cloud draft worker. No secret, verified credit or durable ledger => zero API calls."""
import argparse, datetime as dt, hashlib, json, math, os, pathlib, subprocess, time, urllib.request
R=pathlib.Path(__file__).resolve().parents[1]
UTC=dt.timezone.utc
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');temp.replace(p)
def parse_time(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def guard(policy,now,key_present):
    if not policy.get('enabled'):return 'credit policy disabled; balance and expiry unverified'
    if not key_present:return 'no project API secret'
    if policy.get('new_cash_budget_usd')!=0 or not policy.get('credit_isolated_from_paid_balance'):return 'zero-new-cash isolation not verified'
    try:
        checked=parse_time(policy['balance_verified_at']);expiry=parse_time(policy['credit_expires_at'])
        if checked>now or now-checked>dt.timedelta(hours=policy['verification_max_age_hours']):return 'balance verification stale'
        if expiry-now<=dt.timedelta(hours=policy['expiry_buffer_hours']):return 'expiry buffer reached'
        if not 0<float(policy['project_cap_usd'])<=float(policy['verified_remaining_usd']):return 'invalid verified credit cap'
        if policy['model']!='claude-sonnet-4-6' or (policy['input_usd_per_million'],policy['output_usd_per_million'])!=(3,15):return 'model/pricing requires review'
    except (TypeError,ValueError,KeyError):return 'incomplete verified credit policy'
    return None
def reserve_cost(prompt,policy):
    # UTF-8 bytes plus 4096 exceed expected prompt tokenization; no tools/cache/thinking enabled.
    return math.ceil(((len(prompt.encode('utf-8'))+4096)*policy['input_usd_per_million']+policy['max_output_tokens']*policy['output_usd_per_million'])/1000)/1000
def persist(state,ledger,message,git_enabled):
    save(state/'ledger.json',ledger)
    if git_enabled:
        for args in [['add','--','ledger.json','drafts'],['commit','--allow-empty','-m',message],['push','origin','HEAD:bible-cloud-state']]:
            subprocess.run(['git','-C',str(state),*args],check=True,capture_output=True)
def run(policy,state,execute=False,git_enabled=False):
    now=dt.datetime.now(UTC);reason=guard(policy,now,bool(os.getenv('ANTHROPIC_API_KEY')))
    if reason:return {'status':'skipped','reason':reason,'api_calls':0}
    if not execute:return {'status':'ready_dry_run','api_calls':0}
    if not git_enabled:raise ValueError('Paid execution requires remote durable ledger before every request')
    state.mkdir(parents=True,exist_ok=True);(state/'drafts').mkdir(exist_ok=True)
    (state/'drafts/.gitkeep').touch()
    ledger=read(state/'ledger.json') if (state/'ledger.json').exists() else {'jobs':{},'reserved_usd':0}
    queue=read(R/'automation/cloud-queue.json');calls=0;started=time.monotonic()
    cap=float(policy['project_cap_usd']);days=max(1,(parse_time(policy['credit_expires_at'])-now).total_seconds()/86400)
    # Pace useful work across days. Reserve remains charged in our ledger even on failure.
    daily=(cap-ledger['reserved_usd'])/days
    day=now.date().isoformat();spent_today=sum(j['reserved_usd'] for j in ledger['jobs'].values() if j['reserved_at'].startswith(day))
    adopted={v['source'] for p in read(R/'data/editorial.json')['passages'] for v in p['verses']}
    claimed={v for j in ledger['jobs'].values() for v in j.get('verse_ids',[])}
    for job in queue:
        if calls>=policy['max_jobs_per_run'] or time.monotonic()-started+240>policy.get('run_budget_seconds',2800):break
        job={**job,'verses':[v for v in job['verses'] if v['id'] not in adopted|claimed]}
        if not job['verses']:continue
        prompt=json.dumps(job,ensure_ascii=False)+'\nTranslate this pinned Hebrew into fresh Korean, English and modern Spanish. JSON only: {verses:[{id,translations:{ko,en,es},reason_ko,counterargument_ko,current_opinion_ko}]}. State alternatives, do not invent witness checks. Draft only.'
        identity=hashlib.sha256((policy['model']+'\n'+prompt).encode()).hexdigest()
        if identity in ledger['jobs']:continue
        cost=reserve_cost(prompt,policy)
        if ledger['reserved_usd']+cost>cap or spent_today+cost>daily:break
        if guard(policy,dt.datetime.now(UTC),True):break
        entry={'source_job':job['id'],'verse_ids':[v['id'] for v in job['verses']],'reserved_at':now.isoformat(),'reserved_usd':cost,'status':'reserved','model':policy['model']}
        ledger['jobs'][identity]=entry;ledger['reserved_usd']=round(ledger['reserved_usd']+cost,6)
        persist(state,ledger,'Reserve Bible draft '+identity[:12],True) # push must succeed BEFORE API
        claimed.update(entry['verse_ids'])
        body={'model':policy['model'],'max_tokens':policy['max_output_tokens'],'messages':[{'role':'user','content':prompt}]}
        request=urllib.request.Request('https://api.anthropic.com/v1/messages',data=json.dumps(body).encode(),headers={'x-api-key':os.environ['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01','content-type':'application/json'})
        calls+=1;spent_today+=cost
        try:
            with urllib.request.urlopen(request,timeout=240) as response:result=json.load(response)
            save(state/'drafts'/(identity+'.json'),{'job':job,'response':result,'state':'unadopted_model_draft','author':'Hansam Yang','no_consensus_claim':True})
            entry['status']='received';entry['usage']=result.get('usage',{});entry['actual_model']=result.get('model');entry['stop_reason']=result.get('stop_reason')
            if result.get('stop_reason')!='end_turn':entry['status']='needs_manual_review_truncated_or_other_stop'
        except Exception as exc:
            entry['status']='uncertain_no_automatic_retry';entry['error_type']=type(exc).__name__ # never emit headers/body/secret
        persist(state,ledger,'Record Bible draft '+identity[:12],True)
    return {'status':'finished','api_calls':calls,'reserved_usd':ledger['reserved_usd'],'daily_target_usd':round(daily,3),'drafts_require_editorial_review':True}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=pathlib.Path,default=R/'private/cloud-state');p.add_argument('--execute',action='store_true');p.add_argument('--git-ledger',action='store_true');a=p.parse_args()
    print(json.dumps(run(read(R/'automation/credit-policy.json'),a.state,a.execute,a.git_ledger),ensure_ascii=False))
