# Changelog

## 0.2.0 Contract Hardening

- Made post-build DOCX inspection part of every successful build and unified source, citation, formatting, anonymous-review, and profile findings.
- Added Profile 2.0 with approval state, provenance source kinds, explicit system fallbacks, bilingual abstract/keyword rules, distinct label/body styles, and independent language counts.
- Implemented safe `output.filename_pattern` placeholders and profile-driven citation default mode with explicit CLI overrides.
- Applied and inspected alignment, character indents, line spacing, paragraph spacing, bold, italic, and keep-with-next at style and actual paragraph/run levels.
- Rejects configured pagination, numbering, legacy separator, prefix, and suffix rules instead of silently ignoring them.
- Added anonymous-build field controls, DOCX package identity scanning, and author metadata scrubbing.
- Unified profile resource resolution and added bounded Obsidian attachment lookup with ambiguity failures.
- Added the machine-readable capability matrix, Profile Coverage reporting, real Pandoc integration tests, regression fixtures, and Windows GitHub Actions.

### Migration

Profile 1.0 remains readable and is migrated in memory. `scripts/migrate_profile.py`
persists the new Profile 2.0 shape. Legacy shared abstract/keyword styles become
language-specific body styles; label styles and separators are recorded as
`system_default` until a journal source or user confirmation replaces them.
