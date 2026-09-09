from __future__ import annotations

from pathlib import Path

from docx import Document

from asc.docx.formatter import STYLE_MAP, _ensure_style, _remove_paragraph_borders, apply_rule_to_style
from asc.models import JournalProfile


def generate_reference_docx(path: Path, profile: JournalProfile) -> None:
    document = Document()
    document.core_properties.title = f"{profile.journal.name} reference document"
    document.add_paragraph("Reference document for Pandoc style definitions", style="Title")
    _remove_paragraph_borders(document.styles["Title"].element)
    for profile_name, style_names in STYLE_MAP.items():
        rule = getattr(profile, profile_name)
        for style_name in style_names:
            apply_rule_to_style(_ensure_style(document, style_name), rule)
    for index, level in enumerate(("level1", "level2", "level3"), 1):
        if level in profile.headings:
            apply_rule_to_style(_ensure_style(document, f"Heading {index}"), profile.headings[level])
    for name in ("Affiliation", "Abstract", "Keywords", "Funding", "Bibliography", "Table Caption"):
        _ensure_style(document, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
