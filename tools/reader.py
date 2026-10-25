"""Publish the reading library separately from the versioned editorial dataset."""
import hashlib
import json
import pathlib
import shutil

R = pathlib.Path(__file__).resolve().parents[1]


def build(page, write, config, passages, hebrew):
    target = R / 'dist/library'
    shutil.copytree(R / 'library', target, dirs_exist_ok=True)
    records = {}
    for passage in passages:
        for verse in passage['verses']:
            book, chapter, number = verse['source'].split('.')
            records.setdefault(book, {}).setdefault(chapter, {})[number] = {
                **{lang: verse[lang] for lang in ('ko', 'en', 'es')},
                'he': hebrew[verse['source']]['hebrew'],
                'study': {lang: f'/{lang}/{passage["slug"]}/#v{verse["number"]}' for lang in ('ko', 'en', 'es')},
            }
    write('library/original.json', json.dumps({'version': config['version'], 'author': config['author'], 'records': records}, ensure_ascii=False) + '\n')
    for asset in ('reader.js', 'reader.css'):
        write('assets/' + asset, (R / 'tools' / asset).read_text(encoding='utf-8'))
    write('library/checksums.sha256', ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(R / 'dist').as_posix() + '\n' for p in sorted(target.rglob('*.json'))))
    body = '''<link rel="stylesheet" href="/assets/reader.css">
<section class="reader" id="reader" aria-busy="true">
  <div class="reader-intro"><div><p class="eyebrow">READ / COMPARE / COPY</p><h1>성경 읽기 · 대조</h1><p>같은 절을 나란히 읽고, 필요한 본문만 가져가세요.</p></div><a href="/ko/#passages">원문성경의 번역 근거 ↗</a></div>
  <p class="reader-scope">66권 공개 배포본 3종 · 원문성경 __VERSES__절 / 3개 언어 연구 초안 · 최초 기획·제작 Hansam Yang</p>
  <div id="reader-error" role="alert" hidden></div>
  <div id="reader-controls" hidden>
    <form id="reference-form" class="reference-form"><label for="reference">바로 찾기</label><input id="reference" placeholder="창 1:1-5 또는 John 3:16" autocomplete="off"><button type="submit">이동</button><span id="reference-status" role="status"></span></form>
    <div class="reader-controls">
      <div class="location-controls"><label>성경 책<select id="book"></select></label><label>장<select id="chapter"></select></label><button id="previous" aria-label="이전 장">←</button><button id="next" aria-label="다음 장">→</button><div class="reader-modes" aria-label="읽기 방식"><button id="mode-read" aria-pressed="false">읽기</button><button id="mode-compare" aria-pressed="true">대조</button></div></div>
      <div class="version-controls"><label>첫 번째 성경<select id="left-version"></select></label><label id="right-label">비교 성경<select id="right-version"></select></label><label class="check-label"><input id="show-hebrew" type="checkbox"> 히브리어 표시문</label></div>
      <details class="range-details"><summary>절 범위 · 이 장에서 찾기</summary><div class="range-controls"><label>시작 절<input id="from-verse" type="number" min="1" value="1"></label><span>—</span><label>끝 절<input id="to-verse" type="number" min="1" value="31"></label><button id="apply-range">범위 적용</button><button id="whole-chapter">장 전체</button><label class="chapter-filter">이 장에서 찾기<input id="chapter-filter" type="search" placeholder="단어 입력"></label></div></details>
    </div>
    <section id="paste-panel" hidden><h2>내 번역본 붙여넣기</h2><p>개역개정·새번역·NIV 등은 직접 보유한 본문을 붙여 넣어 대조할 수 있습니다. 절마다 줄을 바꾸고 <code>1 본문</code>처럼 적어 주세요. 번호가 없으면 시작 절부터 한 줄을 한 절로 읽습니다.</p><p><a href="http://holybible.or.kr/" target="_blank" rel="noopener">HolyBible에서 번역본 찾기 ↗</a> · <a href="https://bible.bskorea.or.kr/" target="_blank" rel="noopener">대한성서공회 ↗</a></p><label>붙여넣을 비교본<select id="paste-target"></select></label><label>이번 장의 본문<textarea id="paste-text" rows="5" placeholder="1 태초에…&#10;2 …"></textarea></label><div class="reader-actions"><button id="apply-paste">본문 적용</button><button id="clear-paste">붙여넣기 지우기</button><span id="paste-status" role="status"></span></div><p class="fine">이 내용은 현재 브라우저 메모리에만 남습니다. 서버 전송·자동 저장·공유 링크 포함을 하지 않으며 새로고침하면 지워집니다.</p></section>
    <div class="reading-title"><div><p class="eyebrow" id="reference-eyebrow"></p><h2 id="chapter-title"></h2></div><div><button id="share-link">현재 위치 링크 복사</button><span id="share-status" role="status"></span><input id="share-url" aria-label="현재 위치 공유 주소" readonly hidden></div></div>
    <p id="reading-notice" class="reading-notice"></p>
    <div class="selection-tools"><span id="selection-count">선택 없음 · 표시한 범위 복사</span><button id="select-visible">표시된 절 선택</button><button id="clear-selection">선택 해제</button><button id="copy-quick" class="primary">선택·범위 복사</button><a href="#copy-panel">복사 형식 ↓</a><span id="quick-status" role="status"></span></div>
    <div id="verse-head" class="verse-head" aria-hidden="true"></div>
    <div id="verses" aria-label="성경 본문"></div>
    <p id="empty-result" hidden>이 범위에 일치하는 본문이 없습니다.</p>
    <section class="copy-panel" id="copy-panel"><div><p class="eyebrow">TAKE THE TEXT</p><h2>본문 복사</h2><p>절을 체크하면 해당 절만, 선택하지 않으면 화면에 표시된 범위를 복사합니다. 본문·절 번호 형식은 미공개·빈 절을 제외하며, TSV는 빈 절의 상태도 남깁니다.</p></div><div class="copy-options"><label>가져올 본문<select id="copy-source"><option value="both">두 성경 함께</option><option value="left">첫 번째 성경</option><option value="right">비교 성경</option></select></label><label>복사 형식<select id="copy-format"><option value="numbered">절 번호 포함</option><option value="plain">본문만</option><option value="tsv">비교표 · TSV</option></select></label><label class="check-label"><input id="copy-credit" type="checkbox" checked> 출처·판본 포함</label></div><label>복사 미리보기<textarea id="copy-preview" rows="6" readonly></textarea></label><div class="reader-actions"><button id="copy-text" class="primary">본문 복사</button><button id="download-text">텍스트 내려받기</button><span id="copy-status" role="status"></span></div></section>
    <details class="reader-sources"><summary>수록 범위 · 출처 · 대조 기준</summary><div id="source-list"></div><p>절 번호를 기준으로 나란히 표시합니다. 판본에 따라 절 묶음·번호·본문 계열이 달라 정확한 문장 대응을 뜻하지 않습니다. 배포본의 빈 절은 ‘배포본에 별도 본문 없음’으로 표시하며 다른 판본의 말로 채우지 않습니다.</p><p>개역한글 공개 배포본의 원출처 표기는 ‘KorRV: 개역성경’입니다. 1961년 인쇄본과 대조 교정한 디지털 판본이라고 주장하지 않습니다. <a href="https://www.biblekorea.kr/bbs/content.php?co_id=subpage2_3_4_1">대한성서공회 권리 안내 ↗</a></p><p>원문성경: Hansam Yang의 AI 보조 연구 초안 v__VERSION__, 전문가 검수 전. 새 편집·번역 자료는 권리 보유 범위에서 CC BY 4.0. WLC 히브리어 표시문은 public domain. 비교용 기존 번역본의 번역자는 Hansam Yang이 아닙니다.</p><p><a href="/library/catalog.json">읽기 라이브러리 목록 JSON</a> · <a href="/library/checksums.sha256">읽기 라이브러리 SHA-256</a> · <a href="/reuse/">원문성경 재사용 안내</a></p></details>
  </div><p id="reader-loading" role="status">성경 목록을 불러오는 중입니다…</p>
  <noscript><p>대조 화면에는 JavaScript가 필요합니다. <a href="/ko/#passages">원문성경 본문</a>과 <a href="/library/catalog.json">공개 배포본 데이터</a>는 직접 열 수 있습니다.</p></noscript>
</section><script type="module" src="/assets/reader.js"></script>'''
    for asset in ('reader.js', 'reader.css'):
        fingerprint = hashlib.sha256((R / 'tools' / asset).read_bytes()).hexdigest()[:12]
        body = body.replace('/assets/' + asset + '"', '/assets/' + asset + '?v=' + fingerprint + '"')
    page('/read/', '성경 읽기·대조 — 개역한글, ASV, RV1909, 원문성경', body, 'ko', description='66권 성경 읽기, 절별 번역 대조, 원문성경 비교와 본문·절 번호·TSV 복사. 한국어·영어·스페인어 공개 배포본.')
