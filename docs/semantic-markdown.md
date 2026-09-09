# Semantic Academic Markdown 规范

稿件使用 UTF-8 Markdown。YAML front matter 保存题名、作者、单位、摘要、关键词、基金、语言和文类；正文只保存论证结构、脚注、图表和 Pandoc citation。视觉格式只进入 journal profile。

```yaml
---
title: 可复现的学术投稿工作流
authors:
  - name: 示例作者
    affiliation: 示例大学
abstract:
  zh: |
    中文摘要
  en: |
    English abstract
keywords:
  zh: [学术写作, 可复现工作流]
  en: [academic writing, reproducible workflow]
funding:
  - name: 示例项目
    number: ABC123
language: zh-CN
article_type: research-article
---
```

引用必须使用 Pandoc 语法，例如 `[@hayles1999, p. 35]`、`[@a; @b]` 和叙述式 `@hayles1999`。构建器不会覆写源稿。Obsidian wikilink 在 AST 层转为可见文本；图片 embed 转为图片；笔记 embed 当前输出明确提示，不递归展开。
