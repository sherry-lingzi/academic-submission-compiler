from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from asc.docx.formatter import STYLE_MAP
from asc.models import JournalProfile


@dataclass(frozen=True)
class DocxFinding:
    ok: bool
    label: str
    expected: str
    detected: str


def _fonts(style) -> tuple[str | None, str | None]:
    r_fonts = style.element.rPr.find(qn("w:rFonts")) if style.element.rPr is not None else None
    if r_fonts is None:
        return None, None
    return r_fonts.get(qn("w:eastAsia")), r_fonts.get(qn("w:ascii")) or r_fonts.get(qn("w:hAnsi"))


def inspect_docx(path: Path, profile: JournalProfile) -> list[DocxFinding]:
    document = Document(path)
    findings: list[DocxFinding] = []
    checks = [("title", "Title"), ("body", "Normal"), ("abstract", "Abstract"), ("keywords", "Keywords"), ("bibliography", "Bibliography")]
    checks.extend((f"headings.{level}", f"Heading {index}") for index, level in enumerate(("level1", "level2", "level3"), 1) if level in profile.headings)
    for rule_name, style_name in checks:
        rule = profile.headings[rule_name.split(".", 1)[1]] if rule_name.startswith("headings.") else getattr(profile, rule_name)
        style = document.styles[style_name]
        east, latin = _fonts(style)
        if rule.font:
            if rule.font.east_asia:
                findings.append(DocxFinding(east == rule.font.east_asia, f"{style_name} Chinese font", rule.font.east_asia, str(east)))
            if rule.font.latin:
                findings.append(DocxFinding(latin == rule.font.latin, f"{style_name} Latin font", rule.font.latin, str(latin)))
        if rule.size:
            detected = style.font.size.pt if style.font.size else None
            findings.append(DocxFinding(detected is not None and abs(detected - rule.size.pt) < 0.05, f"{style_name} size", f"{rule.size.pt:g}pt", f"{detected:g}pt" if detected else "None"))
    margins = profile.document.margins
    first = document.sections[0]
    for label, detected, expected in (("Top margin", first.top_margin.mm, margins.top_mm), ("Bottom margin", first.bottom_margin.mm, margins.bottom_mm), ("Left margin", first.left_margin.mm, margins.left_mm), ("Right margin", first.right_margin.mm, margins.right_mm)):
        findings.append(DocxFinding(abs(detected - expected) < 0.2, label, f"{expected:g}mm", f"{detected:.1f}mm"))
    return findings

