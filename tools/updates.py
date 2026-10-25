"""Static update timeline with an optional read-only public deployment-status check."""
import html, json, pathlib, xml.etree.ElementTree as ET
from datetime import timedelta, timezone
from update_log import read_log, timestamp

R=pathlib.Path(__file__).resolve().parents[1]
KST=timezone(timedelta(hours=9))

def build(page,write,config,passages):
    log=read_log(R)
    entries=sorted(log['entries'],key=lambda e:(timestamp(e['recorded_at']),e['id']),reverse=True)
    if not any(e.get('version')==config['version'] for e in entries):
        raise ValueError('Current edition needs an update record before publication')
    esc=lambda s:html.escape(str(s),quote=True)
    count=sum(len(p['verses']) for p in passages)
    repo=config['repository'];actions=repo+'/actions/workflows/pages.yml'
    rows=[]
    labels={'github_release_published_at':'릴리스 공개','git_commit_at':'변경 기록','edition_adopted_at':'판본 채택','change_recorded_at':'변경 기록'}
    for e in entries:
        time=timestamp(e['recorded_at']).astimezone(KST)
        links=[]
        for link in e.get('links',[]):
            url=link['url']
            if not (url.startswith('/') and not url.startswith('//') or url.startswith(repo+'/')):
                raise ValueError('Update links must stay in the project or its repository')
            links.append(f'<a href="{esc(url)}">{esc(link["label"])} ↗</a>')
        models='<p class="fine">검토 모델: '+esc(' · '.join(e['models']))+'</p>' if e.get('models') else ''
        rows.append(f'''<article class="update-entry" id="{esc(e['id'])}"><div class="update-meta"><span>{'번역판' if e['kind']=='edition' else '사이트'}</span><time datetime="{esc(e['recorded_at'])}">{time.strftime('%Y.%m.%d %H:%M')} KST</time><small>{labels[e['time_basis']]}</small></div><div><h3>{esc(e['title_ko'])}</h3><ul>{''.join('<li>'+esc(s)+'</li>' for s in e['summary_ko'])}</ul>{models}<p class="update-links">{' · '.join(links)}</p></div></article>''')
    stages=['원문·출처 확인','GPT·Gemini 비교','난구 추가 검토','현재 최선 번역 채택','자동 검사','판본 공개']
    body=f'''<section class="updates-page"><p class="eyebrow">PROJECT JOURNAL / ORIGINAL BIBLE</p><div class="updates-heading"><div><h1>업데이트 기록</h1><p class="lead">언제, 무엇이 바뀌었는지.<br>번역이 어떤 검토를 거쳐 공개되는지 기록합니다.</p></div><div class="updates-current"><span>현재 공개 번역판</span><strong>v{esc(config['version'])}</strong><p>{count}절 · 3개 언어 · {count*3}개 번역</p><a href="/read/">본문 읽기·대조 ↗</a></div></div>
<section class="update-workflow" aria-labelledby="workflow-title"><h2 id="workflow-title">작업은 이렇게 진행됩니다</h2><ol>{''.join('<li>'+esc(s)+'</li>' for s in stages)}</ol><p>자동 작업은 사용량과 작업 시간 조건이 맞을 때 5절씩 진행합니다. 검토 전 초안과 공개 채택문을 구분하며, 더 나은 근거가 나오면 이전판을 남기고 새 판본으로 바꿉니다. 모델 검토와 별개로 인간 전문가 검수·사본 전면 대조는 진행 과제로 남아 있습니다.</p></section>
<section class="deployment-panel" aria-labelledby="deployment-title"><h2 id="deployment-title">최근 공개 작업</h2><p id="deployment-status" role="status">공개 기록을 불러오는 중입니다. 아래 업데이트 이력은 바로 읽을 수 있습니다.</p><p><a id="deployment-link" href="{esc(actions)}" target="_blank" rel="noopener">검사·배포 기록 확인 ↗</a></p><p class="fine">페이지를 열 때 공개 저장소의 검사·배포 상태를 한 번 조회합니다. 번역 초안 작성 여부와 모든 작업의 실시간 진행률을 뜻하지 않습니다. 조회가 제한돼도 아래 이력은 유지됩니다.</p><noscript>실시간 상태는 위 검사·배포 기록 링크에서 확인할 수 있습니다.</noscript></section>
<div class="update-list-heading"><h2>전체 업데이트</h2><p><a href="/updates/feed.xml">RSS 구독 ↗</a> · <a href="/updates/feed.json">JSON 기록 ↗</a></p></div><p class="fine">시각은 한국 시간입니다. 과거 번역판은 GitHub 릴리스 공개 시각, 기능 변경은 저장소 변경 시각을 사용했습니다. 이후 판본의 채택 기록 시각과 실제 배포 완료 시각은 별도로 표시합니다.</p>{''.join(rows)}</section><script src="/assets/updates.js" defer></script>'''
    structured={'@context':'https://schema.org','@type':'CollectionPage','name':'원문성경 업데이트 기록','url':config['origin']+'/updates/','inLanguage':'ko','dateModified':entries[0]['recorded_at'],'author':{'@type':'Person','name':'Hansam Yang'}}
    page('/updates/','원문성경 업데이트 — 번역판·작업 진행 기록',body,lang='ko',structured=structured,description='원문성경의 새 번역, 모델 비교 검토, 판본 공개와 사이트 개선을 날짜별로 확인하세요. Hansam Yang의 공개 성경 연구 프로젝트.')
    exported=[{**e,'links':[{**link,'url':config['origin']+link['url'] if link['url'].startswith('/') else link['url']} for link in e.get('links',[])]} for e in entries]
    write('updates/feed.json',json.dumps({'schema_version':1,'home_page_url':config['origin']+'/updates/','current_version':config['version'],'total_verses':count,'translation_count':count*3,'timezone':'Asia/Seoul','entries':exported},ensure_ascii=False,indent=2)+'\n')
    rss=ET.Element('rss',version='2.0');channel=ET.SubElement(rss,'channel')
    for k,v in [('title','원문성경 업데이트'),('link',config['origin']+'/updates/'),('description','번역판과 사이트의 변경 기록'),('language','ko')]:ET.SubElement(channel,k).text=v
    from email.utils import format_datetime
    for e in entries:
        item=ET.SubElement(channel,'item');ET.SubElement(item,'title').text=e['title_ko'];link=config['origin']+'/updates/#'+e['id']
        ET.SubElement(item,'link').text=link;ET.SubElement(item,'guid',isPermaLink='true').text=link
        ET.SubElement(item,'pubDate').text=format_datetime(timestamp(e['recorded_at']))
        ET.SubElement(item,'description').text='\n'.join(e['summary_ko'])
    write('updates/feed.xml',ET.tostring(rss,encoding='utf-8',xml_declaration=True).decode('utf-8')+'\n')
    write('assets/updates.js',(R/'tools/updates.js').read_text(encoding='utf-8'))
