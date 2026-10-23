"""Model proposals, editorial selections and previous editions for humans and AI readers."""
import html, json, pathlib
R=pathlib.Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def esc(x): return html.escape(str(x),quote=True)

def load(version):
    def folders(ver,seen=()):
        if ver in seen:raise ValueError('Review inheritance cycle')
        folder=R/'data/model-reviews'/('v'+ver)
        manifest=read(folder/'manifest.json') if (folder/'manifest.json').exists() else {}
        return [f for parent in manifest.get('inherits',[]) for f in folders(parent,seen+(ver,))]+[folder]
    proposals={}; opinions={}; registry={}; opinion_history={}
    review_folders=folders(version)
    for p in [p for folder in review_folders for p in sorted(folder.glob('*.round1.json'))]:
        item=read(p); model=item['model']; registry[model]=item['execution']
        for v in item['verses']:
            proposals.setdefault(v['id'],[]).append({'model':model,'execution':item['execution'],**v})
        for v in item.get('opinions',[]):
            entry={'stage':p.stem,**v}; opinions.setdefault(v['id'],{})[model]=entry
            opinion_history.setdefault(v['id'],[]).append({'model':model,**entry})
    for p in [p for folder in review_folders for p in sorted(list(folder.glob('*.round2.json'))+list(folder.glob('*.round3.json')))]:
        item=read(p)
        for v in item['opinions']:
            entry={'stage':p.stem,**v}; opinions.setdefault(v['id'],{})[item['model']]=entry
            opinion_history.setdefault(v['id'],[]).append({'model':item['model'],**entry})
    decisions={v['id']:v for v in read(R/'data/decisions.json')['verses']}
    archives=[read(p) for p in sorted((R/'data/releases').glob('*.json'))]
    records={}
    for vid, decision in decisions.items():
        history=[]
        for a in archives:
            for v in a['records']:
                if v['id']==vid:
                    history.append({'version':a['version'],'translations':v['translations'],
                                    'basis':v['basis'],'decision':v['decision'],
                                    'archive_path':'/data/releases/v'+a['version']+'.json'})
        records[vid]={'selection':decision,'model_proposals':proposals.get(vid,[]),
                      'model_final_opinions':opinions.get(vid,{}),'model_opinion_history':opinion_history.get(vid,[]),'previous_editions':history}
    return {'version':version,'models':registry,'records':records,
            'policy':'Current best, revisable editorial choices; model opinions are not manuscript evidence or an infallibility claim.'}

LABELS={
 'ko':('현재 최선의 채택 번역','모델별 번역·최종 의견·이전판','채택 근거','모델','제안 번역','최종 의견 — 한국어 원문','이전 채택문','판본 데이터','MT 표시문의 번역'),
 'en':('Current best selected translation','Model translations, final opinions and history','Selection rationale','Model','Proposed translation','Final opinion — Korean original','Previous selected wording','Edition data','Translation of the MT display'),
 'es':('Traducción seleccionada: mejor opción actual','Traducciones de modelos, opiniones finales e historial','Motivo de selección','Modelo','Traducción propuesta','Opinión final — original coreano','Redacción anterior','Datos de edición','Traducción del texto del TM')}

def render(trace,lang):
    s=trace['selection']; labels=LABELS[lang]; rows=[]
    for p in trace['model_proposals']:
        opinion=trace['model_final_opinions'].get(p['model'],{})
        final=opinion.get('final_opinion_ko',p['current_opinion_ko'])
        rows.append('<tr><th scope="row">'+esc(p['model'])+'</th><td>'+esc(p['translations'][lang])+
                    '</td><td lang="ko">'+esc(final)+'</td></tr>')
    rationale=s.get('reason',{}).get(lang,s['reason_ko'])
    body='<p><strong>'+labels[2]+'</strong>: '+esc(rationale)+'</p>'
    body+='<div class="review-scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in labels[3:6])+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    body+='<p class="fine" lang="ko">반대 근거: '+esc(s['counterargument_ko'])+'</p>'
    if s.get('mt_display_translation'):
        body+='<p><strong>'+labels[8]+'</strong>: '+esc(s['mt_display_translation'][lang])+'</p>'
    for previous in trace['previous_editions']:
        body+='<p><strong>'+labels[6]+' · v'+esc(previous['version'])+'</strong>: '+esc(previous['translations'][lang])+' <a href="'+previous['archive_path']+'">'+labels[7]+' ↗</a></p>'
    if s.get('additional_review_status'):
        body+='<p class="fine" lang="ko">'+esc(s['additional_review_status'])+'</p>'
    return '<p class="selection-label">'+labels[0]+' · v'+esc(s['version'])+'</p><details class="model-review"><summary>'+labels[1]+'</summary>'+body+'</details>'

def markdown(trace,lang):
    s=trace['selection']; lines=['### '+LABELS[lang][0],s.get('reason',{}).get(lang,s['reason_ko'])]
    for p in trace['model_proposals']:
        opinion=trace['model_final_opinions'].get(p['model'],{})
        lines += ['#### '+p['model'],p['translations'][lang],
                  'Final opinion (Korean original): '+opinion.get('final_opinion_ko',p['current_opinion_ko'])]
    if s.get('mt_display_translation'):lines += [LABELS[lang][8],s['mt_display_translation'][lang]]
    lines += ['Counterargument (Korean): '+s['counterargument_ko']]
    for a in trace['previous_editions']:lines += ['Previous v'+a['version'],a['translations'][lang]]
    return lines
