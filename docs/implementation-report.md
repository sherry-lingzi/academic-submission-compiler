# Academic Submission Compiler 0.1.0 实现报告

## 选型与复用

1. 主要工程参考是 `pan4ratte/obsidian-pandoc-gui` 2.2.0。它在被评估的三个重点项目中对 Pandoc 参数、defaults、reference document、Lua filter、Obsidian AST 和 Windows 路径的覆盖最完整。
2. 实际底层是 Pandoc 3.10，而不是另写 Markdown-to-DOCX 引擎。这样复用 citeproc、CSL、DOCX writer、脚注、图像和表格等成熟能力。
3. 直接携带的第三方代码只有 Better BibTeX 9.0.64 官方 self-contained live citation filter，部署 revision `199d652`。ASC 为 Windows 做了两处记录在案的 transport patch：关闭远程 revision check，以 curl 访问 loopback JSON-RPC；citation field 编码未重写。
4. 重新实现的模块包括 Journal Profile schema、profile provenance/conflict、CLI、Markdown/citation lint、合规报告、DOCX formatter、OOXML inspector、profile builder contract 和两个 ASC Lua filters。

## 目录结构

```text
bibliography/                 Better CSL JSON 与 BibTeX 示例
docs/                         架构、语义 Markdown、实现报告
filters/                      Obsidian AST、semantic metadata、BBT live filter
journals/                     两个虚构 journal profiles、CSL、reference.docx、来源
examples/demo-paper/          虚构的中英 metadata、脚注、图像、引用、wikilink 示例
schemas/                      正式 JSON Schema
scripts/                      schema 与示例图生成脚本
src/asc/                      CLI、compiler、profiles、citations、DOCX、intake、compliance
tests/                        pytest 测试
dist/                         DOCX 与 Markdown compliance report
```

## Schema 与编译流程

5. `JournalProfile` 使用 Pydantic 2 定义，并生成 `schemas/journal-profile.schema.json`。Style rule 支持中西文字体、中文字号和 pt、粗斜体、对齐、字符缩进、悬挂缩进、行距、段前后、分页、编号、前后缀、provenance、confidence 和 conflict candidates。
6. explicit 与 inferred style rule 缺少 provenance 时验证失败；unknown 可以不提供证据。多个 candidates 会产生 CONFLICT，profile approval 和 build 均拒绝继续。
7. Static 流程为 preflight → Pandoc AST filters → citeproc + CSL + Better CSL JSON → reference.docx → python-docx/OOXML formatter → DOCX inspection/report。
8. `paper.md` 只读。构建中间文件位于系统临时目录；同一稿件已实际编译为两个期刊产物，标题字号、正文字体和页边距确实不同。

## Citation 与 DOCX

9. Static citation 支持 CSL JSON、BibTeX 和 BibLaTeX；示例使用 `references.json`。citekey lint 覆盖单条、多条、locator 和 narrative citation。
10. CSL-M 检测包含 1.1mlz、Juris-M、default-locale-sort 等扩展标记。`check` 警告，static build 默认拒绝，用户只能通过 Live Mode 或显式 `--allow-csl-m` 继续。
11. Live Mode 已接入本机 Zotero 9.0.6 与 Better BibTeX 9.0.64 的 JSON-RPC。虚构示例 citekey 不在用户真实 library，构建因此按设计 FAIL；post-Pandoc 门禁验证必须存在 `ZOTERO_ITEM CSL_CITATION` 且不得残留 citekey，所以没有保留伪 live 产物。
12. formatter 同时修改 Word styles 和必要的 direct runs。它写入 `w:ascii`、`w:hAnsi`、`w:eastAsia`、`w:cs`，支持字符单位首行/悬挂缩进，并设置 section page size/margins。
13. `reference.docx` 从 approved profile 确定性生成，包含 Pandoc 和 ASC 需要的 Title、Author、Affiliation、Abstract、Keywords、Normal、Body Text、Heading 1-3、Footnote Text、Bibliography、Funding 和 Caption styles。

## Compliance 与 intake

14. Markdown checker 覆盖 metadata、单位、基金、分语言摘要长度、正文字符/词数、关键词数量、bibliography、missing citekey、疑似手写作者年份、CSL-M、缺图、embed、匿名元数据和 profile conflict。
15. DOCX inspector 读取实际 OOXML，验证 Title、Normal、Abstract、Keywords、Bibliography、Heading 1-3 的中英文字体与字号，以及四边页边距。
16. AI Profile Builder 当前完成 provider-neutral `ProfileExtractor`、`MockExtractor`、确定性 TXT/Markdown `TextRuleExtractor`、generated profile、review report 与 explicit approval。真实 LLM provider、PDF/DOCX/HTML adapter 尚未实现；compiler runtime 不依赖 AI。

## 验证结果

17. pytest 共 24 项，全部通过。覆盖 profile、provenance、conflict、citations、YAML、wikilink/embed、DOCX 字体/字号/缩进/页边距、Windows 中文与空格路径、static/live 分离、live field 门禁、compliance 和 intake approval。
18. 已运行 `asc doctor`、两个 profile 的 `asc check`、`asc build` 和 `asc inspect`。Pandoc 3.10、Git 2.53、Zotero 9.0.6、Better BibTeX 9.0.64 可用；Quarto 未安装且为 optional。两份 DOCX 均经 Word/WPS PDF 导出和 Poppler 逐页查看，无乱码、截断、重叠、标题装饰线或泄露的图片路径。
19. 已用虚构 demo 稿生成两种期刊格式的 DOCX 与对应 Markdown reports；`dist/` 中的构建产物默认不纳入版本控制。

## 当前限制与下一步

已知限制是 note embed 不递归展开；intake 尚无 PDF/DOCX/HTML parser 或真实 AI provider；DOCX inspector 还没有遍历每个局部 direct-formatting run、页眉页脚与复杂多 section；live 示例需要 citekey 真正存在于当前 Zotero library 才能生成字段。验证范围内没有未解决的 static build bug。Codex bundled runtime 没有 LibreOffice，因此视觉 QA 改用本机 Word/WPS 隐藏导出 PDF；这不影响项目运行时。

下一步最值得实现的三项功能：

1. PDF/DOCX/HTML 投稿指南解析，加页码或段落级 provenance，并对官方文字与模板形成 candidates/CONFLICT。
2. OpenAI-compatible structured-output extractor，以及逐条人工 review/merge 的交互式 CLI。
3. 扩展 post-build inspector，检查每个正文 run、脚注 XML、bibliography paragraph、页眉页脚、section 和匿名 metadata，并增加真实 Zotero fixture 的 live integration test。
