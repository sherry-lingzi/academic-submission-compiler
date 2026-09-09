from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from asc.docx import format_docx, generate_reference_docx, inspect_docx


def test_reference_and_formatter_fonts(tmp_path: Path, profile):
    reference = tmp_path / "reference.docx"
    output = tmp_path / "output.docx"
    generate_reference_docx(reference, profile)
    format_docx(reference, output, profile)
    document = Document(output)
    fonts = document.styles["Normal"].element.rPr.rFonts
    assert fonts.get(qn("w:eastAsia")) == "宋体"
    assert fonts.get(qn("w:ascii")) == "Times New Roman"
    assert document.styles["Normal"].font.size.pt == 12
    assert str(document.styles["Heading 1"].font.color.rgb) == "000000"
    title_borders = document.styles["Title"].element.pPr.find(qn("w:pBdr"))
    assert title_borders is None


def test_indent_and_margins(tmp_path: Path, profile):
    reference = tmp_path / "reference.docx"
    generate_reference_docx(reference, profile)
    document = Document(reference)
    ind = document.styles["Normal"].element.pPr.find(qn("w:ind"))
    assert ind.get(qn("w:firstLineChars")) == "200"
    assert abs(document.sections[0].left_margin.mm - 31.7) < 0.2


def test_inspector_passes_generated_reference(tmp_path: Path, profile):
    reference = tmp_path / "reference.docx"
    output = tmp_path / "output.docx"
    generate_reference_docx(reference, profile)
    format_docx(reference, output, profile)
    assert all(item.ok for item in inspect_docx(output, profile))
