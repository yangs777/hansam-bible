"""Publish chapter-level source photographs without rewriting translation editions."""
import hashlib
import html
import json
import pathlib
import shutil
from urllib.parse import urlparse

R = pathlib.Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def href(value):
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') and not (value.startswith('/') and not value.startswith('//')):
        raise ValueError('Unsupported source link')
    return esc(value)


def load():
    return json.loads((R / 'data/chapter-sources.json').read_text(encoding='utf-8'))


def chapter_url(chapter):
    return '/sources/' + chapter['slug'] + '/'


def photos_url(chapter):
    return chapter_url(chapter) + 'photos/'


def verse_ranges(numbers):
    groups = []
    for n in sorted(set(numbers)):
        if groups and n == groups[-1][-1]+1:
            groups[-1].append(n)
        else:
            groups.append([n])
    return ', '.join(str(g[0]) if len(g)==1 else f'{g[0]}–{g[-1]}' for g in groups)


def reader_index():
    return {c['key']: {'url': chapter_url(c), 'label': c['basis_label'],
                       'photo_url': photos_url(c),
                       'photo_count': len(c['photos']), 'published_verses': c['published_verses']}
            for c in load()['chapters']}


def passage_links(passage, lang):
    names = {'ko': ('사용 원문·내역', '사본 사진'), 'en': ('Textual sources', 'Manuscript photographs'),
             'es': ('Fuentes del texto', 'Fotografías del manuscrito')}[lang]
    keys = list(dict.fromkeys('.'.join(v['source'].split('.')[:2]) for v in passage['verses']))
    index = reader_index()
    return ''.join(f'<p class="chapter-source-links"><span>{esc(index[k]["label"])}</span> · '
                   f'<a href="{href(index[k]["url"])}#basis">{names[0]} ↗</a> · '
                   f'<a href="{href(index[k]["photo_url"])}">{names[1]} ↗</a></p>'
                   for k in keys if k in index)


def link(url, label):
    return f'<a href="{href(url)}" target="_blank" rel="noopener">{esc(label)} ↗</a>'


def build(page, write, config, passages, hebrew):
    data = load()
    if len({c['key'] for c in data['chapters']}) != len(data['chapters']):
        raise ValueError('Duplicate chapter-source registration')
    published = {v['source'] for p in passages for v in p['verses']}
    registered = {f'{c["key"]}.{n}' for c in data['chapters'] for n in c['published_verses']}
    if published != registered:
        raise ValueError('Chapter-source scope must match the published editorial verses')
    if data['electronic_source']['commit'] != config['source_commit']:
        raise ValueError('Chapter sources must use the actual pinned text version')
    assets = {}
    for chapter in data['chapters']:
        covered = {n for p in chapter['photos'] for n in p['covered_verses']}
        if covered != set(chapter['published_verses']):
            raise ValueError('Photograph index must cover exactly the published chapter scope')
        for photo in chapter['photos'] + chapter['additional_sources']:
            if photo.get('preview'):
                path = (R / photo['preview'].lstrip('/')).resolve()
                if not path.is_relative_to(R / 'assets/manuscripts'):
                    raise ValueError('Unexpected photo path')
                if hashlib.sha256(path.read_bytes()).hexdigest() != photo['preview_sha256']:
                    raise ValueError('Source photograph checksum mismatch')
                assets[path] = photo['preview_sha256']
    for path in assets:
        dest = R / 'dist' / path.relative_to(R)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    write('sources/catalog.json', json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    write('sources/checksums.sha256', ''.join(f'{digest}  {p.relative_to(R).as_posix()}\n' for p, digest in sorted(assets.items())))
    write('assets/sources.css', (R / 'tools/sources.css').read_text(encoding='utf-8'))
    css = '<link rel="stylesheet" href="/assets/sources.css">'
    cards = ''.join(f'<a class="source-index-card" href="{chapter_url(c)}"><span>{esc(c["title_ko"])}</span>'
                    f'<small>{esc(c["basis_label"])} · 사본 사진 {len(c["photos"])}면</small>'
                    f'<small>공개 범위: {verse_ranges(c["published_verses"])}절</small></a>' for c in data['chapters'])
    page('/sources/', '장별 사용 원문과 사본 사진', css + '<section class="document source-page">'
         '<p class="eyebrow">원문과 사진</p><h1>어떤 본문을<br>어떻게 읽었는가</h1>'
         '<p class="lead">사용한 전자 원문, 대응 사본 사진, 채택한 읽기와 남은 확인 범위를 장별로 살펴봅니다.</p>'
         f'<p>{esc(data["scope_ko"])}</p><div class="source-index-grid">{cards}</div>'
         '<p>사본은 전승된 복사본입니다. 저자의 자필원본이 발견되었다는 뜻이 아닙니다. '
         '사진을 연결한 시점과 번역에 그 사진을 실제 사용한 시점도 구분합니다.</p></section>', 'ko')
    m = data['manuscript']
    for c in data['chapters']:
        base = chapter_url(c)
        refs = [f'{c["key"]}.{n}' for n in c['published_verses']]
        source_urls = sorted({hebrew[r]['source_url'] for r in refs})
        photos = ''
        for photo in c['photos']:
            photos += f'''<figure class="source-photo" id="{esc(photo['id'])}">
<a class="photo-open" href="{href(photo['original_url'])}" target="_blank" rel="noopener" aria-label="{esc(c['title_ko'])} 사본 {esc(photo['folio_label'])} 원본 해상도로 보기">
<img src="{href(photo['preview'])}" width="{photo['width']}" height="{photo['height']}" loading="lazy" alt="레닌그라드 사본 {esc(photo['folio_label'])}, {esc(photo['indexed_range'])}에 대응하는 실제 본문 사진"></a>
<figcaption><h3>{esc(photo['folio_label'])}</h3><p class="source-scope">이 장의 대응: {esc(photo['chapter_scope_ko'])}</p>
<p>사진 전체의 색인 범위: {esc(photo['indexed_range'])}</p><p>{esc(photo['mapping_method_ko'])}</p>
<p class="source-photo-links">{link(photo['original_url'], '원본 해상도 사진')}{link(photo['commons_page'], '사진 출처·권리')}{link(photo['mapping_source'], '구절 대응 색인')}</p>
<details><summary>사진 확인 범위와 출처</summary><p>{esc(photo['inspection_status_ko'])}</p><p>{esc(photo['credit'])}</p>
<p>{esc(photo['image_transformation_ko'])}</p><p>권리: Wikimedia Commons 파일 안내의 Public Domain Mark / PD-Art. 사진은 원문성경의 새 저작물로 표시하지 않습니다.</p>
<p>원본 파일 SHA-256: <code>{esc(photo['original_sha256'])}</code></p></details></figcaption></figure>'''
        table = ''.join(f'<tr><th><a href="{photos_url(c)}#{esc(p["id"])}">{esc(p["folio_label"])}</a></th>'
                        f'<td>{esc(p["indexed_range"])}</td><td>{esc(p["chapter_scope_ko"])}</td></tr>' for p in c['photos'])
        explanation = ''.join(f'<li>{esc(s)}</li>' for s in c['explanation_ko'])
        traces = ''.join(f'<li><a href="/read/?book={c["book"]}&amp;chapter={c["chapter"]}&amp;from={n}&amp;to={n}&amp;hebrew=1">{n}절 ↗</a>'
                         f'<p lang="he" dir="rtl">{esc(hebrew[c["key"]+"."+str(n)]["hebrew"])}</p></li>' for n in c['published_verses'])
        extras = ''
        extra_photos = ''
        for s in c['additional_sources']:
            picture = (f'<a href="{href(s["url"])}" target="_blank" rel="noopener"><img src="{href(s["preview"])}" loading="lazy" alt="{esc(s["name"])} 실제 인쇄면 스캔"></a>' if s.get('preview') else '')
            if picture:
                extra_photos += f'<figure class="source-extra">{picture}<figcaption>{esc(s["name"])} · {esc(s["caption_ko"])}<p>{esc(s["rights_ko"])}</p></figcaption></figure>'
            extras += f'<article class="source-extra"><h3>{esc(s["name"])}</h3><p class="source-scope">{esc(s["role_ko"])}</p>' \
                      f'<p>{esc(s["caption_ko"])}</p><p>{link(s["url"], "자료·사진 열람")} · {link(s["evidence_url"], "판독·선택 근거")}</p><p class="fine">{esc(s["rights_ko"])}</p></article>'
        history = f'''<section id="history"><h2>어디에 있으며, 언제 만들어졌는가</h2><dl class="source-facts">
<dt>사본</dt><dd>{esc(m['name_ko'])} · {esc(m['shelfmark'])}</dd><dt>형태</dt><dd>{esc(m['type_ko'])}</dd>
<dt>현재 소장처</dt><dd>{esc(m['location_ko'])}</dd><dt>제작 시기·장소</dt><dd>{esc(m['date_ko'])}</dd>
<dt>발견·입수</dt><dd>{esc(m['discovery_ko'])}</dd><dt>사진</dt><dd>{esc(m['photography_ko'])}</dd></dl>
<p>{link(m['history_source'], '소장기관 목록')} · {link(m['photography_source'], '촬영 기관 설명')}</p><p class="fine">{esc(m['history_evidence_ko'])}</p></section>'''
        trace_note = ('아래는 표시용 WLC/OSHB의 MT 대조문입니다. 채택 번역의 하나님의 아들들 어구는 이 MT 대조문에 없으며, 보고된 4Q37 어구를 따로 채택했습니다. 이 대조문이나 사진을 채택 번역 전체의 단일 원본으로 보아서는 안 됩니다.'
                      if c['key']=='Deut.32' else '아래는 사진에서 새로 전사한 문장이 아니라, 번역에 사용한 고정 WLC/OSHB 전자 본문입니다.')
        body = f'''{css}<section class="document source-page"><a class="breadcrumb" href="/sources/">← 장별 원문·사진 목록</a>
<p class="eyebrow">사용 원문과 대응 사진 · 번역 판본 v{esc(config['version'])}</p><h1>{esc(c['title_ko'])}<br><span>사용 원문·사본 사진</span></h1>
<p class="lead">{esc(c['basis_ko'])}</p><nav class="source-jumps" aria-label="원문 자료 항목"><a href="#basis">사용 원문</a><a href="{photos_url(c)}">사본 사진 보기</a><a href="#history">소장·발견 기록</a><a href="#trace">절별 입력 본문</a></nav>
<section id="basis"><h2>이 장에서 무엇을 사용했는가</h2><p>{esc(data['electronic_source']['relationship_ko'])}</p><ol class="source-explanation">{explanation}</ol>
<div class="source-basis-links">{''.join(link(u, '실제 입력 전자 원문 XML') for u in source_urls)} · {link(data['electronic_source']['repository'], 'WLC / OSHB 자료 설명')}</div>
<p class="fine">고정 버전: <code>{esc(config['source_commit'])}</code> · {esc(data['electronic_source']['rights_ko'])}</p></section>
<section id="photos"><h2>대응 사본과 구절 범위</h2><p>사진은 별도 화면에서 원하는 분만 열어볼 수 있습니다. 아래 대응은 공식 색인의 장·절 범위이며, 특정 단어의 좌표를 확정한 표시는 아닙니다. 경계절은 두 면에 나뉠 수 있습니다.</p>
<p><a class="source-photo-button" href="{photos_url(c)}">사본 사진 {len(c['photos'])}면 보기 ↗</a></p>
<div class="source-table-wrap"><table><thead><tr><th>사본 면 · 사진 열기</th><th>사진 전체 범위</th><th>현재 공개 본문과 대응</th></tr></thead><tbody>{table}</tbody></table></div></section>
{('<section id="additional"><h2>별도로 사용·참고한 자료</h2>'+extras+'</section>') if extras else ''}{history}
<section id="trace"><h2>절별 입력·대조 히브리어</h2><p>{esc(trace_note)} 클릭하면 해당 절의 읽기 화면으로 이동합니다.</p><details><summary>공개된 {len(refs)}절의 입력·대조 본문 펼치기</summary><ol class="source-trace">{traces}</ol></details></section>
<p class="fine">사진 자료 연결: {esc(data['registered_at'])}. 최초 번역 당시의 사진 직접 판독으로 소급하지 않습니다. <a href="/sources/catalog.json">전체 출처·사진 기록 JSON</a> · <a href="/sources/checksums.sha256">사진 미리보기 체크섬</a></p></section>'''
        page(base, c['title_ko'] + ' 사용 원문·원본 사진', body, 'ko', description=c['title_ko'] + '의 사용 저본, 실제 사본 사진과 구절 대응, 소장처 및 확인 범위.')
        gallery = f'''{css}<section class="document source-page"><a class="breadcrumb" href="{base}">← {esc(c['title_ko'])} 사용 원문·설명</a>
<p class="eyebrow">별도 사진 열람</p><h1>{esc(c['title_ko'])}<br><span>대응 사본 사진</span></h1>
<p>이 장의 선택 본문: {esc(c['basis_ko'])}. 아래 사진은 대응 사본 면이며, 최초 번역 당시의 사진 직접 판독으로 소급하지 않습니다. 사진을 누르면 제공처의 원본 해상도 파일이 열립니다.</p>
{('<p class="source-scope">이 사진은 MT 대조 자료입니다. 채택 번역의 하나님의 아들들 어구를 보여주는 4Q37 사진이 아닙니다. 4Q37의 해당 조각·행 직접 판독은 미완료입니다.</p>') if c['key']=='Deut.32' else ''}
<p>공식 색인에 따른 장·절 범위 대응이며 단어별 전면 대조 완료를 뜻하지 않습니다. 경계절은 두 면에 나뉠 수 있습니다. <a href="{base}#basis">채택한 읽기와 실제 사용 내역</a> · <a href="{base}#history">소장·발견 기록</a></p>
<div class="source-photo-grid">{photos}</div>{('<section><h2>별도 인쇄판 사진</h2>'+extra_photos+'</section>') if extra_photos else ''}</section>'''
        page(photos_url(c), c['title_ko'] + ' 사본 사진 보기', gallery, 'ko', description=c['title_ko'] + '에 대응하는 실제 사본 사진을 별도 화면에서 열람합니다.')
