# Academic Submission Compiler 学术投稿编译器

Academic Submission Compiler 把一份语义化 Markdown 母版编译为不同期刊要求的 DOCX，并同时生成可追溯的合规报告。项目的原则是 **Write semantically. Compile typographically.** 写作时维护内容和语义，投稿格式在编译阶段由确定性代码完成。

当前版本是 **0.2.0 Contract Hardening**。`asc build` 已形成 Markdown preflight → Pandoc → DOCX formatter → DOCX inspector → unified compliance report 的闭环。Profile 中的可执行规则必须被 formatter 与 inspector 消费；暂未实现的字段会阻止构建，未知规则与系统 fallback 不会冒充期刊合规。

已实现：Profile 2.0、静态引用、双语摘要/关键词规则、标签与正文字符样式、独立语言计数、安全输出命名、匿名字段控制、实际段落/run/脚注/参考文献检查和 Windows CI。实验性功能：Better BibTeX Zotero Live Mode 与确定性 TXT/Markdown intake。计划功能：真实 LLM、PDF/DOCX 投稿指南识别、GUI 和期刊数据库。

## 工作流

```text
Zotero + Better BibTeX
        ↓ Better CSL JSON
Obsidian Semantic Markdown [@citekey]
        ↓
approved Journal Profile
        ↓
Pandoc structure and citations
        ↓ reference.docx
deterministic DOCX formatter
        ↓
DOCX and compliance report
```

Markdown 是论文正文唯一母版，Zotero 导出的 bibliography 是文献元数据唯一母版。Word 是投稿产物，不应反向成为内容源。引用保留为 `[@citekey]`，因此更换期刊时无需修改正文。

## Windows 安装

需要 Python 3.10+、Pandoc 和 Git。Static Mode 不需要运行 Zotero。

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\asc.exe doctor
```

Better BibTeX 推荐把 Zotero collection 自动导出为 `bibliography/references.json`，格式选择 Better CSL JSON 并启用 Keep updated。BibTeX/BibLaTeX 仍可用，但 CSL JSON 避免了来回映射造成的信息损失。

## 支持的文件格式

| 用途 | 格式 | 支持状态 | 说明 |
| --- | --- | --- | --- |
| 论文母版 | `.md` | 已支持 | UTF-8 或 UTF-8 BOM；支持 YAML front matter、Pandoc citations、脚注、标题、表格、普通 Markdown 图片和 Obsidian wikilink/embed 语法。Markdown 始终是正文唯一母版。 |
| Journal Profile | `.yaml` | 已支持 | 使用 Profile 2.0 schema；正式文件名为 `profile.yaml`，生成后待审文件为 `profile.generated.yaml`。 |
| 文献数据库 | `.json` | 已支持、推荐 | CSL JSON / Better CSL JSON；静态模式不依赖正在运行的 Zotero。 |
| 文献数据库 | `.bib` | 已支持 | BibTeX 或 BibLaTeX；由 Pandoc citeproc 编译，ASC 同时检查 citekey。 |
| 引用样式 | `.csl` | 已支持 | 标准 CSL 用于静态模式；检测到 CSL-M 专用标记时默认拒绝静默编译，可人工核验后使用 `--allow-csl-m`。 |
| Word 样式模板 | `.docx` | 已支持 | `reference.docx` 提供 Pandoc 样式基础；ASC 随后确定性校正并检查实际 DOCX。 |
| 图片附件 | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp` | 已支持 | 可从稿件目录、`obsidian.attachment_paths` 或 vault-relative 精确路径解析；同名多匹配会报告 `AMBIGUOUS`。 |
| 投稿指南 intake | `.txt`, `.md` | 实验性 | 当前仅提取少量明确书写的格式规则，生成的 Profile 必须人工检查和批准。 |
| 投稿成品 | `.docx` | 已支持 | static 和 Zotero Live 两种模式；Live 输出默认增加 `-live.docx`，避免覆盖静态成品。 |
| 合规报告 | `.md` | 已支持 | 与 DOCX 同名生成 `*-report.md`，包含源稿、引用、实际 DOCX、匿名审稿和 Profile Coverage。 |

当前不支持把 `.docx`、`.pdf` 或 `.html` 当作论文母版，也不输出 PDF、LaTeX 或 HTML 投稿成品。PDF/DOCX/HTML 投稿指南解析仍是计划功能；普通笔记 wikilink 可保留为文本，但递归展开 Obsidian 笔记 embed 尚未实现。

## 示例

```powershell
asc doctor
asc check examples/demo-paper/paper.md --journal example-humanities-journal
asc build examples/demo-paper/paper.md --journal example-humanities-journal
asc inspect dist/demo-paper-example-humanities-journal.docx --journal example-humanities-journal
```

同一源稿可直接切换 profile：

```powershell
asc build examples/demo-paper/paper.md --journal journal-a
asc build examples/demo-paper/paper.md --journal journal-b
```

仓库内可直接验证两个虚构 profile：`example-humanities-journal` 使用 12pt 宋体正文和 25.4/31.7mm 页边距，`example-compact-journal` 使用 10.5pt 仿宋正文和 20/25mm 页边距。

编译器不修改 `paper.md`。中间 DOCX 写入系统临时目录，最终文件进入 `dist/`。`build` 已自动运行 post-build inspection；`inspect` 保留为独立调试命令。

构建报告固定包含 Source / Markdown Compliance、Citation Compliance、DOCX Formatting Compliance、Anonymous Review、Profile / Unknown Rules 与 Profile Coverage。只要实际 DOCX 有一项 FAIL，最终状态就是 FAIL，即使源稿 preflight 已通过。

## Static Mode 与 Zotero Live Mode

Static Mode 使用 Pandoc citeproc、bibliography 和 journal CSL。它最适合最终投稿、CI 和可重复构建，也是默认模式。

```powershell
asc build paper.md --journal journal-id
```

Live Mode 使用 Better BibTeX 官方 `zotero.lua` 生成 Word 中可刷新的 Zotero citation fields，适合导师批改、合作者协作和返修阶段。它要求 Zotero 与 Better BibTeX 正在运行；preflight 失败时不会生成半成品。未指定模式时使用 `citation.default_mode`；`--static` 与 `--live-zotero` 可显式覆盖 Profile。

```powershell
asc build paper.md --journal journal-id --live-zotero
```

Live Mode 不改变 Markdown，但 Word 或 Zotero 版本组合仍可能有上游限制。最终提交前应在 Microsoft Word 中打开并执行 Zotero Refresh。
Live 产物使用 `-live.docx` 后缀，避免覆盖同一次写作的 static 成品。

## CSL 与 reference.docx

CSL 决定引用和参考文献内容如何呈现；`reference.docx` 决定 Word paragraph/character styles 与页面属性。两者不能互相替代。Pandoc 先生成文档结构，ASC formatter 再校正中西文字体、字号、段落缩进、行距和页边距。

中文 CSL 可能依赖 CSL-M 或 citeproc-js 扩展。`asc check` 会发出 warning，static build 默认拒绝检测到的 CSL-M 样式，并建议 Live Mode。只有人工确认 Pandoc 输出正确后才应使用 `--allow-csl-m`。

## Journal Profile

正式 schema 位于 `schemas/journal-profile.schema.json`，Pydantic source model 位于 `src/asc/models.py`，执行覆盖见 `docs/profile-capability-matrix.md`。Profile 2.0 用 `source_kind` 区分 journal、template、inferred、system_default 与 user_override，并保存 generated/reviewed/approved 状态。每条 explicit/inferred/user_confirmed 规则必须含 provenance；无依据的规则保持 unknown。多个来源冲突时保留 candidates，approval 和 build 都拒绝未解决冲突。

摘要和关键词按 `zh`/`en` 分开，每种语言分别包含 `label`、`body`、`count`，关键词另有 `separator`。因此“摘要：”与摘要正文、“关键词：”与关键词内容可以使用不同字符样式；中文可按 characters、英文可按 words、关键词按 items 独立计数。

新增期刊的无 AI 流程是复制示例目录、手写 `profile.yaml`、放入 CSL 与 `reference.docx`，再运行 `asc journal inspect journal-id`。也可以先创建待审 profile：

```powershell
asc journal create --id my-journal --name "某学刊" --source author-guidelines.txt
asc journal inspect my-journal
asc journal approve my-journal
asc journal reference my-journal
```

`asc journal approve` 默认拒绝仍含 unknown 的生成 Profile；人工接受未知项时必须显式使用 `--allow-unknown`。Profile 1.0 可继续读取，并可用以下命令持久化迁移：

```powershell
python scripts/migrate_profile.py journals/my-journal/profile.yaml
```

`output.filename_pattern` 支持 `{manuscript}`、`{journal}`、`{journal_id}` 和 `{mode}`，并拒绝路径穿越、Windows 非法名称、空结果和重复 `.docx`。

`journal create` 只生成 `profile.generated.yaml` 和 `profile-review.md`，不会静默批准。MVP intake 支持 TXT/Markdown；PDF、DOCX、HTML adapter 已留接口但尚未启用。

## 中文字体处理

formatter 同时写入 OOXML `w:ascii`、`w:hAnsi`、`w:eastAsia` 和 `w:cs`。例如正文把 `w:eastAsia` 设为宋体，把 Latin、数字和复杂文字 fallback 设为 Times New Roman。单元测试和 `asc inspect` 都直接读取 OOXML 验证这些值。

## Compliance

`asc check` 检查 metadata、摘要和正文字数、关键词数量、citekey、bibliography、疑似手写引用、缺失图片、Obsidian embed、匿名信息和 profile 冲突。`asc inspect` 读取最终 DOCX，验证 styles 的字体、字号与 section 页边距。结果使用 PASS、WARNING、FAIL 和 UNKNOWN，不生成缺乏依据的百分比分数。

## 设计与来源

技术选型、版本、Windows 支持和许可证比较见 [docs/architecture-review.md](docs/architecture-review.md)。Semantic Markdown 约定见 [docs/semantic-markdown.md](docs/semantic-markdown.md)。直接复用的第三方文件及版本见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 当前限制

- Live Mode 的代码路径和 upstream filter 已集成，但没有运行中的 Zotero + Better BibTeX 就无法端到端验证。
- TXT/Markdown intake 只识别少量明确格式规则；它不会假装理解所有自然语言投稿指南。
- 图片 embed 可转换；递归笔记 embed 目前只输出提示。
- DOCX inspection 已检查样式、实际段落/run、脚注 OOXML、参考文献段落、页边距和匿名信息，但无法验证 Word 在特定电脑上最终选择的字体 fallback 或自动分页后的视觉效果。
- 复杂文字字体、文本颜色、同时输出中英文双标题和正文致谢章节推断仍是 partial；具体边界见能力矩阵。
- PDF/DOCX/HTML 投稿指南解析、真实 LLM provider 和交互式冲突合并属于 Phase 2。

项目采用 MIT License。示例期刊明确为虚构测试用途。
