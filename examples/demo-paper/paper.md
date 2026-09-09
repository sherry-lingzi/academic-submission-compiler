---
title: 可复现的学术投稿工作流
authors:
  - name: 示例作者
    affiliation: 示例大学数字人文实验室
abstract:
  zh: |
    本文以完全虚构的材料演示学术投稿编译器的基本工作流。语义化 Markdown 保存内容结构，独立的期刊配置保存版式规则，文献数据与引用样式分别控制来源和呈现。演示覆盖中英文元数据、引文、脚注、图片和 Obsidian 链接，用于验证同一源稿能够稳定生成不同期刊格式的 Word 文档。本文不承载真实研究成果或个人信息。
  en: |
    This fictional manuscript demonstrates a reproducible submission workflow in which semantic Markdown, journal rules, bibliography data, and citation styles remain separate.
keywords:
  zh: [学术写作, 可复现工作流, 文档编译]
  en: [academic writing, reproducible workflow, document compilation]
funding:
  - name: 虚构演示项目
    number: DEMO-0000
language: zh-CN
article_type: research-article
---

# 引言

学术稿件在内容完成后，常常还需要适配不同期刊的标题、字体、缩进、页边距与参考文献格式。这个演示把投稿过程视为一次可重复编译：作者维护语义内容，工具读取经过确认的期刊规则，再生成用于投稿的 DOCX。文稿中的资料、作者与机构均为虚构信息，只用于自动化测试。

系统使用稳定的 citekey 表示来源，例如叙述式引用 @hayles1999、带定位信息的引用 [@liu2020, p. 48]，以及组合引用 [@hayles1999; @haraway1985]。引用的可见形式由 CSL 决定，文献元数据则来自静态导出文件；因此默认构建不依赖正在运行的 Zotero。

## 一 内容与格式分离

Markdown 保存标题层级、段落、脚注、图像和引文等语义。字体、字号、行距和页边距不写进正文，而由 Journal Profile 与 `reference.docx` 管理。这样，同一份内容可以面向多个虚构期刊生成不同版式，同时避免在改格式时误改论证内容。

> [!NOTE]
> 本文、期刊与项目资料均为公开仓库使用的虚构测试数据。

![[figures/workflow.png]]

图 1 展示从语义稿件到投稿文档与合规报告的处理顺序。相关背景另见 [[工作流说明|演示说明条目]]；导出时，wikilink 只保留可见文本。

## 二 可验证的输出

构建器先检查元数据、引文键、图片路径和期刊规则，再调用 Pandoc 处理结构与引用，最后以确定性代码校正 Word 样式。构建后检查实际 OOXML 中的字体、字号和页面属性，并把结果写入合规报告。[^build]

这种安排使错误更容易定位：未知规则继续保持未知，推断规则保留来源，冲突规则阻止构建。静态引用模式适合持续集成和最终投稿；实时模式则可以在本地 Zotero 与 Better BibTeX 可用时生成可刷新的 Word 引用字段。

[^build]: 编译过程只读取源稿，中间文件写入临时目录，不会覆写 Markdown。

# 结语

这个虚构样例展示了项目的最小完整路径。内容、文献、引用样式和版式规则各自拥有清晰的来源，生成结果可以重复检查，也可以在切换期刊配置后重新编译。

# 参考文献
