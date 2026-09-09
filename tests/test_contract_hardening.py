from pathlib import Path

from docx import Document
from docx.shared import Pt

from asc.compliance import Status, check_markdown
from asc.docx import format_docx, generate_reference_docx, inspect_docx
from asc.models import Confidence, SourceKind
from asc.paths import resolve_attachment, resolve_profile_resource


def test_unknown_fallback_is_not_reported_as_pass(tmp_path: Path, profile):
    changed = profile.model_copy(deep=True)
    changed.body.confidence = Confidence.unknown
    changed.body.source_kind = SourceKind.system_default
    source = tmp_path / "source.docx"
    output = tmp_path / "output.docx"
    generate_reference_docx(source, changed)
    format_docx(source, output, changed)
    findings = inspect_docx(output, changed)
    body = [item for item in findings if item.rule_path and item.rule_path.startswith("style.Normal")]
    assert body
    assert all(item.status == Status.UNKNOWN for item in body)


def test_unsupported_style_field_fails_preflight(root: Path, profile):
    changed = profile.model_copy(deep=True)
    changed.headings["level1"].numbering = "一、"
    findings = check_markdown(root / "examples/demo-paper/paper.md", changed, root, root / "journals/example-humanities-journal")
    assert any(item.status == Status.FAIL and "headings.level1.numbering" in item.message for item in findings)


def test_label_and_body_styles_can_differ(tmp_path: Path, profile):
    changed = profile.model_copy(deep=True)
    changed.abstract.zh.label.font.east_asia = "黑体"
    changed.abstract.zh.label.bold = True
    changed.abstract.zh.body.font.east_asia = "宋体"
    reference = tmp_path / "reference.docx"
    output = tmp_path / "output.docx"
    generate_reference_docx(reference, changed)
    format_docx(reference, output, changed)
    document = Document(output)
    assert document.styles["Abstract zh Label"].font.bold is True
    assert document.styles["Abstract zh Label"].element.rPr.rFonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia") == "黑体"
    assert document.styles["Abstract zh Body"].element.rPr.rFonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia") == "宋体"


def test_resource_resolver_local_project_absolute_and_chinese(tmp_path: Path):
    root = tmp_path / "中文 project"
    journal = root / "journals" / "测试 刊"
    journal.mkdir(parents=True)
    local = journal / "local file.csl"
    local.write_text("x", encoding="utf-8")
    project = root / "shared file.json"
    project.write_text("x", encoding="utf-8")
    absolute = tmp_path / "absolute file.docx"
    absolute.write_text("x", encoding="utf-8")
    assert resolve_profile_resource(root, journal, "local file.csl") == local.resolve()
    assert resolve_profile_resource(root, journal, "shared file.json") == project.resolve()
    assert resolve_profile_resource(root, journal, str(absolute)) == absolute.resolve()


def test_attachment_resolver_reports_ambiguity(tmp_path: Path):
    root = tmp_path / "vault"
    manuscript = root / "notes" / "paper.md"
    manuscript.parent.mkdir(parents=True)
    (root / "assets").mkdir()
    (manuscript.parent / "image.png").write_bytes(b"one")
    (root / "assets" / "image.png").write_bytes(b"two")
    import pytest
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        resolve_attachment(manuscript, "image.png", root, ["assets"])
