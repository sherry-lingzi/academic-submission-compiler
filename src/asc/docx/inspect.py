from __future__ import annotations

from pathlib import Path
import re
from zipfile import ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from asc.docx.formatter import ALIGNMENTS, character_style_rules, paragraph_style_rules
from asc.findings import Finding, Status
from asc.models import Confidence, JournalProfile, SourceKind, StyleRule


SECTION = "DOCX Formatting Compliance"
ANONYMOUS = "Anonymous Review"
DocxFinding = Finding


def _contract_status(rule, matched: bool) -> Status:
    if not matched:
        return Status.FAIL
    if getattr(rule, "confidence", None) == Confidence.unknown or getattr(rule, "source_kind", None) == SourceKind.system_default:
        return Status.UNKNOWN
    return Status.PASS


def _finding(rule, path: str, expected, detected, matched: bool, *, detail: str = "") -> Finding:
    fallback = getattr(rule, "source_kind", None) == SourceKind.system_default or getattr(rule, "confidence", None) == Confidence.unknown
    message = f"{path}: " + ("journal requirement unknown; ASC fallback verified" if fallback and matched else "generated value matches journal rule" if matched else "generated value violates configured rule")
    if detail:
        message += f"; {detail}"
    return Finding(SECTION, _contract_status(rule, matched), message, path, str(expected), str(detected))


def _fonts(element) -> tuple[str | None, str | None]:
    r_pr = element.rPr if hasattr(element, "rPr") else element.find(qn("w:rPr"))
    r_fonts = r_pr.find(qn("w:rFonts")) if r_pr is not None else None
    if r_fonts is None:
        return None, None
    return r_fonts.get(qn("w:eastAsia")), r_fonts.get(qn("w:ascii")) or r_fonts.get(qn("w:hAnsi"))


def _indent_chars(paragraph_format) -> tuple[float | None, float | None]:
    p_pr = paragraph_format._element.pPr
    ind = p_pr.find(qn("w:ind")) if p_pr is not None else None
    if ind is None:
        return None, None
    first = ind.get(qn("w:firstLineChars"))
    hanging = ind.get(qn("w:hangingChars"))
    return (float(first) / 100 if first is not None else None, float(hanging) / 100 if hanging is not None else None)


def _near(actual, expected, tolerance: float = 0.05) -> bool:
    return actual is not None and abs(float(actual) - float(expected)) < tolerance


def _style_findings(style, rule: StyleRule, path: str) -> list[Finding]:
    findings: list[Finding] = []
    east, latin = _fonts(style.element)
    if rule.font and rule.font.east_asia:
        findings.append(_finding(rule, f"{path}.font.east_asia", rule.font.east_asia, east, east == rule.font.east_asia))
    if rule.font and rule.font.latin:
        findings.append(_finding(rule, f"{path}.font.latin", rule.font.latin, latin, latin == rule.font.latin))
    if rule.size:
        detected = style.font.size.pt if style.font.size else None
        findings.append(_finding(rule, f"{path}.size", f"{rule.size.pt:g}pt", f"{detected:g}pt" if detected else "None", _near(detected, rule.size.pt)))
    if rule.bold is not None:
        findings.append(_finding(rule, f"{path}.bold", rule.bold, style.font.bold, style.font.bold == rule.bold))
    if rule.italic is not None:
        findings.append(_finding(rule, f"{path}.italic", rule.italic, style.font.italic, style.font.italic == rule.italic))
    if not hasattr(style, "paragraph_format"):
        return findings
    fmt = style.paragraph_format
    if rule.alignment:
        expected = ALIGNMENTS[rule.alignment]
        findings.append(_finding(rule, f"{path}.alignment", rule.alignment, str(fmt.alignment), fmt.alignment == expected))
    first, hanging = _indent_chars(fmt)
    if rule.first_line_indent_chars is not None:
        findings.append(_finding(rule, f"{path}.first_line_indent_chars", rule.first_line_indent_chars, first, _near(first, rule.first_line_indent_chars)))
    if rule.hanging_indent_chars is not None:
        findings.append(_finding(rule, f"{path}.hanging_indent_chars", rule.hanging_indent_chars, hanging, _near(hanging, rule.hanging_indent_chars)))
    if rule.line_spacing is not None:
        detected = fmt.line_spacing
        findings.append(_finding(rule, f"{path}.line_spacing", rule.line_spacing, detected, _near(detected, rule.line_spacing)))
    if rule.space_before_pt is not None:
        detected = fmt.space_before.pt if fmt.space_before else 0.0
        findings.append(_finding(rule, f"{path}.space_before_pt", rule.space_before_pt, detected, _near(detected, rule.space_before_pt)))
    if rule.space_after_pt is not None:
        detected = fmt.space_after.pt if fmt.space_after else 0.0
        findings.append(_finding(rule, f"{path}.space_after_pt", rule.space_after_pt, detected, _near(detected, rule.space_after_pt)))
    if rule.keep_with_next is not None:
        findings.append(_finding(rule, f"{path}.keep_with_next", rule.keep_with_next, fmt.keep_with_next, fmt.keep_with_next == rule.keep_with_next))
    return findings


def _actual_paragraph_findings(document, profile: JournalProfile, rules: dict[str, StyleRule]) -> list[Finding]:
    findings: list[Finding] = []
    for style_name, rule in rules.items():
        paragraphs = [p for p in document.paragraphs if p.style.name == style_name and p.text.strip()]
        if not paragraphs:
            if style_name in {"Normal", "Body Text", "First Paragraph", "Image Caption", "Table Caption"}:
                continue
            findings.append(Finding(SECTION, Status.UNKNOWN, f"No actual `{style_name}` paragraph was available for run-level validation", f"actual.{style_name}"))
            continue
        for index, paragraph in enumerate(paragraphs):
            if rule.alignment:
                detected = paragraph.paragraph_format.alignment
                findings.append(_finding(rule, f"actual.{style_name}[{index}].alignment", rule.alignment, detected, detected == ALIGNMENTS[rule.alignment]))
            first, hanging = _indent_chars(paragraph.paragraph_format)
            if rule.first_line_indent_chars is not None:
                findings.append(_finding(rule, f"actual.{style_name}[{index}].first_line_indent_chars", rule.first_line_indent_chars, first, _near(first, rule.first_line_indent_chars)))
            if rule.hanging_indent_chars is not None:
                findings.append(_finding(rule, f"actual.{style_name}[{index}].hanging_indent_chars", rule.hanging_indent_chars, hanging, _near(hanging, rule.hanging_indent_chars)))
            if rule.line_spacing is not None:
                findings.append(_finding(rule, f"actual.{style_name}[{index}].line_spacing", rule.line_spacing, paragraph.paragraph_format.line_spacing, _near(paragraph.paragraph_format.line_spacing, rule.line_spacing)))
            for run_index, run in enumerate(run for run in paragraph.runs if run.text.strip()):
                run_rule = character_style_rules(profile).get(run.style.name, rule)
                east, latin = _fonts(run._element)
                if run_rule.font and run_rule.font.east_asia and re.search(r"[\u3400-\u9fff]", run.text):
                    findings.append(_finding(run_rule, f"actual.{style_name}[{index}].run[{run_index}].font.east_asia", run_rule.font.east_asia, east, east == run_rule.font.east_asia))
                if run_rule.font and run_rule.font.latin and re.search(r"[A-Za-z0-9]", run.text):
                    findings.append(_finding(run_rule, f"actual.{style_name}[{index}].run[{run_index}].font.latin", run_rule.font.latin, latin, latin == run_rule.font.latin))
                if run_rule.size:
                    detected = run.font.size.pt if run.font.size else None
                    findings.append(_finding(run_rule, f"actual.{style_name}[{index}].run[{run_index}].size", run_rule.size.pt, detected, _near(detected, run_rule.size.pt)))
    return findings


def _metadata_run_findings(document, profile: JournalProfile) -> list[Finding]:
    findings: list[Finding] = []
    prefixes = {
        "摘要：": ("abstract", "zh"),
        "Abstract: ": ("abstract", "en"),
        "关键词：": ("keywords", "zh"),
        "Keywords: ": ("keywords", "en"),
    }
    for paragraph in document.paragraphs:
        matched = next(((prefix, field, language) for prefix, (field, language) in prefixes.items() if paragraph.text.startswith(prefix)), None)
        if not matched:
            continue
        prefix, field, language = matched
        runs = [run for run in paragraph.runs if run.text]
        label_style = f"{field.title()} {language} Label"
        body_style = f"{field.title()} {language} Body"
        label_ok = bool(runs) and runs[0].style.name == label_style and runs[0].text == prefix
        body_ok = len(runs) > 1 and all(run.style.name == body_style for run in runs[1:] if run.text.strip())
        findings.append(Finding(SECTION, Status.PASS if label_ok else Status.FAIL, f"{field}.{language} label uses a distinct `{label_style}` character style" if label_ok else f"{field}.{language} label character style is missing", f"actual.{field}.{language}.label_style"))
        findings.append(Finding(SECTION, Status.PASS if body_ok else Status.FAIL, f"{field}.{language} body uses `{body_style}` character style" if body_ok else f"{field}.{language} body character style is missing", f"actual.{field}.{language}.body_style"))
        if field == "keywords":
            variant = getattr(profile.keywords, language)
            separator = variant.separator if variant.separator is not None else ("；" if language == "zh" else "; ")
            content = paragraph.text[len(prefix):]
            matched_separator = separator in content
            status = Status.FAIL if not matched_separator else Status.UNKNOWN if variant.separator_source_kind == SourceKind.system_default else Status.PASS
            message = f"keywords.{language}.separator " + ("matches configured journal rule" if status == Status.PASS else "uses ASC system fallback" if status == Status.UNKNOWN else "does not match configured/fallback separator")
            findings.append(Finding(SECTION, status, message, f"actual.keywords.{language}.separator", repr(separator), repr(content)))
    return findings


def _xml_parts(path: Path) -> dict[str, str]:
    with ZipFile(path) as archive:
        return {name: archive.read(name).decode("utf-8", errors="ignore") for name in archive.namelist() if name.endswith(".xml")}


def inspect_docx(path: Path, profile: JournalProfile, sensitive_values: set[str] | None = None) -> list[Finding]:
    document = Document(path)
    findings: list[Finding] = []
    p_rules = paragraph_style_rules(profile)
    for style_name, rule in p_rules.items():
        if style_name in document.styles:
            findings.extend(_style_findings(document.styles[style_name], rule, f"style.{style_name}"))
    for style_name, rule in character_style_rules(profile).items():
        if style_name in document.styles:
            findings.extend(_style_findings(document.styles[style_name], rule, f"style.{style_name}"))

    first = document.sections[0]
    margins = profile.document.margins
    for path_name, detected, expected in (
        ("document.margins.top_mm", first.top_margin.mm, margins.top_mm),
        ("document.margins.bottom_mm", first.bottom_margin.mm, margins.bottom_mm),
        ("document.margins.left_mm", first.left_margin.mm, margins.left_mm),
        ("document.margins.right_mm", first.right_margin.mm, margins.right_mm),
    ):
        findings.append(_finding(profile.document, path_name, f"{expected:g}mm", f"{detected:.1f}mm", _near(detected, expected, 0.2)))
    expected_size = (210.0, 297.0) if profile.document.page_size == "A4" else (215.9, 279.4)
    detected_size = (first.page_width.mm, first.page_height.mm)
    findings.append(_finding(profile.document, "document.page_size", profile.document.page_size, f"{detected_size[0]:.1f}x{detected_size[1]:.1f}mm", _near(detected_size[0], expected_size[0], 0.2) and _near(detected_size[1], expected_size[1], 0.2)))
    findings.extend(_actual_paragraph_findings(document, profile, p_rules))
    findings.extend(_metadata_run_findings(document, profile))

    bibliography = [p for p in document.paragraphs if p.style.name == "Bibliography" and p.text.strip()]
    findings.append(Finding(SECTION, Status.PASS if bibliography else Status.UNKNOWN, f"Actual Bibliography paragraphs: {len(bibliography)}", "actual.bibliography"))
    xml = _xml_parts(path)
    footnotes = xml.get("word/footnotes.xml", "")
    if footnotes:
        styled = "FootnoteText" in footnotes
        findings.append(Finding(SECTION, Status.PASS if styled else Status.FAIL, "Footnotes XML uses Footnote Text style" if styled else "Footnotes XML contains an unstyled footnote", "actual.footnotes.style"))
        findings.extend(_style_findings(document.styles["Footnote Text"], profile.footnotes, "actual.footnotes.effective_style"))
    else:
        findings.append(Finding(SECTION, Status.UNKNOWN, "No word/footnotes.xml part was available", "actual.footnotes"))

    if profile.anonymous_review.required:
        joined = "\n".join(text for name, text in xml.items() if name.startswith(("word/", "docProps/")))
        core = xml.get("docProps/core.xml", "")
        author_blank = not re.search(r"<dc:creator>\s*[^<\s]", core) and not re.search(r"<cp:lastModifiedBy>\s*[^<\s]", core)
        findings.append(Finding(ANONYMOUS, Status.PASS if author_blank else Status.FAIL, "DOCX core author metadata is blank" if author_blank else "DOCX core author metadata contains a value", "anonymous.docx.core_properties"))
        generic_leaks = []
        if profile.anonymous_review.hide_email and re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", joined):
            generic_leaks.append("email")
        if profile.anonymous_review.hide_orcid and re.search(r"\b\d{4}-\d{4}-\d{4}-[\dX]{4}\b", joined):
            generic_leaks.append("ORCID")
        for value in sensitive_values or set():
            if value and value in joined:
                generic_leaks.append(value)
        findings.append(Finding(ANONYMOUS, Status.FAIL if generic_leaks else Status.PASS, f"Identity leaks found in DOCX package: {', '.join(sorted(set(generic_leaks)))}" if generic_leaks else "No configured identity values found in document, headers, footers, footnotes, comments, or properties", "anonymous.docx.package"))
    return findings
