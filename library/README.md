# Separately sourced reading editions

These files support the Bible reader. They are **not** new translations by
Hansam Yang, editorial adoptions, or manuscript verification. They remain
separate from the versioned Original Bible datasets and their CC BY notices.

The three 66-book distributions are KorRV (upstream title: 개역성경), ASV (1901),
and SpaRV / Reina-Valera (1909). Upstream marks each Public Domain.
`catalog.json` records exact upstream URLs, rights statements, pinned commit,
SHA-256 of downloaded JSON, verse counts and empty verse slots.

Rebuild explicitly with `python tools/import_library.py`; normal site builds
use these committed files without downloading scripture. The importer retains
every text string and verse number, including empty slots. It does not correct,
modernize, harmonize, or fill missing text. KorRV has not been collated here
against a printed 1961 edition. Chapter/verse alignment is numerical only;
verse grouping and textual bases can differ.

Benchmark: [HolyBible](http://holybible.or.kr/) informed the version → book →
chapter navigation and verse-aligned comparisons. Its licensed modern Bible
texts, design assets and code were not copied. Modern versions can be opened
at their providers or pasted by the reader into an in-memory comparison.

`dist/library/original.json` is generated from the project's current selected
translations and WLC display; it is labeled with the editorial version,
research-draft state and scoped attribution in the reader. Reading UI changes
do not adopt a new translation edition.
