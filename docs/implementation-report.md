# Academic Submission Compiler 0.2.0 Implementation Report

## Release outcome

0.2.0 hardens the existing Pandoc-centered architecture instead of replacing it.
Every successful build now runs source checks, Pandoc, deterministic DOCX
formatting, post-build inspection, and one unified report. A DOCX failure makes
the final build status FAIL regardless of the source result.

## Contract changes

Profile 2.0 adds `profile_status`, `approved_at`, `source_kind`, localized title
rules, bilingual abstract/keyword variants, separate label/body rules, per-language
counts, keyword separators, anonymous identity flags, and Obsidian attachment
paths. This is a schema-breaking change, but Profile 1.0 remains readable through
an explicit in-memory migration. `scripts/migrate_profile.py` persists the 2.0
shape; it marks label formatting, English count conversions, and separators as
system fallbacks instead of inventing journal evidence.

Approval now rejects conflicts and, by default, unknown requirements. Users must
pass `--allow-unknown` to record an informed approval. Build accepts only an
approved profile.

## Executed and inspected fields

The formatter and inspector now share the same rule mapping. East Asian and Latin
fonts, size, bold, italic, alignment, first-line and hanging character indents,
line spacing, spacing before/after, and keep-with-next are applied and checked.
Inspection covers style definitions and actual paragraphs/runs. Bibliography
paragraphs and `word/footnotes.xml` are checked separately. Page size and every
margin are checked from actual sections.

`pagination`, `numbering`, legacy style-level `separator`, `prefix`, and `suffix`
remain in the migration model but are unsupported. Configuring any of them makes
preflight fail with its exact field path. The complete classification is in
`docs/profile-capability-matrix.md` and its machine-readable source is
`src/asc/capabilities.py`.

## Unknown requirements and fallbacks

`confidence: unknown` means the journal requirement is unknown. `source_kind:
system_default` records a value ASC may use to produce a usable document. A
matching generated value is reported as UNKNOWN and described as a fallback,
never as journal compliance. Reports include explicit, inferred, user-confirmed,
unknown, system-default, unsupported, and conflict counts without a misleading
percentage score.

## Bilingual metadata

Chinese and English abstracts and keywords have independent rules and counts.
Chinese defaults to character counting and English to word counting when the
journal rule is unknown; keyword lists are counted independently as items.
Pandoc receives each Profile separator as metadata, removing the former hardcoded
Chinese delimiter. Distinct DOCX character styles are emitted for each label and
body, and the inspector verifies those styles on actual runs.

## Anonymous review

Anonymous builds respect the individual author, affiliation, funding, email,
ORCID, correspondence, and acknowledgement flags. The formatter clears DOCX
creator and last-modified-by properties. Post-build inspection scans document,
header, footer, footnote, comment, and property XML for configured identity
values, generic emails, and ORCIDs. Acknowledgements stored as metadata are
supported; inferring and removing an arbitrary body section remains partial.

## Paths and attachments

Bibliography, CSL, reference DOCX, filters, and journal resources use one resolver:
absolute path, existing journal-local path, then project-relative path. Tests cover
journal-local, project-relative, absolute, Chinese, and space-containing paths.
Obsidian embeds resolve in manuscript-directory, configured attachment-directory,
then vault-relative order. Multiple exact candidates fail as AMBIGUOUS; ASC does
not recursively scan an unrestricted vault.

## Tests and CI

The suite includes real Pandoc → citeproc → DOCX → formatter → inspector tests,
a deliberately wrong title-size regression, anonymous package scanning, bilingual
counts, custom separator behavior, unknown fallback reporting, unsupported fields,
safe filenames, citation edge cases, resource paths, and Windows Chinese paths.
GitHub Actions runs on `windows-latest`, installs Python and Pandoc, runs pytest,
then executes the real demo build and standalone inspector. Zotero Live Mode stays
out of CI; command construction, preflight, and Word-field validation remain tested.

## Remaining limits and next phase

Text-color run coverage, complex-script font inspection, bilingual title emission,
and acknowledgement body-section removal are partial. Note embeds remain visible
placeholders. Live Zotero requires a real local library. PDF/DOCX/HTML guideline
parsing and a real LLM provider are intentionally deferred. With the 0.2.0
contract and regression gates in place, 0.3.0 AI Journal Intake can begin next,
provided new extractors emit provenance-aware Profile 2.0 data and do not bypass
approval.
