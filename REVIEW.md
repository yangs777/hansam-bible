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
