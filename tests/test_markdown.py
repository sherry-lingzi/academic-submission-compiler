from pathlib import Path

from asc.markdown import embed_targets, extract_citations, parse_markdown, wikilink_targets


def test_yaml_metadata_and_body(root: Path):
    manuscript = parse_markdown(root / "examples/demo-paper/paper.md")
    assert manuscript.metadata["title"] == "可复现的学术投稿工作流"
    assert "# 引言" in manuscript.body


def test_single_multi_narrative_and_locator():
    citations = extract_citations("@a 说明 [@b, p. 35]，并见 [@c; @d]。`@ignored`\n```\n@alsoignored\n```")
    assert [item.key for item in citations] == ["a", "b", "c", "d"]
    assert citations[0].narrative
    assert citations[1].locator == "35"


def test_wikilink_and_embed():
    text = "见 [[工作流说明|条目]]。\n![[figures/workflow.png]]"
    assert wikilink_targets(text) == ["工作流说明"]
    assert embed_targets(text) == ["figures/workflow.png"]
