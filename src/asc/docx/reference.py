from __future__ import annotations

from pathlib import Path

from docx import Document

from asc.docx.formatter import _ensure_style, _remove_paragraph_borders, apply_rule_to_style, character_style_rules, paragraph_style_rules
from asc.models import JournalProfile


def generate_reference_docx(path: Path, profile: JournalProfile) -> None:
    document = Document()
    document.core_properties.title = f"{profile.journal.name} reference document"
    document.add_paragraph("Reference document for Pandoc style definitions", style="Title")
    _remove_paragraph_borders(document.styles["Title"].element)
    for style_name, rule in paragraph_style_rules(profile).items():
        apply_rule_to_style(_ensure_style(document, style_name), rule)
    for style_name, rule in character_style_rules(profile).items():
        from docx.enum.style import WD_STYLE_TYPE
        apply_rule_to_style(_ensure_style(document, style_name, style_type=WD_STYLE_TYPE.CHARACTER), rule)
    for name in ("Affiliation", "Abstract", "Keywords", "Funding", "Bibliography", "Table Caption"):
        _ensure_style(document, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
