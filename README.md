# Academic Submission Compiler 学术投稿编译器

Academic Submission Compiler 把一份语义化 Markdown 母版编译为不同期刊要求的 DOCX，并同时生成可追溯的合规报告。项目的原则是 **Write semantically. Compile typographically.** 写作时维护内容和语义，投稿格式在编译阶段由确定性代码完成。

当前版本完成 Phase 1 MVP：正式 Journal Profile schema、Pandoc static citation、`reference.docx`、中文和 Latin 字体分离、DOCX post-formatter、构建前和构建后检查、期刊切换、Windows 路径测试、虚构演示稿和测试套件。AI intake 提供 provider-neutral 接口和 TXT/Markdown 规则提取器；Zotero Live Mode 已接入 Better BibTeX 官方 Lua filter，但仍标记为 experimental。

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

编译器不修改 `paper.md`。中间 DOCX 写入系统临时目录，最终文件进入 `dist/`。

## Static Mode 与 Zotero Live Mode

Static Mode 使用 Pandoc citeproc、bibliography 和 journal CSL。它最适合最终投稿、CI 和可重复构建，也是默认模式。

```powershell
asc build paper.md --journal journal-id
```

Live Mode 使用 Better BibTeX 官方 `zotero.lua` 生成 Word 中可刷新的 Zotero citation fields，适合导师批改、合作者协作和返修阶段。它要求 Zotero 与 Better BibTeX 正在运行；preflight 失败时不会生成半成品。

```powershell
asc build paper.md --journal journal-id --live-zotero
```

Live Mode 不改变 Markdown，但 Word 或 Zotero 版本组合仍可能有上游限制。最终提交前应在 Microsoft Word 中打开并执行 Zotero Refresh。
Live 产物使用 `-live.docx` 后缀，避免覆盖同一次写作的 static 成品。

## CSL 与 reference.docx

CSL 决定引用和参考文献内容如何呈现；`reference.docx` 决定 Word paragraph/character styles 与页面属性。两者不能互相替代。Pandoc 先生成文档结构，ASC formatter 再校正中西文字体、字号、段落缩进、行距和页边距。

中文 CSL 可能依赖 CSL-M 或 citeproc-js 扩展。`asc check` 会发出 warning，static build 默认拒绝检测到的 CSL-M 样式，并建议 Live Mode。只有人工确认 Pandoc 输出正确后才应使用 `--allow-csl-m`。

## Journal Profile

正式 schema 位于 `schemas/journal-profile.schema.json`，Pydantic source model 位于 `src/asc/models.py`。字体分别保存 `east_asia` 与 `latin`，字号同时保存中文名与 pt。每条 explicit/inferred 规则必须含 `source` 和 `evidence`；无依据的规则保持 `unknown`。多个来源冲突时保留 `candidates`，approval 和 build 都拒绝未解决冲突。

新增期刊的无 AI 流程是复制示例目录、手写 `profile.yaml`、放入 CSL 与 `reference.docx`，再运行 `asc journal inspect journal-id`。也可以先创建待审 profile：

```powershell
asc journal create --id my-journal --name "某学刊" --source author-guidelines.txt
asc journal inspect my-journal
asc journal approve my-journal
asc journal reference my-journal
```

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
- DOCX inspection 目前覆盖主要 style 和页边距，不检查 Word 实际字体 fallback、页眉页脚或每一个局部 direct-formatting run。
- PDF/DOCX/HTML 投稿指南解析、真实 LLM provider 和交互式冲突合并属于 Phase 2。

项目采用 MIT License。示例期刊明确为虚构测试用途。
