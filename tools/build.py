"""Dependency-free static publisher. HTML, Markdown and JSON share one source."""
import csv, hashlib, html, io, json, pathlib, shutil, zipfile
from datetime import datetime, timezone
import review_layers
import search_pages
import reader
import updates
import support
import chapter_sources
R=pathlib.Path(__file__).resolve().parents[1]; D=R/'dist'; D.mkdir(exist_ok=True)
C=json.loads((R/'config.json').read_text(encoding='utf-8'))
E=json.loads((R/'data/editorial.json').read_text(encoding='utf-8'))['passages']
H=json.loads((R/'data/hebrew.json').read_text(encoding='utf-8'))
TRACES=review_layers.load(C['version'])
VERSE_COUNT=sum(len(p['verses']) for p in E)
ORIGIN=C['origin']; VERSION=C['version']; AUTHOR=C['author']; LICENSE='https://creativecommons.org/licenses/by/4.0/'
L={
'ko':dict(name='한국어',home='본문 읽기',data='데이터',about='프로젝트',pilot='연구 시험판',hero='원문을 따라,<br>언어를 넘어.',lead='성경의 말과 그 근거를 함께 읽습니다. 원어에서 번역까지, 모든 판단의 흔적을 남기는 Hansam Yang의 공개 연구 프로젝트.',read='본문 살펴보기',download='데이터 내려받기',texts='본문과 번역의 쟁점',draft='AI 보조 번역 초안 · 원어·모국어 전문가 검수 전',evidence='근거를 펼쳐 읽기',notes='번역과 본문 주석',gloss='선택 어휘',morph='전체 표시문 형태분석',source='출처와 재사용',copy='인용 복사',copied='복사했습니다',original='히브리어 표시문 · MT / WLC',translation='현재 최선의 채택 번역',variant='보고된 이문구 · 채택 번역의 근거',status='판정',none='외부 전문가 검수 대기',focus='읽기 전 알아둘 점',intro2='현재의 최선을 읽고,<br>새 증거로 갱신합니다.',intro3='사본과 복원, 번역과 해석을 구별합니다. 새 증거가 들어오면 판단과 번역을 함께 갱신합니다.',view='본문 열기',number='절',author='최초 기획·제작',warning='이 판본은 연구 초안입니다. 자필원본의 발견이나 완전한 본문 복원을 주장하지 않습니다.',selected='아래 어휘 풀이는 선택 어휘의 초안입니다. 모든 단어에 대한 완성된 한국어 인터리니어가 아닙니다.',citation='인용 예시',terms='재사용 안내',pending='직접 사본 사진 판독 대기',all='전체 데이터',privacy='추적 쿠키·광고 없음'),
'en':dict(name='English',home='Read',data='Data',about='Project',pilot='Research pilot',hero='Follow the text.<br>Across languages.',lead='Read the biblical words alongside their evidence. An open research project by Hansam Yang, tracing decisions from Hebrew display to translation.',read='Explore the texts',download='Download the data',texts='Texts and translation questions',draft='AI-assisted translation draft · specialist and native-language review pending',evidence='Read with the evidence',notes='Text and translation notes',gloss='Selected vocabulary',morph='Morphology of the full display',source='Sources and reuse',copy='Copy citation',copied='Copied',original='Hebrew display · MT / WLC',translation='Current best selected translation',variant='Reported variant phrase · basis of the selected translation',status='Decision',none='External specialist review pending',focus='Before you read',intro2='The best current reading.<br>Open to better evidence.',intro3='Manuscript, reconstruction, translation and interpretation remain distinct. New evidence can change both the decision and the translation.',view='Open passage',number='Verse',author='Founder and original creator',warning='This is a research draft. It does not claim discovery of an autograph or a complete reconstruction of the earliest text.',selected='These are selected draft glosses, not a complete word-aligned interlinear translation.',citation='Suggested citation',terms='Reuse guide',pending='Direct manuscript-image review pending',all='Complete data',privacy='No tracking cookies or advertising'),
'es':dict(name='Español',home='Leer',data='Datos',about='Proyecto',pilot='Piloto de investigación',hero='Siga el texto.<br>Más allá del idioma.',lead='Lea las palabras bíblicas junto a sus testimonios. Un proyecto abierto de Hansam Yang que permite seguir las decisiones desde el hebreo hasta la traducción.',read='Explorar los textos',download='Descargar los datos',texts='Textos y cuestiones de traducción',draft='Borrador de traducción asistido por IA · pendiente de revisión especializada y nativa',evidence='Leer con los testimonios',notes='Notas de texto y traducción',gloss='Vocabulario seleccionado',morph='Morfología del texto completo presentado',source='Fuentes y reutilización',copy='Copiar cita',copied='Copiado',original='Texto hebreo · TM / WLC',translation='Mejor traducción actual seleccionada',variant='Frase variante publicada · base de la traducción seleccionada',status='Decisión',none='Pendiente de revisión externa especializada',focus='Antes de leer',intro2='La mejor lectura actual.<br>Abierta a nuevos datos.',intro3='Manuscrito, reconstrucción, traducción e interpretación se mantienen distintos. Un nuevo testimonio puede cambiar la decisión y la traducción.',view='Abrir pasaje',number='Versículo',author='Fundador y creador original',warning='Este es un borrador de investigación. No afirma haber descubierto un autógrafo ni reconstruido por completo el texto más antiguo.',selected='Estas son glosas seleccionadas provisionales, no una traducción interlineal completa palabra por palabra.',citation='Cita sugerida',terms='Guía de reutilización',pending='Pendiente de revisión directa de imágenes del manuscrito',all='Datos completos',privacy='Sin cookies de seguimiento ni publicidad')}
def esc(v): return html.escape(str(v),quote=True)
def write(path,text):
    p=D/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text.replace('__VERSION__',C['version']).replace('__PASSAGES__',str(len(E))).replace('__VERSES__',str(VERSE_COUNT)),encoding='utf-8',newline='\n')
def js(v): return json.dumps(v,ensure_ascii=False,indent=2)
def url(path): return ORIGIN+path
def citation(p,lang):return f"Hansam Yang. Original Bible: {p['reference']} ({lang}), research pilot v{VERSION}. {url('/'+lang+'/'+p['slug']+'/')}"
def header(lang, path=''):
    t = L[lang]
    names = {
        'ko': ('본문 읽기', '성경 대조', '더보기', '자료 내려받기', '원문과 사본', '업데이트', '프로젝트', '의견함', '본문으로 건너뛰기'),
        'en': ('Read', 'Compare', 'More', 'Downloads', 'Text and manuscripts', 'Updates', 'Project', 'Feedback', 'Skip to content'),
        'es': ('Leer', 'Comparar', 'Más', 'Descargas', 'Texto y manuscritos', 'Novedades', 'Proyecto', 'Comentarios', 'Saltar al contenido'),
    }[lang]
    langs = ''.join(f'<a lang="{key}" href="/{key}/{path}"' + (' aria-current="page"' if key == lang else '') + f'>{value["name"]}</a>' for key, value in L.items())
    extra = ''.join(f'<a href="{href}">{label}</a>' for href, label in zip(
        ('/data/', '/sources/', '/updates/', '/about/', 'https://original-bible-feedback.yangs7777.chatgpt.site/'), names[3:8]))
    return f'''<a class="skip" href="#main">{names[8]}</a>
<header class="top">
  <a class="brand" href="/{lang}/"><span class="mark">O<span>B</span></span><span>{C['name_ko'] if lang == 'ko' else C['name_en']}<small>ORIGINAL BIBLE / TEXTUAL ORIGINS</small></span></a>
  <nav class="primary-nav" aria-label="{names[0]}">
    <a href="/{lang}/#passages">{names[0]}</a><a href="/read/">{names[1]}</a>
    <details class="nav-more"><summary>{names[2]}</summary><div class="nav-menu">{extra}<div class="languages">{langs}</div></div></details>
  </nav>
</header>'''


def footer(lang):
    t=L[lang]
    return f'''<footer>{support.footer(lang)}<div class="footer-brand">ORIGINAL BIBLE <span>v{VERSION}</span></div><p>{t['author']}: <a href="/about/">Hansam Yang</a></p><p>{t['warning']}</p><p><a href="/reuse/">CC BY 4.0 · {t['terms']}</a> · <a href="{C['repository']}">GitHub</a> · <a href="/data/">JSON / JSONL / Markdown</a></p><small>{t['privacy']}</small></footer>'''
PAGES=[]
def page(path,title,body,lang='en',alternates=None,structured=None,description=''):
    canonical=url(path); PAGES.append(canonical)
    data=structured or {'@context':'https://schema.org','@type':'WebPage','name':title,'url':canonical,'inLanguage':lang,'isPartOf':{'@id':url('/#project')}}
    safe_json=js(data).replace(chr(60)+chr(47),chr(60)+chr(92)+chr(47))
    alt=''.join(f'<link rel="alternate" hreflang="{k}" href="{url(v)}">' for k,v in (alternates or {}).items())
    out=f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | 원문성경 · Original Bible</title><meta name="description" content="{esc(description or title+' — Hansam Yang, research pilot '+VERSION)}"><meta name="author" content="Hansam Yang"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}">{alt}<link rel="alternate" type="application/rss+xml" title="Original Bible updates" href="{url('/updates/feed.xml')}"><link rel="stylesheet" href="/assets/style.css"><meta property="og:site_name" content="원문성경 / Original Bible"><meta property="og:title" content="{esc(title)}"><meta property="og:url" content="{canonical}"><meta property="og:type" content="article"><script type="application/ld+json">{safe_json}</script><script src="/assets/app.js" defer></script></head><body>{header(lang,path.split('/',2)[-1] if path.startswith('/'+lang+'/') else '')}<main id="main">{body}</main>{footer(lang)}</body></html>'''
    write(path.lstrip('/')+'index.html',out)
def home(lang):
    t = L[lang]
    words = {
        'ko': ('성경 원문과 번역을 함께 읽으세요', '원문과 한국어 번역을 나란히 읽고, 궁금한 근거는 펼쳐 보세요.', '창세기 1장부터 읽기', '히브리어 원문', '한국어 번역', '수록 본문', '최근 업데이트', '프로젝트와 수록 범위', '본문', '언어', '절', '편집 방법'),
        'en': ('Read the Hebrew alongside the translation', 'Start reading. Open the notes whenever you want to explore the evidence.', 'Start with Genesis 1', 'Hebrew text', 'English translation', 'Available passages', 'Recent updates', 'Project and coverage', 'passages', 'languages', 'verses', 'Editorial method'),
        'es': ('Lea el hebreo junto con la traducción', 'Empiece a leer. Abra las notas cuando quiera explorar los testimonios.', 'Empezar por Génesis 1', 'Texto hebreo', 'Traducción al español', 'Pasajes disponibles', 'Novedades recientes', 'Proyecto y alcance', 'pasajes', 'idiomas', 'versículos', 'Método editorial'),
    }[lang]
    order = {book['id']: i for i, book in enumerate(json.loads((R / 'library/catalog.json').read_text(encoding='utf-8'))['books'])}
    passages = sorted(E, key=lambda p: (order[p['verses'][0]['source'].split('.')[0]], *map(int, p['verses'][0]['source'].split('.')[1:])))
    sample = next(p for p in passages if p['slug'] == 'genesis-1')['verses'][0]
    rows = ''.join(f'''<a class="passage-row" href="/{lang}/{p['slug']}/"><span class="row-number">{i:02}</span><div><h3>{esc(p['title'][lang])}</h3><p>{esc(p['subtitle'][lang])}</p></div><span class="arrow" aria-hidden="true">→</span></a>''' for i, p in enumerate(passages, 1))
    entries = json.loads((R / 'data/updates.json').read_text(encoding='utf-8'))['entries']
    latest = entries[0]
    update_text = esc(latest['title_ko']) if lang == 'ko' else 'v' + VERSION
    body = f'''<section class="welcome">
  <div><h1>{words[0]}</h1><p class="lead">{words[1]}</p><p class="edition-note">{t['draft']} · v{VERSION}</p><a class="button" href="/{lang}/genesis-1/">{words[2]} →</a></div>
  <article class="opening-text"><p class="eyebrow">{esc(next(p for p in E if p['slug'] == 'genesis-1')['title'][lang])} · 1</p><span class="text-label">{words[3]}</span><div class="hebrew" lang="he" dir="rtl">{esc(H[sample['source']]['hebrew'])}</div><span class="text-label">{words[4]}</span><p class="translation">{esc(sample[lang])}</p></article>
</section>
<section class="catalog" id="passages"><h2>{words[5]}</h2>{rows}</section>
<p class="recent-update"><a href="/updates/">{words[6]} →</a> <small>{update_text}</small></p>
<details class="project-details"><summary>{words[7]}</summary><p>{t['lead']}</p><div class="stats"><div><strong>{len(E):02}</strong><span>{words[8]}</span></div><div><strong>03</strong><span>{words[9]}</span></div><div><strong>{VERSE_COUNT}</strong><span>{words[10]}</span></div><div class="stat-note">{t['draft']}</div></div><h2>{t['hero']}</h2><h3>{t['intro2']}</h3><p>{t['intro3']}</p><a href="/methodology/">{words[11]} ↗</a><p><a href="/data/">{t['download']} ↗</a></p></details>'''
    title = {'ko': '원문성경 — 히브리어 원문과 번역 대조', 'en': 'Original Bible — Hebrew text and translation comparison', 'es': 'Original Bible — texto hebreo y comparación de traducciones'}[lang]
    page('/' + lang + '/', title, body, lang, {key: '/' + key + '/' for key in L}, description=words[1])


def study(p, lang):
    t = L[lang]
    words = {
        'ko': ('히브리어 원문', '한국어 번역', '이 본문 안내와 사용 자료', '새 근거에 따라 갱신하는 현재 채택 번역', '번역에 사용한 본문', '형태 분석 코드 안내', '형태 분석과 사전형 정보는 OSHB에서 가져왔습니다. 원문 사진을 새로 판독한 결과와 구분합니다.', '히브리어', '사전형', '형태 분석', '출처와 재사용 · 인용', '신명은 한국어에서 여호와로 표기합니다. 원어 표기는 YHWH(יהוה)입니다.', '기록 원문 · 정확한 내부 명칭', '다른 성경과 대조 · 본문 복사'),
        'en': ('Hebrew text', 'English translation', 'About this passage and its sources', 'Current selected translation, open to new evidence', 'Textual basis', 'Morphology code guide', 'Morphology and lemmas are imported from OSHB, separate from a new reading of manuscript images.', 'Hebrew', 'Lemma', 'Morphology', 'Sources, reuse and citation', 'The Korean translation uses 여호와 for the divine name YHWH(יהוה). English and Spanish retain their existing conventions.', 'Original records and exact internal names', 'Compare Bibles / copy text'),
        'es': ('Texto hebreo', 'Traducción al español', 'Sobre este pasaje y sus fuentes', 'Traducción actual seleccionada, abierta a nuevos testimonios', 'Base textual', 'Guía de códigos morfológicos', 'La morfología y los lemas proceden de OSHB y se distinguen de una nueva lectura de imágenes de manuscritos.', 'Hebreo', 'Lema', 'Morfología', 'Fuentes, reutilización y cita', 'La traducción coreana emplea 여호와 para el nombre divino YHWH(יהוה). El inglés y el español conservan sus convenciones.', 'Registros originales y nombres internos exactos', 'Comparar Biblias / copiar texto'),
    }[lang]
    basis = {
        'ko': '고정한 히브리어 전자 본문을 사용했습니다. 관련 사본 전체의 독립 대조는 완료되지 않았습니다.',
        'en': 'The pinned Hebrew digital text is used. Independent collation of all relevant manuscripts remains incomplete.',
        'es': 'Se utiliza el texto hebreo digital fijado. Sigue pendiente el cotejo independiente de todos los manuscritos pertinentes.',
    }[lang]
    if p['slug'] == 'deuteronomy-32-8':
        basis = {
            'ko': '신적 존재의 아들들에 해당하는 보고된 사해문서 어구를 잠정 채택했습니다. 전체 번역은 히브리어 전승 본문의 나머지와 이 어구를 결합한 편집적 재구성입니다.',
            'en': 'The reported Dead Sea Scroll phrase referring to divine sons is provisionally selected. The full translation is an editorial reconstruction using the rest of the Masoretic text.',
            'es': 'Se selecciona provisionalmente la frase publicada de un manuscrito del Mar Muerto sobre los hijos divinos. La traducción completa es una reconstrucción editorial con el resto del texto masorético.',
        }[lang]
    elif p['slug'] == 'numbers-6-24-26':
        basis = {
            'ko': '고정한 히브리어 전자 본문을 번역했습니다. 유사한 비문으로 성경 본문을 대체하지 않았습니다.',
            'en': 'The pinned Hebrew digital text is translated. No inscription is substituted for the biblical text.',
            'es': 'Se traduce el texto hebreo digital fijado. Ninguna inscripción sustituye al texto bíblico.',
        }[lang]
    rows = []
    md = [f"# {p['title'][lang]}", f'Hansam Yang · Original Bible · v{VERSION}', t['draft'], t['warning'], p['intro'][lang], f"Basis: {p['basis']}", f"Decision: {p['decision']}"]
    for verse in p['verses']:
        hebrew = H[verse['source']]
        review = review_layers.render(TRACES['records'][verse['id']], lang, VERSION)
        review = review.replace('</summary>', '</summary><p><code>' + esc(verse['id']) + '</code></p>', 1)
        rows.append(f'''<article class="verse" id="v{verse['number']}"><div class="verse-label"><span>{verse['number']:02}</span></div><div class="verse-original"><span class="text-label">{words[0]}</span><div class="hebrew" lang="he" dir="rtl">{esc(hebrew['hebrew'])}</div></div><div class="verse-translation"><span class="text-label">{words[1]}</span><p class="translation">{esc(verse[lang])}</p></div>{review}</article>''')
        md.extend([f"## {verse['number']} · {verse['id']}", f"Hebrew display (MT/WLC): {hebrew['hebrew']}", verse[lang], f"Source: {hebrew['source_url']} · {verse['source']}"])
        md.extend(review_layers.markdown(TRACES['records'][verse['id']], lang))
    notes = ''.join(f'<li>{esc(note[lang])}</li>' for note in p['notes'])
    gloss = ''.join(f'<tr><th lang="he" dir="rtl">{esc(item["he"])}</th><td>{esc(item[lang])} <small>({esc(item["form_type"])})</small></td></tr>' for item in p['glosses'])
    morph = ''.join(f'<tr><td>{verse["number"]}</td><td lang="he" dir="rtl">{esc(word["hebrew"])}</td><td><code>{esc(word["lemma"])}</code></td><td><code>{esc(word["morph"])}</code></td></tr>' for verse in p['verses'] for word in H[verse['source']]['tokens'])
    variant = ''
    if 'variant' in p:
        item = p['variant']
        variant = f'''<section class="variant"><p class="eyebrow">{t['variant']}</p><p class="hebrew" lang="he" dir="rtl">{esc(item['hebrew'])}</p><p>{esc(item[lang])}</p><small>{esc(item['witness'])} · {t['pending']}</small><p><a href="{esc(item['source'])}">Emanuel Tov (2023), TheTorah.com ↗</a></p></section>'''
        md.extend(['## Reported comparison reading — NOT a complete 4Q37 verse', item['hebrew'], item[lang], item['status'], item['source']])
    book, chapter, _ = p['verses'][0]['source'].split('.')
    cite = citation(p, lang)
    source_text = {
        'ko': '히브리어 전자 본문은 공공영역인 Westminster Leningrad Codex입니다. 사전형과 형태 분석은 Open Scriptures Hebrew Bible에서 가져왔으며 CC BY 4.0으로 제공합니다. 표시된 모음과 악센트는 이 마소라 본문 판본의 표기입니다. 사해문서 사진의 특징으로 간주하지 않습니다. 문장부호 공백은 화면에 맞게 조정했습니다. 위 번역은 이 프로젝트의 AI 보조 번역 초안이며 현대 성경 번역을 가져오지 않았습니다. 별도 출처를 밝힌 기존 번역본은 대조 화면에서 읽을 수 있습니다.',
        'en': 'The Hebrew digital text is the public-domain Westminster Leningrad Codex. Lemmas and morphology come from Open Scriptures Hebrew Bible under CC BY 4.0. Displayed vowels and accents belong to this Masoretic edition, rather than to Dead Sea Scroll photographs. Punctuation spacing is adapted for display. These AI-assisted editorial drafts do not import a modern Bible translation. Separately credited reading editions are available in the comparison reader.',
        'es': 'El texto hebreo digital es el Westminster Leningrad Codex de dominio público. Los lemas y la morfología proceden de Open Scriptures Hebrew Bible bajo CC BY 4.0. Las vocales y los acentos pertenecen a esta edición masorética y no se atribuyen a fotografías del Mar Muerto. Los espacios de puntuación se adaptan a la pantalla. Estos borradores editoriales con IA no incorporan una traducción bíblica moderna. El lector comparativo ofrece ediciones existentes con sus propias fuentes.',
    }[lang]
    body = f'''<div class="study-head reading-head"><a class="breadcrumb" href="/{lang}/#passages">← {t['home']}</a><h1>{esc(p['title'][lang])}</h1><p class="subtitle">{esc(p['subtitle'][lang])}</p><p class="edition-note">{t['translation']} · v{VERSION}<br>{t['draft']}</p></div>
<div class="study-content reading-content">
  <details class="passage-info"><summary>{words[2]}</summary><p>{basis}</p><p>{words[3]}</p><p class="byline">{t['author']} · <a href="/about/">Hansam Yang</a></p><dl><dt>{words[4]}</dt><dd>{basis}</dd></dl><p>{words[11]}</p>{chapter_sources.passage_links(p,lang)}<p><a href="/read/?book={book}&amp;chapter={chapter}&amp;left=original-{lang}&amp;right=krv">{words[13]} ↗</a></p>{search_pages.chapter_navigation(p,lang)}<p><a href="/data/{p['slug']}.{lang}.md">Markdown ↗</a> · <a href="/data/{p['slug']}.json">JSON ↗</a></p><details><summary>{words[12]}</summary><p>{p['intro'][lang]}</p><p><code>{p['id']}</code></p><p lang="en">{esc(p['decision'])}</p><p lang="en">{esc(p['basis'])}</p></details></details>
  {''.join(rows)}
  <details class="passage-notes" id="notes"><summary>{t['notes']} · {t['gloss']}</summary>{variant}{search_pages.related_links(p,lang)}<ol>{notes}</ol><h3>{t['gloss']}</h3><p class="fine">{t['selected']}</p><table><thead><tr><th>{words[7]}</th><th>{t['gloss']}</th></tr></thead><tbody>{gloss}</tbody></table><details><summary>{t['morph']} · OSHB</summary><p>{words[6]} <a href="https://github.com/openscriptures/morphhb/tree/master/parsing">{words[5]} ↗</a></p><table><thead><tr><th>{t['number']}</th><th>{words[7]}</th><th>{words[8]}</th><th>{words[9]}</th></tr></thead><tbody>{morph}</tbody></table></details></details>
  <details class="source-note"><summary>{words[10]}</summary><p>{source_text}</p><p>Open Scriptures Hebrew Bible · <a href="https://github.com/openscriptures/morphhb">https://github.com/openscriptures/morphhb</a> · CC BY 4.0</p><p><code>{C['source_commit']}</code> · <a href="/data/{p['slug']}.json">JSON · SHA-256</a></p><section class="citation"><h2>{t['citation']}</h2><p id="citation-text">{cite}</p><button class="button" data-copy="citation-text" data-done="{t['copied']}">{t['copy']}</button><p class="copy-status" role="status"></p><p class="fine">{t['warning']}</p><p><a href="/reuse/">CC BY 4.0 · {t['terms']}</a></p></section></details>
</div>'''
    structured = {'@context': 'https://schema.org', '@type': 'CreativeWork', '@id': url('/' + lang + '/' + p['slug'] + '/#work'), 'name': p['title'][lang] + ' — research draft', 'url': url('/' + lang + '/' + p['slug'] + '/'), 'inLanguage': lang, 'version': VERSION, 'datePublished': C['date'], 'dateModified': C['date'], 'creator': {'@id': url('/about/#hansam-yang'), '@type': 'Person', 'name': AUTHOR}, 'license': LICENSE, 'creditText': f'Hansam Yang, Original Bible v{VERSION}; AI-assisted draft. WLC/OSHB separately credited.', 'isBasedOn': sorted({H[verse['source']]['source_url'] for verse in p['verses']}), 'creativeWorkStatus': 'Research pilot; specialist review pending', 'isPartOf': {'@id': url('/#project')}}
    page('/' + lang + '/' + p['slug'] + '/', search_pages.chapter_title(p,lang), body, lang, {key: '/' + key + '/' + p['slug'] + '/' for key in L}, structured, p['subtitle'][lang])
    md.extend(['## Notes'] + [note[lang] for note in p['notes']] + ['## Citation', cite, 'Editorial material: CC BY 4.0 to the extent rights are held. Ancient WLC text: public domain. OSHB morphology: CC BY 4.0, Open Scriptures Hebrew Bible.', 'No human specialist approval is claimed.', 'Source transformation: OSHB separators removed; original vowel/accent codepoints preserved; punctuation spacing adapted.'])
    write(f'data/{p["slug"]}.{lang}.md', '\n\n'.join(md) + '\n')

for lang in L:
    home(lang)
    for p in E: study(p,lang)
# Entry point resolves to Korean home without requiring client-side rendering.
root=(D/'ko/index.html').read_text(encoding='utf-8'); write('index.html',root)
records=[]; packets=[]
for p in E:
    packet={'id':p['id'],'reference':p['reference'],'version':VERSION,'project_author':AUTHOR,'author_role':'Project founder, responsible editor and publisher; ancient authorship not claimed','status':'research-pilot','decision':p['decision'],'basis':p['basis'],'notes':p['notes'],'selected_glosses':p['glosses'],'records':[]}
    if 'variant' in p:
        packet['reported_variant']=p['variant']
        packet['readings']=p['readings']
    for v in p['verses']:
        record={'id':v['id'],'reference':v['source'],'passage':p['reference'],'version':VERSION,'project_author':AUTHOR,'author_role':'Project founder, responsible editor and publisher','translation_origin':'New AI-assisted drafts for this project; no modern Bible translation imported','translation_status':'draft','human_specialist_review':'pending','decision':p['decision'],'basis':p['basis'],'hebrew_layer':H[v['source']],'translations':{k:v[k] for k in L},'canonical_urls':{k:url('/'+k+'/'+p['slug']+'/#v'+str(v['number'])) for k in L},'citations':{k:citation(p,k)+' #v'+str(v['number']) for k in L},'rights':{'editorial':{'license':'CC-BY-4.0','url':LICENSE,'credit':AUTHOR,'scope':'New editorial material and translation drafts, to the extent rights are held; no exclusive right claimed over public-domain scripture'},'hebrew_text':{'status':'public-domain','source':'Westminster Leningrad Codex'},'morphology':{'license':'CC-BY-4.0','credit':'Open Scriptures Hebrew Bible','url':'https://github.com/openscriptures/morphhb'}}}
        record['selection_status']='current_best_provisional'
        record['decision_trace']=TRACES['records'][v['id']]
        record['model_provenance']={proposal['model']:proposal.get('execution',{}) for proposal in TRACES['records'][v['id']]['model_proposals']}
        record['title']=C['title']
        record['citations']={k:citation(p,k).rstrip()+'#v'+str(v['number']) for k in L}
        if 'variant' in p:
            record['reported_variant']=p['variant']
            record['readings']=p['readings']
        packet['records'].append(record); records.append(record)
    packets.append(packet); write(f'data/{p["slug"]}.json',js(packet)+'\n')
dataset={'@context':'https://schema.org','@type':'Dataset','@id':url('/#project'),'name':C['title'],'description':f'{VERSE_COUNT} Hebrew Bible verses with current-best translations and model comparisons in Korean, English and Spanish. Revisable research edition.','creator':{'@type':'Person','@id':url('/about/#hansam-yang'),'name':AUTHOR},'version':VERSION,'license':LICENSE,'url':url('/data/'),'datePublished':C['date'],'inLanguage':['he','ko','en','es'],'distribution':[{'@type':'DataDownload','encodingFormat':'application/json','contentUrl':url('/data/hansam-bible.json')},{'@type':'DataDownload','encodingFormat':'application/x-ndjson','contentUrl':url('/data/hansam-bible.jsonl')}],'isAccessibleForFree':True,'creativeWorkStatus':'Research pilot; human specialist review pending'}
write('data/hansam-bible.json',js({'metadata':dataset,'records':records})+'\n');write('data/hansam-bible.jsonl','\n'.join(json.dumps(x,ensure_ascii=False) for x in records)+'\n')
write(f'data/releases/v{VERSION}.json',js({'version':VERSION,'title':C['title'],'state':'current','metadata':dataset,'records':records})+'\n')
write('data/model-reviews.json',js(TRACES)+'\n')
for source in (R/'data/releases').glob('*.json'):
    archive_target=D/'data/releases'/source.name; archive_target.parent.mkdir(parents=True,exist_ok=True); archive_target.write_bytes(source.read_bytes())
write('data/catalog.json',js({'author':AUTHOR,'version':VERSION,'passages':[{'id':p['id'],'reference':p['reference'],'json':url('/data/'+p['slug']+'.json'),'pages':{k:url('/'+k+'/'+p['slug']+'/') for k in L}} for p in E]})+'\n')
buf=io.StringIO(); w=csv.writer(buf,delimiter='\t',lineterminator='\n');w.writerow(['id','reference','hebrew','ko','en','es','project_author','version','status','citation_ko','editorial_license','hebrew_rights','morphology_credit'])
for x in records:w.writerow([x['id'],x['reference'],x['hebrew_layer']['hebrew'],*[x['translations'][k] for k in L],AUTHOR,VERSION,x['translation_status'],x['citations']['ko'],'CC-BY-4.0','Public domain','Open Scriptures Hebrew Bible (CC BY 4.0)'])
write('data/verses.tsv',buf.getvalue())
data_body='''<section class="document"><p class="eyebrow">OPEN RESEARCH DATA</p><h1>Take the text.<br>Keep the source.</h1><p class="lead">Hansam Yang · Original Bible · research pilot __VERSION__</p><div class="notice">번역 초안 / Translation drafts / Borradores. External specialist and native-language review pending.</div><p>__PASSAGES__ passages · __VERSES__ unique verses · 3 translation languages. Every JSONL record carries author, version, source, rights and review state.</p><div class="downloads"><a href="/data/hansam-bible.json">Complete JSON ↗</a><a href="/data/hansam-bible.jsonl">JSONL: one verse per record ↗</a><a href="/data/verses.tsv">UTF-8 TSV ↗</a><a href="/data/catalog.json">Catalog ↗</a><a href="/data/schema.json">Schema ↗</a><a href="/data/hansam-bible-pilot-v__VERSION__.zip" download>Download ZIP ↧</a></div><h2>Markdown</h2>'''+''.join('<p>'+esc(p['reference'])+' · '+' · '.join(f'<a href="/data/{p["slug"]}.{k}.md">{L[k]["name"]}</a>' for k in L)+'</p>' for p in E)+'''<h2>Reuse with attribution</h2><p>Credit Hansam Yang for this modern editorial project, preserve the version and draft state, and keep upstream WLC/OSHB credits. Do not describe Hansam Yang as the ancient author or imply an endorsement.</p><p><a href="/reuse/">Read the scoped license notice</a> · <a href="/methodology/">Editorial method</a></p><h2>Model comparison and edition history</h2><p>Every verse has a current best selection, actual GPT/Gemini proposals, recorded final opinions and previous wording. Model agreement is not manuscript evidence.</p><p><a href="/data/model-reviews.json">Model reviews and decisions ↗</a> · <a href="/data/releases/v0.1.0.json">Previous edition v0.1.0 ↗</a></p><h2>Reproducibility</h2><p>The dataset pins its upstream commit and original XML hashes. No login, API key or JavaScript is required to retrieve these files.</p><p><a href="/data/checksums.sha256">SHA-256 manifest</a> · <a href="'''+C['repository']+'''">GitHub source</a></p></section>'''
page('/data/','Open data',data_body,structured=dataset)
page('/about/','Hansam Yang — project author','''<section class="document"><p class="eyebrow">THE PERSON BEHIND THE PROJECT</p><h1>Hansam Yang</h1><p class="lead">Project founder, responsible editor and publisher of Original Bible.</p><p>Hansam Yang initiated this project to trace the earliest recoverable biblical text and make evidence-aware readings available across languages. The pilot collection is produced with AI assistance. The name identifies the modern editorial project, not authorship of the ancient biblical texts.</p><div class="notice">AI assistance is disclosed. External Hebrew, textual-critical and native-language review is pending; no human specialist approval or institutional endorsement is claimed.</div><h2>A project built to be checked</h2><p>Read the evidence, inspect the data, and challenge the decisions. A reported variant remains distinct from a directly verified manuscript reading. Corrections are versioned.</p><p>기획·책임 편집·발행: Hansam Yang. 원어와 각 언어의 전문가 검수 전인 공개 연구 초안입니다.</p><p>Fundador y editor responsable: Hansam Yang. Piloto con asistencia de IA, pendiente de revisión especializada.</p><p><a href="/methodology/">Editorial method ↗</a> · <a href="/reuse/">Reuse and attribution ↗</a></p></section>''',structured={'@context':'https://schema.org','@type':'Person','@id':url('/about/#hansam-yang'),'name':AUTHOR,'url':url('/about/'),'description':'Founder, responsible editor and publisher of Original Bible, an AI-assisted research pilot.'})
page('/methodology/','Evidence, decisions, translation','''<section class="document"><p class="eyebrow">EDITORIAL METHOD / v__VERSION__</p><h1>Evidence before<br>certainty.</h1><p class="lead">Evidence → decision → counter-check → translation → review → versioned publication.</p><ol><li>Register the source, rights, date and textual scope.</li><li>Distinguish manuscript transcription from a modern edited display.</li><li>Keep normalized text, restored text, retroversion and conjecture distinct.</li><li>Compare individual readings and ancient editions; do not privilege a manuscript solely because it is older.</li><li>Record the strongest counterargument and select the current best translation; keep unresolved historical details separately identified.</li><li>Translate from the stated Hebrew basis, distinguishing a manuscript display from an editorial reconstruction; label every alternative reading.</li><li>Request independent review and record corrections. Specialist review remains a separate requirement.</li></ol><h2>This collection</h2><p>Complete MT-WLC verses are provided as comparison displays; selected translations state their own textual basis. No complete independent collation of these passages has been performed. Deuteronomy 32:8 now selects the divine-sons reading provisionally. Its full translation is an editorial reconstruction using the MT remainder and a reported 4Q37 phrase, rather than a complete 4Q37 verse or a new photograph reading.</p><h2>Layers and rights</h2><p>WLC Hebrew text is public domain. OSHB morphology and lemmas are credited under CC BY 4.0. Display removes morpheme separators and adapts punctuation spacing while preserving vowel/accent codepoints. The three translations and notes are fresh AI-assisted editorial drafts. Selected glosses are illustrative, not a complete word-aligned interlinear.</p><h2>Corrections</h2><p>Report the passage ID, version, source and proposed correction through the repository. New evidence can reopen a decision; the previous release remains identifiable.</p><p><a href="'''+C['repository']+'''/issues">Repository issues ↗</a> · <a href="/data/">Inspect the records ↗</a></p></section>''')
page('/reuse/','Reuse and attribution','''<section class="document"><p class="eyebrow">OPEN BY DESIGN</p><h1>Use it.<br>Credit its sources.</h1><p class="lead">CC BY 4.0 for new editorial material and translation drafts, to the extent rights are held.</p><p>Reuse, translate, adapt and redistribute the editorial material, including commercially, under the <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0 license</a>. Retain reasonable attribution, a license link and change notices. The license does not require promotional praise or imply endorsement. Public-domain material and applicable exceptions remain outside its conditions.</p><pre>Hansam Yang. Original Bible, [passage], [language],
research pilot v__VERSION__. [canonical URL].
AI-assisted draft; specialist review pending.
Modified by [name], [date], if applicable.</pre><h2>Keep these scopes separate</h2><ul><li>Ancient WLC Hebrew: public domain. No exclusive authorship claim by Hansam Yang.</li><li>OSHB lemmas and morphology: CC BY 4.0. Credit: Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb.</li><li>New notes and translations: CC BY 4.0 to the extent rights are held; AI assistance disclosed.</li><li>Third-party studies and manuscript images retain their respective rights. Links are not a relicensing of those materials.</li><li>Site generator and interface code: MIT.</li></ul><p>No warranties are given. Preserve the research-draft label, evidence distinctions and unresolved readings when describing the release. These documentation requests do not add restrictions beyond the applicable license.</p><p>AI retrieval, training incorporation and visible citations are not guaranteed by crawler access or this license.</p></section>''')
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':url('/data/schema.json'),'title':'Original Bible verse record','type':'object','required':['id','reference','version','project_author','translation_status','human_specialist_review','decision','basis','hebrew_layer','translations','canonical_urls','citations','rights','selection_status','decision_trace','model_provenance'],'properties':{'id':{'type':'string','pattern':'^HYB\\.'},'project_author':{'const':AUTHOR},'version':{'type':'string'},'translation_status':{'enum':['draft','reviewed']},'human_specialist_review':{'type':'string'},'translations':{'type':'object','required':['ko','en','es'],'properties':{k:{'type':'string','minLength':1} for k in L}},'hebrew_layer':{'type':'object','required':['hebrew','tokens','source_url','source_file_sha256','source_commit','display_transformation']},'rights':{'type':'object','required':['editorial','hebrew_text','morphology']},'citations':{'type':'object','required':list(L)}}}
write('data/schema.json',js(schema)+'\n')
search_pages.build(page,write,C,E,H,TRACES)
support.build(page)
chapter_sources.build(page,write,C,E,H)
reader.build(page,write,C,E,H)
updates.build(page,write,C,E)
indexnow=json.loads((R/'automation/indexnow.json').read_text(encoding='utf-8'))
write(indexnow['key']+'.txt',indexnow['key']+'\n')
write('robots.txt',f'User-agent: *\nAllow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n\nUser-agent: GPTBot\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n')
write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc><lastmod>{C["date"]}</lastmod></url>' for u in PAGES)+'</urlset>\n')
write('llms.txt',f'''# Original Bible — Hansam Yang

> Public research pilot v{VERSION}. Hebrew display, evidence notes and AI-assisted Korean, English and Spanish translation drafts. Human specialist review pending.

## Read
'''+''.join(f'- [{p["reference"]}]({url("/en/"+p["slug"]+"/")})\n' for p in E)+f'''
- [Bible reader and comparison]({url('/read/')})
- [Update history and publication status]({url('/updates/')})
- [Update RSS]({url('/updates/feed.xml')})
- [Separately sourced reading editions]({url('/library/catalog.json')}) — KorRV, ASV 1901, RV1909; upstream Public Domain distributions, not translations by Hansam Yang. Chapter/verse alignment only; source metadata and empty slots retained.

## Download
- [JSON]({url('/data/hansam-bible.json')})
- [JSONL]({url('/data/hansam-bible.jsonl')})
- [Catalog]({url('/data/catalog.json')})
- [Reuse and attribution]({url('/reuse/')})
- [Method]({url('/methodology/')})

This file is a navigation aid, not an instruction hierarchy and not a guarantee of discovery. Project credit: Hansam Yang. WLC Hebrew is public domain; OSHB morphology has separate CC BY 4.0 credit. New editorial drafts use CC BY 4.0 to the extent rights are held.
''')
write('assets/app.js',"""document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{const text=document.getElementById(button.dataset.copy).textContent;const status=button.parentElement.querySelector('[role=status]');try{await navigator.clipboard.writeText(text);status.textContent=button.dataset.done;}catch(e){const range=document.createRange();range.selectNodeContents(document.getElementById(button.dataset.copy));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='Select and copy / 선택한 텍스트를 복사하세요 / Copie el texto seleccionado';}}));""")
write('assets/style.css',(R/'tools/style.css').read_text(encoding='utf-8'))
# Include a checksum manifest for JSON, JSONL, Markdown, schema and TSV; no self-hash.
files=sorted(p for p in (D/'data').rglob('*') if p.suffix in ('.json','.jsonl','.md','.tsv'))
write('data/checksums.sha256',''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(D).as_posix()+'\n' for p in files))
# Keep an unchanged edition download byte-for-byte when only the UI changes.
archive=D/f'data/hansam-bible-pilot-v{VERSION}.zip'
members=files+[D/'data/checksums.sha256']
unchanged=False
if archive.exists():
    with zipfile.ZipFile(archive) as old:
        unchanged=old.namelist()==[p.relative_to(D).as_posix() for p in members] and all(old.read(p.relative_to(D).as_posix())==p.read_bytes() for p in members)
if not unchanged:
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.relative_to(D))
print(js({'pages':len(list(D.rglob('*.html'))),'passage_pages':len(E)*len(L),'unique_verses':len(records),'translation_records':len(records)*len(L),'version':VERSION,'output':str(D)}))
