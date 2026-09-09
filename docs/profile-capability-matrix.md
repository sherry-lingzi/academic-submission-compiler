# Profile 2.0 Capability Matrix

The machine-readable source of truth is `src/asc/capabilities.py`. `supported`
means the value is applied and inspected, `partial` means the documented limit
is reported, and `unsupported` means a configured value makes preflight fail.

| Field | Compiler | Formatter | Inspector | Status |
| --- | --- | --- | --- | --- |
| `font.east_asia` | yes | yes | style + runs | supported |
| `font.latin` | yes | yes | style + runs | supported |
| `font.complex_script` | yes | yes | style only | partial |
| `size` | yes | yes | style + runs | supported |
| `bold`, `italic` | yes | yes | style + label/body runs | supported |
| `alignment` | yes | yes | style + paragraphs | supported |
| `first_line_indent_chars` | yes | yes | style + paragraphs | supported |
| `hanging_indent_chars` | yes | yes | style + bibliography paragraphs | supported |
| `line_spacing` | yes | yes | style + paragraphs + footnote style | supported |
| `space_before_pt`, `space_after_pt` | yes | yes | style | supported |
| `keep_with_next` | yes | yes | style | supported |
| `pagination` | reject | no | no | unsupported |
| `numbering` | reject | no | no | unsupported |
| legacy style `separator` | reject | no | no | unsupported |
| `prefix`, `suffix` | reject | no | no | unsupported |
| `document.page_size`, `margins` | yes | yes | sections | supported |
| `document.text_color` | yes | yes | style/direct-run coverage only | partial |
| `title.default` | yes | yes | style + runs | supported |
| `title.zh`, `title.en` | select by title script | yes | actual title | partial (one title emitted) |
| `abstract.{zh,en}.label/body` | yes | char styles | style + runs | supported |
| `abstract.{zh,en}.count` | yes | n/a | source | supported |
| `keywords.{zh,en}.label/body` | yes | char styles | style + runs | supported |
| `keywords.{zh,en}.count` | yes | n/a | source | supported |
| `keywords.{zh,en}.separator` | Pandoc metadata | yes | actual text | supported |
| anonymous author/affiliation/funding/email/ORCID/correspondence flags | yes | yes | package scan | supported |
| `hide_acknowledgements` | metadata only | yes | package scan | partial (body section not inferred) |
| `citation.default_mode` | yes | n/a | post-build citation gate | supported |
| `output.filename_pattern` | yes | n/a | path safety gate | supported |
| `obsidian.attachment_paths` | yes | resource path | ambiguity/missing gate | supported |

Unknown and `system_default` values may still be executed to produce a usable
document, but their matching inspector result remains `UNKNOWN`; it is never
reported as proof of journal compliance.
