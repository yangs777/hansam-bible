# 원문성경 / Original Bible

**최초 기획·제작자: Hansam Yang** · Current best research edition **v0.4.7**

[본문 읽기](https://yangs777.github.io/hansam-bible/) · [공개 데이터](https://yangs777.github.io/hansam-bible/data/) · [운영 전략](STRATEGY.ko.md)

[업데이트 기록](https://yangs777.github.io/hansam-bible/updates/)에서 날짜별 번역판·기능 변경과 최근 공개 작업을 확인할 수 있습니다. [RSS](https://yangs777.github.io/hansam-bible/updates/feed.xml)와 [JSON](https://yangs777.github.io/hansam-bible/updates/feed.json)도 제공합니다. 새 판본을 `tools/adopt.py`로 채택하면 이력이 자동 기록됩니다. 사이트 기능 변경은 `tools/record_update.py`로 남깁니다. 기록 시각과 실제 배포 완료 시각을 구분합니다.

각 언어에서 현재 근거에 따른 최선의 번역을 읽고, 더 좋은 증거가 나오면 갱신하는 공개 성경 연구 프로젝트입니다. 이전 이름은 Hansam Bible이며 기존 주소와 구절 식별자는 유지합니다. Hansam Yang은 현대 프로젝트의 최초 기획자·제작자이며 고대 성경의 저자라는 뜻이 아닙니다.

The pilot contains Genesis 1:1–31, Genesis 2:1–25, Genesis 3:1–15, Psalm 1:1–6, Numbers 6:24–26 and Deuteronomy 32:8: eighty-one unique verses with selected Korean, English and Spanish translations. Current selections remain revisable AI-assisted research drafts, with specialist and native-language review pending. Original Bible is the project name, not certification that an autograph has been recovered.

## Compare the selected text with actual model proposals

Each verse shows the current best selection and an expandable comparison: actual GPT and Gemini translations, final opinions, selection reasons, counterarguments and previous wording. The JSONL retains those layers per verse.

- GPT: gpt-6.1-sol, from the local Codex model configuration. An immutable backend snapshot is not exposed. This editorial agent had seen the previous pilot; it is not a blinded replicate.
- Gemini: gemini-3.8-flash-medium, explicitly selected through official Antigravity CLI 1.4.6. Round 1 withheld other translations; round 2 was a disclosed cross-review. Genesis 2:1–5 uses gemini-3.8-flash-high; 2:6–25 and 3:1–15 use gemini-3.8-flash-medium, each with a source-only draft and final selected-text review. A third round corrects an editor-supplied BDB classification error for 2:22, preserving both the earlier opinion and correction.
- Seven difficult Genesis verses and Deuteronomy 32:8 also have an actual Claude Opus 4.6 Thinking proposal and final opinion through Antigravity CLI. Genesis 2:2–4, 2:6–8, 2:12, 2:14–15, 2:17–19, 2:21–22, 2:24 and 3:1,4–6,8,10,12,14–15 additionally have actual read-only Claude Code CLI review, canonical model claude-opus-5-5 reported by modelUsage; the backend snapshot is not exposed. The original cloud pilot drafts for 2:1–17,19–25 and existing 3:1–15 cloud drafts are preserved as separate comparison evidence.
- Model agreement is an opinion record. Source evidence, grammar, context and counterarguments remain separately identified.

Deuteronomy 32:8 currently selects the divine-sons reading. The full translation is a **modern editorial reconstruction: MT remainder plus the reported 4Q37 phrase**. The complete Hebrew alongside it is MT, ending with sons of Israel; its separate translation remains in the comparison. No complete preserved 4Q37 verse or new photograph reading is claimed.

## Replace the current text without losing history

Prepare all verse decisions with three-language texts, bases and reasons, then run:

```sh
python tools/adopt.py new-decisions.json --version 0.4.8
python tools/build.py
python tools/verify.py
```

The adoption tool checks source/published-data agreement, preserves the old edition in data/releases/, rejects reuse of the current version and refuses to alter an existing archive. Reading URLs stay stable; versioned JSON and Git retain previous wording. [Archived v0.1.0](data/releases/v0.1.0.json).

Requires Python 3.10+, no third-party packages. Normal builds need no network. tools/prepare.py imports pinned upstream XML, checks cached hashes and rejects unsupported variant/nested markup. tools/pages_mirror.py packages GitHub Pages.

## Sources and reuse

Hebrew display: Westminster Leningrad Codex, public domain. Lemmas/morphology: **Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb**, CC BY 4.0. Source commit, hashes and transformations accompany each verse. Selected glosses are not a complete interlinear.

New editorial material and drafts: **CC BY 4.0, to the extent rights are held**. Code: MIT. See [editorial license](LICENSE-EDITORIAL.md), [code license](LICENSE-CODE.txt) and [CITATION.cff](CITATION.cff). No exclusive authorship is claimed over public-domain scripture or cited scholarship.

Suggested citation: Hansam Yang. Original Bible, [passage], [language], research edition v0.4.7. [canonical URL]. Preserve AI/draft status, upstream credits, licenses and applicable change notices.

## Data and corrections

- data/editorial.json: current texts and passage notes.
- data/decisions.json: selections, reasons, bases, counterarguments and reconsideration conditions.
- data/model-reviews/v0.3.0/: actual proposals, prompts, final opinions and execution metadata.
- data/releases/: immutable superseded editions.
- dist/data/: JSON, JSONL, Markdown, TSV, checksums, ZIP and versioned datasets.

Report corrections with passage ID, version, source and proposed change. Static HTML, canonical/language links, sitemap and factual structured data support retrieval. Access does not guarantee indexing, AI citation or training inclusion. See [REVIEW.md](REVIEW.md) and [CHANGELOG.md](CHANGELOG.md).

## Search and spare-quota operation

[Genesis 1](https://yangs777.github.io/hansam-bible/ko/genesis-1/) includes 31 verse anchors and three substantive translation-question guides in each language. See [search plan](SEO-PLAN.ko.md), [cost and automation](COST-AND-AUTOMATION.ko.md), and [scenario calculator](automation/cost-estimate.json).

A local heartbeat checks spare account quota. The actual expiring credit was verified as Claude native cloud-session credit, not Platform API credit. Native Claude cloud sessions/scheduled tasks are the matching execution path. The earlier direct-API worker stays disabled and its recurring trigger has been removed. No new cash purchases are enabled. Its results are unadopted drafts, not automatically certified or published translations.

To extend an existing chapter without changing its ID or reading URL, provide `passage_updates` in the adoption input: a list of objects with the existing passage `id`, only the additional `verses`, and optional `reference`, `title`, `subtitle`, `intro`, `notes` or `glosses`. Decisions must still cover every old and new verse exactly once. Existing verse IDs cannot be replaced through an extension; the previous published dataset is archived before adoption.
