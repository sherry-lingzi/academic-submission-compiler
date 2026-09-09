from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
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
    "authors": ("Author",),
    "affiliations": ("Affiliation",),
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


def apply_rule_to_paragraph_format(paragraph_format, rule: StyleRule) -> None:
    if rule.alignment:
        paragraph_format.alignment = ALIGNMENTS[rule.alignment]
    if rule.line_spacing is not None:
        paragraph_format.line_spacing = rule.line_spacing
    if rule.space_before_pt is not None:
        paragraph_format.space_before = Pt(rule.space_before_pt)
    if rule.space_after_pt is not None:
        paragraph_format.space_after = Pt(rule.space_after_pt)
    if rule.keep_with_next is not None:
        paragraph_format.keep_with_next = rule.keep_with_next
    _set_indent_chars(paragraph_format, rule.first_line_indent_chars, rule.hanging_indent_chars)


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
    if style.type == WD_STYLE_TYPE.PARAGRAPH:
        apply_rule_to_paragraph_format(style.paragraph_format, rule)


def apply_rule_to_run(run, rule: StyleRule, color: str) -> None:
    if rule.font:
        set_run_fonts(run._element, rule.font)
    if rule.size:
        run.font.size = Pt(rule.size.pt)
    if rule.bold is not None:
        run.bold = rule.bold
    if rule.italic is not None:
        run.italic = rule.italic
    run.font.color.rgb = RGBColor.from_string(color)


def _remove_paragraph_borders(element) -> None:
    p_pr = getattr(element, "pPr", None)
    if p_pr is not None:
        borders = p_pr.find(qn("w:pBdr"))
        if borders is not None:
            p_pr.remove(borders)


def _ensure_style(document: Document, name: str, base: str = "Normal", style_type=WD_STYLE_TYPE.PARAGRAPH):
    try:
        return document.styles[name]
    except KeyError:
        style = document.styles.add_style(name, style_type)
        if style_type == WD_STYLE_TYPE.PARAGRAPH:
            style.base_style = document.styles[base]
        return style


def paragraph_style_rules(profile: JournalProfile) -> dict[str, StyleRule]:
    rules: dict[str, StyleRule] = {"Title": profile.title.default}
    for profile_name, style_names in STYLE_MAP.items():
        for style_name in style_names:
            rules[style_name] = getattr(profile, profile_name)
    if profile.document.line_spacing is not None:
        for style_name in ("Normal", "Body Text", "First Paragraph"):
            if rules[style_name].line_spacing is None:
                rules[style_name] = rules[style_name].model_copy(update={"line_spacing": profile.document.line_spacing})
    rules["Abstract"] = profile.abstract.zh.body
    rules["Keywords"] = profile.keywords.zh.body
    for index, level in enumerate(("level1", "level2", "level3"), 1):
        if level in profile.headings:
            rules[f"Heading {index}"] = profile.headings[level]
    return rules


def character_style_rules(profile: JournalProfile) -> dict[str, StyleRule]:
    rules: dict[str, StyleRule] = {}
    for field in ("abstract", "keywords"):
        bilingual = getattr(profile, field)
        for language in ("zh", "en"):
            variant = getattr(bilingual, language)
            rules[f"{field.title()} {language} Label"] = variant.label
            rules[f"{field.title()} {language} Body"] = variant.body
    return rules


def _paragraph_rule(paragraph, profile: JournalProfile, rules: dict[str, StyleRule]) -> StyleRule | None:
    if paragraph.style.name == "Title":
        language = "zh" if re.search(r"[\u3400-\u9fff]", paragraph.text) else "en"
        return profile.title.for_language(language)
    return rules.get(paragraph.style.name)


def format_docx(input_path: Path, output_path: Path, profile: JournalProfile) -> None:
    document = Document(input_path)
    for section in document.sections:
        margins = profile.document.margins
        section.top_margin = Mm(margins.top_mm)
        section.bottom_margin = Mm(margins.bottom_mm)
        section.left_margin = Mm(margins.left_mm)
        section.right_margin = Mm(margins.right_mm)
        section.page_width, section.page_height = (Mm(210), Mm(297)) if profile.document.page_size == "A4" else (Mm(215.9), Mm(279.4))

    paragraph_rules = paragraph_style_rules(profile)
    for style_name, rule in paragraph_rules.items():
        style = _ensure_style(document, style_name)
        apply_rule_to_style(style, rule)
        style.font.color.rgb = RGBColor.from_string(profile.document.text_color)
        if style_name == "Title":
            _remove_paragraph_borders(style.element)
    char_rules = character_style_rules(profile)
    for style_name, rule in char_rules.items():
        apply_rule_to_style(_ensure_style(document, style_name, style_type=WD_STYLE_TYPE.CHARACTER), rule)

    prefix_styles = {
        "摘要：": ("Abstract", "Abstract zh Label", "Abstract zh Body"),
        "Abstract: ": ("Abstract", "Abstract en Label", "Abstract en Body"),
        "关键词：": ("Keywords", "Keywords zh Label", "Keywords zh Body"),
        "Keywords: ": ("Keywords", "Keywords en Label", "Keywords en Body"),
        "基金项目：": ("Funding", None, None),
        "单位：": ("Affiliation", None, None),
    }
    for paragraph in document.paragraphs:
        matched = next(((prefix, styles) for prefix, styles in prefix_styles.items() if paragraph.text.startswith(prefix)), None)
        if matched:
            _, (paragraph_style, _, _) = matched
            paragraph.style = document.styles[paragraph_style]
        rule = _paragraph_rule(paragraph, profile, paragraph_rules)
        if rule:
            apply_rule_to_paragraph_format(paragraph.paragraph_format, rule)
            for run in paragraph.runs:
                run_rule = char_rules.get(run.style.name, rule)
                apply_rule_to_run(run, run_rule, profile.document.text_color)
        if paragraph.style.name == "Title":
            _remove_paragraph_borders(paragraph._p)

    if profile.anonymous_review.required:
        document.core_properties.author = ""
        document.core_properties.last_modified_by = ""
        document.core_properties.comments = "Anonymous submission generated by ASC"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
