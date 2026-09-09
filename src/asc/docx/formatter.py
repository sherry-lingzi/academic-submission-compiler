from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from asc.models import FontSpec, JournalProfile, StyleRule


ALIGNMENTS = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


STYLE_MAP = {
    "title": ("Title",),
    "authors": ("Author",),
    "affiliations": ("Affiliation",),
    "abstract": ("Abstract",),
    "keywords": ("Keywords",),
    "body": ("Normal", "Body Text", "First Paragraph"),
    "footnotes": ("Footnote Text",),
    "bibliography": ("Bibliography",),
    "funding": ("Funding",),
    "figures": ("Caption", "Image Caption"),
    "tables": ("Table Caption",),
}


def set_run_fonts(element, fonts: FontSpec) -> None:
    r_pr = element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    latin = fonts.latin or fonts.east_asia
    east = fonts.east_asia or fonts.latin
    if latin:
        r_fonts.set(qn("w:ascii"), latin)
        r_fonts.set(qn("w:hAnsi"), latin)
        r_fonts.set(qn("w:cs"), fonts.complex_script or latin)
    if east:
        r_fonts.set(qn("w:eastAsia"), east)


def _set_indent_chars(paragraph_format, chars: float | None, hanging: float | None) -> None:
    p_pr = paragraph_format._element.get_or_add_pPr()
    ind = p_pr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        p_pr.append(ind)
    if chars is not None:
        ind.set(qn("w:firstLineChars"), str(round(chars * 100)))
        ind.attrib.pop(qn("w:firstLine"), None)
    if hanging is not None:
        ind.set(qn("w:hangingChars"), str(round(hanging * 100)))
        ind.attrib.pop(qn("w:hanging"), None)


def apply_rule_to_style(style, rule: StyleRule) -> None:
    if rule.font:
        set_run_fonts(style.element, rule.font)
        style.font.name = rule.font.latin or rule.font.east_asia
    if rule.size:
        style.font.size = Pt(rule.size.pt)
    if rule.bold is not None:
        style.font.bold = rule.bold
    if rule.italic is not None:
        style.font.italic = rule.italic
    paragraph = style.paragraph_format
    if rule.alignment:
        paragraph.alignment = ALIGNMENTS[rule.alignment]
    if rule.line_spacing is not None:
        paragraph.line_spacing = rule.line_spacing
    if rule.space_before_pt is not None:
        paragraph.space_before = Pt(rule.space_before_pt)
    if rule.space_after_pt is not None:
        paragraph.space_after = Pt(rule.space_after_pt)
    if rule.keep_with_next is not None:
        paragraph.keep_with_next = rule.keep_with_next
    _set_indent_chars(paragraph, rule.first_line_indent_chars, rule.hanging_indent_chars)


def _remove_paragraph_borders(element) -> None:
    p_pr = getattr(element, "pPr", None)
    if p_pr is not None:
        borders = p_pr.find(qn("w:pBdr"))
        if borders is not None:
            p_pr.remove(borders)


def _ensure_style(document: Document, name: str, base: str = "Normal"):
    try:
        return document.styles[name]
    except KeyError:
        style = document.styles.add_style(name, 1)
        style.base_style = document.styles[base]
        return style


def format_docx(input_path: Path, output_path: Path, profile: JournalProfile) -> None:
    document = Document(input_path)
    for section in document.sections:
        margins = profile.document.margins
        section.top_margin = Mm(margins.top_mm)
        section.bottom_margin = Mm(margins.bottom_mm)
        section.left_margin = Mm(margins.left_mm)
        section.right_margin = Mm(margins.right_mm)
        section.page_width, section.page_height = (Mm(210), Mm(297)) if profile.document.page_size == "A4" else (Mm(215.9), Mm(279.4))

    for profile_name, style_names in STYLE_MAP.items():
        rule = getattr(profile, profile_name)
        for style_name in style_names:
            style = _ensure_style(document, style_name)
            apply_rule_to_style(style, rule)
            style.font.color.rgb = RGBColor.from_string(profile.document.text_color)
            if style_name == "Title":
                _remove_paragraph_borders(style.element)
    for level, style_name in (("level1", "Heading 1"), ("level2", "Heading 2"), ("level3", "Heading 3")):
        if level in profile.headings:
            heading_style = _ensure_style(document, style_name)
            apply_rule_to_style(heading_style, profile.headings[level])
            heading_style.font.color.rgb = RGBColor.from_string(profile.document.text_color)

    prefix_styles = {"摘要：": "Abstract", "关键词：": "Keywords", "基金项目：": "Funding", "单位：": "Affiliation", "Abstract: ": "Abstract", "Keywords: ": "Keywords"}
    for paragraph in document.paragraphs:
        for prefix, style_name in prefix_styles.items():
            if paragraph.text.startswith(prefix):
                paragraph.style = document.styles[style_name]
                break
        try:
            profile_name = next((key for key, names in STYLE_MAP.items() if paragraph.style.name in names), None)
            rule = getattr(profile, profile_name) if profile_name else None
        except (KeyError, AttributeError):
            rule = None
        if rule and rule.font:
            for run in paragraph.runs:
                set_run_fonts(run._element, rule.font)
                run.font.color.rgb = RGBColor.from_string(profile.document.text_color)
                if rule.size:
                    run.font.size = Pt(rule.size.pt)
        if paragraph.style.name == "Title":
            _remove_paragraph_borders(paragraph._p)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
