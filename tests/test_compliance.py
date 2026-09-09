from pathlib import Path

from asc.compliance import Status, check_markdown, overall_status


def test_example_has_no_fail(root: Path, profile):
    findings = check_markdown(root / "examples/demo-paper/paper.md", profile, root, root / "journals/example-humanities-journal")
    assert overall_status(findings) == Status.PASS
    assert not [finding for finding in findings if finding.status == Status.FAIL]


def test_missing_citekey_fails(tmp_path: Path, root: Path, profile):
    paper = tmp_path / "paper.md"
    paper.write_text("---\ntitle: T\nauthors: [{name: A, affiliation: U}]\nabstract: {zh: A}\nkeywords: {zh: [a, b, c]}\n---\n" + "正文" * 100 + " [@missing]", encoding="utf-8")
    findings = check_markdown(paper, profile, root, root / "journals/example-humanities-journal")
    assert any(f.status == Status.FAIL and "missing" in f.message for f in findings)


def test_anonymous_metadata_warning(root: Path, profile):
    changed = profile.model_copy(deep=True)
    changed.anonymous_review.required = True
    findings = check_markdown(root / "examples/demo-paper/paper.md", changed, root, root / "journals/example-humanities-journal")
    assert any(f.section == "Anonymous review" and f.status == Status.WARNING for f in findings)
