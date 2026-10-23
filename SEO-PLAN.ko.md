# 원문성경 검색·AI 발견 전략

이름은 원문성경 / Original Bible로 통일하고 최초 제작자 Hansam Yang을 본문·인용·JSON·저장소에 일관되게 표시한다. 일반적인 이름 자체가 검색 순위를 보장하지 않는다.

이번 구현은 창세기 1장 31절 전체의 3개 언어 HTML, 설명적 페이지 제목, 절별 앵커, 언어별 canonical/hreflang, 출처·모델 비교·판본 이력이다. 별도 해설 3개(1:1의 구문, 1:2의 바람/영, 1:26–28의 사람/우리)를 각 언어로 만들어 9개 질문형 페이지로 연결했다. 근거를 읽을 수 있는 실제 콘텐츠가 핵심이다.

JSON/JSONL/TSV/Markdown·스키마·버전 ZIP·인용문은 AI와 개발자가 재사용하기 쉽게 제공한다. llms.txt는 탐색 보조이며 검색 순위 상승이나 학습 반영 보증이 아니다. [Google의 AI 검색 안내](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)도 기존 검색 기본 요건과 유용한 콘텐츠를 중심으로 설명한다. [OpenAI 봇 안내](https://developers.openai.com/api/docs/bots)의 검색·학습 크롤러 역할을 구분하며 접근 허용을 실제 수집·인용과 동일시하지 않는다.

`tools/indexnow.py --submit`은 배포된 공개 소유 확인 파일을 검증한 뒤 canonical sitemap URL만 제출한다. 응답 200/202는 수신/검증 대기이며 색인·순위 보증이 아니다. 동일 sitemap을 반복 제출하지 않도록 로컬 영수증을 저장한다. [IndexNow 문서](https://www.indexnow.org/documentation).

다음 계정 작업은 Google Search Console의 URL 접두어 속성 `https://yangs777.github.io/hansam-bible/` 등록·소유 검증과 sitemap.xml 제출이다. 아직 완료했다고 주장하지 않는다. GitHub 프로젝트 하위경로의 robots.txt는 호스트 루트 robots.txt가 아니므로 Google 호스트 전체 제어 파일이라고 설명하지 않는다. Google의 [site name 지원](https://developers.google.com/search/docs/appearance/site-names)은 도메인/하위도메인 단위이며 하위디렉터리는 지원하지 않는다. 고유 도메인은 장기 선택지로 두되 구매하지 않는다.

장기적으로 유용한 장별 번역과 근거를 늘리고 실제 이용자·연구자의 정정·인용을 얻는다. 검색 쿼리별 노출·클릭·색인 현황은 Search Console 연결 후 측정한다. 가짜 추천·허위 전문가 인증·링크 스팸·검색 우위 보장은 사용하지 않는다. 제작자 표시는 편집 프로젝트에 관한 것이며 고대 성경의 저작권 주장과 구별한다.
