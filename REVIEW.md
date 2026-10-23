# Independent AI review and disposition

2026-10-23 · Reviewer: Antigravity, Gemini 3.8 Flash Medium (visible application response). It reported reading the strategy, editorial data, Hebrew data and source-preparation script. Review was requested as read-only. No specialist certification is claimed.

| Finding | Disposition |
|---|---|
| Raw morphology snapshot needs OSHB credit and license | Accepted. Added attribution and rights in each Hebrew source record. Public exports also carry separate upstream rights. |
| Raw editorial verses need AI draft/basis/review fields | Accepted. Added to each editorial source verse; the public JSONL already preserves these fields. |
| Qere/Ketiv and nested markup may be flattened incorrectly | Accepted as an expansion hazard. Pinned the sample scope and fail closed on nested/unsupported markup. No claim of a general-purpose OSIS editor. |
| Languages differ in tense/literalness | Partly accepted. Psalm 1:1 Korean and Spanish were made closer to the displayed action sequence; Hebrew qatal is not mechanically identical to a modern-language tense. Deuteronomy inheritance wording was aligned. |
| Hebrew variant phrase lacks words translated as 'according to the number' | Accepted. Variant gloss now translates only the displayed phrase 'sons of God'; it is explicitly not a complete verse. |
| Suggested replacing 4Q37 reading with בני אל / reconstructed material | Rejected pending primary verification. The review supplied no checked primary evidence for this replacement. Published Tov report distinguishes an attested/report reading from a conjectured earlier form. The project keeps the reported reading labelled, with direct-image review pending. |
| Need parallel readings rather than a permanently MT-only schema | Accepted for the disputed verse: explicit reading candidates and distinct evidence types. The general record structure does not declare MT universally privileged. |
| Selected glosses mix roots and forms | Accepted. Added form/type and vocalization labels rather than presenting all as identical dictionary entries. |
| Add source cache and error handling | Accepted. Local ignored cache plus pinned hashes, fail-closed preparation and offline deterministic build. |

The review's 'Critical' labels are its assessments, not legal findings. Its claim that all issues could be fixed to achieve complete scholarly/legal integrity was not adopted. Source rights and specialist checks remain separately scoped.

## Terminal review of public data

2026-10-23 · Official Antigravity CLI 1.4.6, structured headless output. The desktop conversation was unavailable in the CLI store; the review brief was transferred to a CLI conversation. No desktop UI control was used for this review.

Antigravity ran a fixed read-only Python fetch of the public Deuteronomy English Markdown, catalog JSON and verse JSONL on raw.githubusercontent.com. It reported HTTP 200 for all three; the three returned SHA-256 hashes match the corresponding committed files.

It recovered the ten requested facts: Hansam Yang attribution, v0.1.0, ten unique verses, Korean/English/Spanish, pending human review, the MT-WLC display reading, the phrase-only “sons of God” comparison, the Open decision, separately scoped upstream/editorial rights, and the public English citation. It reported no new metadata contradictions in those inputs.

One incidental formatting error in its optional citation example is corrected here: an anchor attaches without a space, as `https://yangs777.github.io/hansam-bible/en/deuteronomy-32-8/#v8`. The unanchored canonical citation was correct. The raw AI response is retained locally.

This verifies retrieval and preservation of the requested metadata when URLs are supplied. It does not demonstrate natural search discovery, training inclusion, future citations, or scholarly accuracy of the translations and manuscript judgments.


## v0.2.0 — current selections and model opinions

The project is now 원문성경 / Original Bible, founded by Hansam Yang. Ten verses have actual three-language GPT and Gemini proposals, current selected texts and final opinions. GPT's label comes from the local Codex configuration; Gemini 3.8 Flash Medium was explicitly selected in Antigravity CLI. Gemini's first round withheld other translations; subsequent rounds were disclosed cross-reviews. GPT had already seen the pilot and is not described as blinded.

Gemini revised several initial expressions after review: its Psalm 1:6 Korean typo, over-specified relationship language for ידע, the loss of the stand parallel in Psalm 1:5, unnatural Spanish in Numbers 6:25, and the shifted beneficiary in Numbers 6:26. Its proposal and later opinion are both retained. These actual errors illustrate why AI outputs must remain checkable.

Claude Opus 4.6 Thinking was additionally queried through Antigravity CLI for Deuteronomy 32:8. Its own three-language proposal and qualified support are retained. Its wording is currently selected, including collective humankind wording and more natural allotment/boundary expressions. Claude Code 2.1.308 is a separate installed client awaiting account authentication; the Antigravity response is not labelled a Claude Code response.

The divine-sons reading is now selected provisionally. Its full translation is a modern editorial reconstruction from the MT remainder plus a reported 4Q37 phrase. The complete MT Hebrew and its separate translation remain visible. Reported Greek/4Q37 convergence and the verse 9 allotment context support the choice; the Israel/seventy tradition and lack of direct collation remain counterarguments. The source article is Emanuel Tov, The Sons of Israel or God? — Deuteronomy 32:8 (2023; page updated 2026-10-09), https://www.thetorah.com/article/the-sons-of-israel-or-god-deuteronomy-32-8. The project's choice is an inference from the specified evidence, not a new direct manuscript reading.

Edition replacement preserves the old dataset, rejects current-version overwrite and refuses archive tampering. Those behaviors are exercised on isolated copies. The public JSONL and Markdown retain the selection, model proposals/opinions and earlier wording. AI concurrence is not added to the manuscript witness count.
