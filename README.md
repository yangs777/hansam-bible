# Hansam Bible — Biblical Textual Origins

**Hansam Yang** · founder, responsible editor and publisher · Research pilot **v0.1.0**

[Read the pilot](https://yangs777.github.io/hansam-bible) · [Open data](https://yangs777.github.io/hansam-bible/data/) · [한국어 실행 전략](STRATEGY.ko.md)

This project traces biblical words and evidence across languages. The pilot contains **Psalm 1:1–6, Numbers 6:24–26 and Deuteronomy 32:8**: 10 unique verses with newly written AI-assisted Korean, English and Spanish drafts. It is **not** a completed critical edition, a recovered autograph, or a human-certified translation. External Hebrew, textual-critical and native-language review is pending.

Hansam Yang identifies the modern editorial project; authorship of ancient scripture or of cited scholarship is not claimed. No credentials or institutional endorsement are implied.

## Reuse

New editorial material and translation drafts: **CC BY 4.0, to the extent rights are held**. See [LICENSE-EDITORIAL.md](LICENSE-EDITORIAL.md). Code: [MIT](LICENSE-CODE.txt).

Hebrew display: Westminster Leningrad Codex, public domain. Lemmas/morphology: **Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb**, CC BY 4.0. Every exported verse includes scope-specific rights and upstream credit.

Suggested citation: `Hansam Yang. Hansam Bible, [passage], [language], research pilot v0.1.0. [canonical URL].` AI assistance and draft status should remain clear. Include licensing and change notices as required. Citation metadata is provided in [CITATION.cff](CITATION.cff); no DOI has been assigned.

## Files and reproducibility

- `data/editorial.json`: translation drafts and evidence notes.
- `data/hebrew.json`: selected Hebrew display, OSHB morphology, immutable upstream commit, XML hashes and display transformations.
- `dist/data/`: public JSON, JSONL, TSV, Markdown, schema, checksums and ZIP.
- `tools/prepare.py`: retrieve selected source verses from the pinned commit. It stops on unsupported variant/nested markup.
- `tools/build.py`: render all languages and exports from the same source.
- `tools/verify.py`: verify source/codepoint preservation, rights, draft labels, language links, IDs, checksums and internal links.

Requires Python 3.10+, no third-party packages:

```sh
python tools/prepare.py  # network needed only to retrieve pinned source
python tools/build.py
python tools/verify.py
python -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Build uses committed selected data and needs no network. Source fetching caches raw XML under ignored `private/`; the public selected records retain the pinned source URLs and complete-file SHA-256 values. A cache hit must match those previously recorded hashes.

## Evidence and corrections

MT-WLC is a provisional display basis for these examples, not an absolute preference for all manuscripts. Deuteronomy 32:8 stays **Open**. Its reported 4Q37 phrase is not presented as a new direct reading of a manuscript photograph; no complete verse is attributed to that fragment here. Alternative readings are kept separate from the display translation. Selected glosses are not a complete word-aligned interlinear.

Report a correction with passage ID, version, source and proposed change. AI agreement alone does not validate a scholarly claim. See [REVIEW.md](REVIEW.md) and [CHANGELOG.md](CHANGELOG.md).

## AI and search access

HTML contains the text without JavaScript; JSONL carries provenance per verse. Sitemap, robots.txt, canonical/hreflang links and factual JSON-LD are included. `llms.txt` is an optional navigation index, not a command to agents or a promise of search visibility, citation or training inclusion. See the strategy for evaluation and scaling gates.

## 한국어

이 프로젝트는 Hansam Yang의 **성경 원문추적 직독직해** 공개 연구 시험판입니다. 실제 사본·복원·번역·해석을 구별하고, 새 증거에 따라 판정과 번역을 갱신합니다. 현재 번역은 전문가 검수 전 AI 보조 초안입니다.
