# Third Party Notices

## Better BibTeX Pandoc live citation filter

`filters/zotero.lua` is based on the self-contained deployment at `https://retorque.re/zotero-better-bibtex/exporting/zotero.lua`, deployment revision `199d652`, retrieved 2026-09-09 while Better BibTeX release 9.0.64 was current. Its source is `retorquere/zotero-better-bibtex/pandoc/pandoc-zotero-live-citemarkers.lua`; the repository head inspected for this release was `0d63f96017615306233f34bae379c283024d16cd`. ASC disables the optional remote revision check and uses `curl` instead of `pandoc.mediabag.fetch` for the loopback JSON-RPC request because Pandoc 3.10 can fail to initialize the Windows X509 store even for HTTP. The request, citation processing, and field-generation logic are unchanged. Copyright 2020 Emiliano Heyns. Licensed under the MIT License; the complete license notice remains embedded in the deployed file.

The filter is loaded only for `asc build --live-zotero`. Static builds do not require Zotero or Better BibTeX.
