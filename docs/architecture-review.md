# 现有项目技术评估与架构选择

评估日期为 2026 年 9 月 9 日。结论基于各项目当日默认分支、仓库清单、许可证、关键实现和官方文档；提交哈希用于避免把“最新版”写成模糊描述。

## 结论

本项目选择 [pan4ratte/obsidian-pandoc-gui](https://github.com/pan4ratte/obsidian-pandoc-gui) 作为主要工程参考，选择 [Pandoc](https://pandoc.org/) 作为实际底层运行时，并直接携带 [Better BibTeX 官方 live citation Lua filter](https://github.com/retorquere/zotero-better-bibtex/blob/master/pandoc/pandoc-zotero-live-citemarkers.lua)。这不是把 Pandoc GUI 整体复制为新的 Obsidian 插件，而是复用其已验证的边界：Pandoc defaults/参数、Lua AST filter、`reference.docx` 和本地/Windows 路径处理分别承担不同职责。

`md-manuscript` 的 journal profile 思路最接近本项目，但它把大量能力绑定到一个完整 vault 和 Obsidian 插件，profile 主要描述导出器而非可追溯的投稿规则。其根目录没有许可证文件；虽然子插件 `package.json` 声明 MIT，本项目仍不复制该仓库代码。

`WesternGua/obsidian-zotero-citations` 对 live Word citation 的实现很有价值，也验证了 Better BibTeX filter、临时 Markdown 和 `reference.docx` 的组合。但它使用带隐藏 Zotero item metadata 的私有 Obsidian 写作模型，README 也明确说明 Windows 尚未充分验证，因此不适合作为 Markdown-first、Windows-first 的 CLI 底座。

## 三个重点项目

| 项目 | 当日版本或提交 | 可复用能力 | 不直接复用的部分 | Windows | 许可证 |
| --- | --- | --- | --- | --- | --- |
| [WesternGua/obsidian-zotero-citations](https://github.com/WesternGua/obsidian-zotero-citations) | 0.2.9；`6272deec`，2026-08-25 | Better BibTeX live filter 调用、custom CSL URI、失败即停止、临时副本不改源稿 | 私有隐藏 metadata、Obsidian UI、直接读取 Zotero profile/database 的 fallback | README 称主要在 macOS 开发，Windows 未充分验证 | MIT |
| [beyerh/md-manuscript](https://github.com/beyerh/md-manuscript) | 插件 1.0.0；`0e513465`，2026-08-10 | profile 分层、Better CSL JSON、可定制 `reference.docx`、Windows 发布包 | 完整 vault、LaTeX/PDF 侧重点、未记录 provenance 的 profile、根仓库授权不清晰 | 提供 Windows 下载和脚本入口 | 子插件声明 MIT；根目录无 LICENSE，因此不复制代码 |
| [pan4ratte/obsidian-pandoc-gui](https://github.com/pan4ratte/obsidian-pandoc-gui) | 2.2.0；`41d6d4f`，2026-09-04 | 完整 Pandoc 参数模型、defaults、`reference.docx`、Lua filter catalogue、wikilink/embed AST 处理、desktop Pandoc 路径 | GUI、移动端 WASM、大量与投稿无关的格式和模板 | desktop 可配置 Pandoc 路径；代码含 Windows 参数测试 | MIT |

三者都能驱动 Pandoc 和 CSL。只有 WesternGua 把 live Zotero Word field 做成主要用户路径；Pandoc GUI 通过 filter catalogue 提供 Better BibTeX filter；md-manuscript 默认走静态 bibliography。`reference.docx` 在三个项目中都出现，但只有本项目再增加一层 OOXML formatter 和 post-build inspection，以覆盖中西文字体、字符缩进和期刊级校验。

## 其他项目和官方组件

| 项目 | 评估 | 采用方式 |
| --- | --- | --- |
| [evolve2k/obsidian-pandoc-academic-word-doc-guide](https://github.com/evolve2k/obsidian-pandoc-academic-word-doc-guide) | 教程型仓库；当日提交 `cd1bf945`（2026-06-24）。说明 Zotero、Obsidian、Pandoc 和 Word 的装配方式，但不是可复用编译核心 | 仅作工作流文档参考 |
| [MarcosNicolau/obsidian-for-academia](https://github.com/MarcosNicolau/obsidian-for-academia) | 面向学术 Obsidian 配置的协作文档，重点不在期刊 profile 或 DOCX 合规 | 仅作用户场景参考 |
| [hoonsubin/obsidian-research-vault-template](https://github.com/hoonsubin/obsidian-research-vault-template) | 高度主观的研究 vault 模板，适合知识管理，不适合作为可移植编译器依赖 | 不复用 vault 结构 |
| [retorquere/zotero-better-bibtex](https://github.com/retorquere/zotero-better-bibtex) | 9.0.64；`0d63f960`，2026-09-09。官方文档建议 Pandoc 使用 Better CSL JSON，并提供 live Word/ODT filter 与本地 JSON-RPC API | 直接携带 MIT Lua filter；通过 `api.ready` 做 live preflight；不读写 Zotero database |
| [zotero-chinese/styles](https://github.com/zotero-chinese/styles) | `cf56b119`，2026-08-23。README 明确说明仓库样式使用 citeproc-js 的 CSL-M 扩展，大部分由 GB/T 7714 衍生 | 用户可放入期刊目录；static 构建检测扩展并默认拒绝冒险输出 |
| [citation-style-language/styles](https://github.com/citation-style-language/styles) | 官方 CSL 样式分发库 | 推荐用户按目标期刊选择；CC BY-SA 3.0 文件不嵌入 MIT 示例 |

Pandoc 官方手册确认 `--citeproc`、bibliography、CSL、defaults 和 `--reference-doc` 是原生能力，且 DOCX reference document 的正文会被忽略，样式与页面属性会被复用。Better BibTeX 官方文档确认 live filter 要求 Pandoc 2.16.2+、正在运行的 Zotero 与 Better BibTeX，并记录了 Word 偶发修复提示和 LibreOffice 对 DOCX live field 的限制。Quarto 也建立在同一 reference document 机制上，因此保留为 optional frontend，不成为核心依赖。

## 复用边界与许可证

直接复用的第三方代码只有 `filters/zotero.lua`，来源、部署 revision 和上游提交记录在 `THIRD_PARTY_NOTICES.md`。项目不携带 `zotero-chinese/styles` 或官方 CSL repository 中的 CC BY-SA 样式；示例 CSL 是本项目的 CC0 测试样式。Pandoc GUI 的 filters 与参数处理只作为设计参考，本项目的 Python CLI、schema、formatter、checker 与两个 ASC Lua filters 为独立实现。

## 最终架构

```text
Semantic Markdown + Better CSL JSON
        │
        ├─ Markdown/profile/citation preflight
        │
        ├─ static: Pandoc citeproc + journal CSL
        └─ live: Better BibTeX official Lua filter + Zotero local API
                    │
             reference.docx
                    │
          deterministic OOXML formatter
                    │
          DOCX inspection + compliance report
```

`Journal Profile` 是本项目新增的核心抽象。它记录排版值、来源、证据、置信类型和冲突候选；AI 或规则提取器只生成待审 profile，编译器只读取人工批准的 `profile.yaml`。
