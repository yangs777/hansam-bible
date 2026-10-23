"""Substantive, linked translation-question articles; no ranking promises or synthetic endorsements."""
import html,json,pathlib
import review_layers
R=pathlib.Path(__file__).resolve().parents[1]
def esc(value):return html.escape(str(value),quote=True)
def guides():return json.loads((R/'data/genesis-guides.json').read_text(encoding='utf-8'))
def chapter_title(p,lang):
    suffix={'ko':'히브리어 원문·직역과 번역 비교','en':'Hebrew text, literal translation and comparison','es':'Texto hebreo, traducción literal y comparación'}
    return p['title'][lang]+' — '+suffix[lang]
def chapter_navigation(p,lang):
    if p['slug']!='genesis-1':return ''
    label={'ko':'창세기 1장 절 찾기','en':'Genesis 1: find a verse','es':'Génesis 1: buscar un versículo'}[lang]
    return '<nav class="verse-index" aria-label="'+label+'">'+''.join('<a href="#v'+str(v['number'])+'">1:'+str(v['number'])+'</a>' for v in p['verses'])+'</nav>'
def related_links(p,lang):
    if p['slug']!='genesis-1':return ''
    title={'ko':'창세기 1장 번역의 핵심 질문','en':'Key Genesis 1 translation questions','es':'Cuestiones clave de traducción en Génesis 1'}[lang]
    return '<section class="question-links"><h2>'+title+'</h2>'+''.join('<p><a href="/'+lang+'/guides/'+g['slug']+'/">'+esc(g['title'][lang])+' ↗</a></p>' for g in guides())+'</section>'
def build(page,write,C,E,H,traces):
    chapter=next(p for p in E if p['slug']=='genesis-1')
    for g in guides():
        for lang in ('ko','en','es'):
            path='/'+lang+'/guides/'+g['slug']+'/'
            title=g['title'][lang]
            back={'ko':'창세기 1장 전체 읽기','en':'Read all of Genesis 1','es':'Leer Génesis 1 completo'}[lang]
            body='<article class="document guide"><p class="eyebrow">GENESIS 1 / TRANSLATION QUESTION</p><h1>'+esc(title)+'</h1><p class="lead">'+esc(g['lead'][lang])+'</p><p class="byline">Hansam Yang · Original Bible · v'+C['version']+'</p><p><a href="/'+lang+'/genesis-1/">'+back+' ↗</a></p>'
            body+='<div class="notice">'+{'ko':'현재 최선의 채택 번역 · AI 보조 연구판 · 새 증거에 따라 갱신','en':'Current best selected translation · AI-assisted research edition · revisable','es':'Mejor traducción actual seleccionada · edición de investigación con IA · revisable'}[lang]+'</div>'
            for number in g['verses']:
                vid=f'HYB.GEN.001.{number:03}'; trace=traces['records'][vid]
                body+='<section><h2>Genesis 1:'+str(number)+'</h2><p class="hebrew" lang="he" dir="rtl">'+esc(H[f'Gen.1.{number}']['hebrew'])+'</p><p class="translation">'+esc(trace['selection']['translations'][lang])+'</p>'+review_layers.render(trace,lang)+'</section>'
            for section in g['sections']:
                body+='<h2>'+esc(section['heading'][lang])+'</h2><p>'+esc(section['text'][lang])+'</p>'
            body+='<h2>'+{'ko':'출처와 추적','en':'Sources and traceability','es':'Fuentes y trazabilidad'}[lang]+'</h2><ul>'
            body+='<li><a href="'+H['Gen.1.1']['source_url']+'">Pinned WLC / OSHB source</a> · WLC public domain; OSHB morphology CC BY 4.0.</li>'
            for source in g['sources']:body+='<li><a href="'+esc(source['url'])+'">'+esc(source['title'])+'</a></li>'
            body+='</ul><p>Hansam Yang. Original Bible: '+esc(title)+', v'+C['version']+'. '+C['origin']+path+'</p><p><a href="/reuse/">Scoped CC BY 4.0 reuse</a> · <a href="/data/genesis-1.json">Verse data and model records</a></p></article>'
            structured={'@context':'https://schema.org','@graph':[{'@type':'Article','headline':title,'inLanguage':lang,'url':C['origin']+path,'author':{'@type':'Person','name':C['author'],'url':C['origin']+'/about/'},'datePublished':C['date'],'dateModified':C['date'],'isBasedOn':[H['Gen.1.1']['source_url']]+[s['url'] for s in g['sources']],'license':'https://creativecommons.org/licenses/by/4.0/','creativeWorkStatus':'Revisable AI-assisted research; no human specialist certification'},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Original Bible','item':C['origin']+'/'+lang+'/'},{'@type':'ListItem','position':2,'name':chapter['title'][lang],'item':C['origin']+'/'+lang+'/genesis-1/'},{'@type':'ListItem','position':3,'name':title,'item':C['origin']+path}]}]}
            page(path,title,body,lang,{k:'/'+k+'/guides/'+g['slug']+'/' for k in ('ko','en','es')},structured,g['lead'][lang])
    write('data/genesis-guides.json',json.dumps(guides(),ensure_ascii=False,indent=2)+'\n')
