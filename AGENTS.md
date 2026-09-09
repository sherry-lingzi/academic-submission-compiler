# Repository guidance

- Preserve Markdown as the manuscript source of truth and Zotero exports as the bibliography source of truth.
- Do not modify manuscripts during builds. Use temporary files, Pandoc AST filters, and deterministic DOCX post-processing.
- Every explicit or inferred journal rule needs provenance. Unknown rules must stay unknown.
- Static citation mode must remain independent of Zotero. Live mode must fail clearly when Zotero or Better BibTeX is unavailable.
- Use `pytest` and run the example CLI workflow after changes that affect profiles, compilation, citations, Markdown, or DOCX.
- Keep Windows paths, UTF-8, spaces, and Chinese filenames covered by tests.

