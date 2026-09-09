from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from asc.intake.extractors import ProfileExtractor
from asc.models import JournalProfile, dump_profile


def skeleton(journal_id: str, name: str) -> dict[str, Any]:
    return {
        "profile_version": "2.0",
        "profile_status": "generated",
        "journal": {"id": journal_id, "name": name, "language": "zh-CN"},
        "document": {
            "page_size": "A4",
            "margins": {"top_mm": 25.4, "bottom_mm": 25.4, "left_mm": 31.7, "right_mm": 31.7},
            "confidence": "unknown",
            "source_kind": "system_default",
        },
        "title": {"default": {}}, "authors": {}, "affiliations": {},
        "abstract": {"zh": {"label": {}, "body": {}}, "en": {"label": {}, "body": {}}},
        "keywords": {"zh": {"label": {}, "body": {}}, "en": {"label": {}, "body": {}}},
        "body": {},
        "headings": {"level1": {}, "level2": {}, "level3": {}},
        "footnotes": {}, "bibliography": {}, "funding": {}, "figures": {}, "tables": {},
        "anonymous_review": {"required": False, "confidence": "unknown"},
        "citation": {}, "output": {},
        "obsidian": {},
    }


def _confidence_counts(value: Any, counter: Counter[str]) -> None:
    if isinstance(value, dict):
        if value.get("confidence") in {"explicit", "inferred", "user_confirmed", "unknown"}:
            counter[value["confidence"]] += 1
        for child in value.values():
            _confidence_counts(child, counter)
    elif isinstance(value, list):
        for child in value:
            _confidence_counts(child, counter)


def create_generated_profile(
    journal_id: str,
    name: str,
    source: Path | None,
    extractor: ProfileExtractor | None,
    journal_dir: Path,
) -> JournalProfile:
    data = skeleton(journal_id, name)
    if source and extractor:
        extracted = extractor.extract(source, JournalProfile.model_json_schema())
        for key, value in extracted.items():
            if key in data:
                data[key] = {"default": value} if key == "title" and "default" not in value else value
    profile = JournalProfile.model_validate(data)
    generated = journal_dir / "profile.generated.yaml"
    dump_profile(profile, generated)
    serialized = profile.model_dump(mode="json", exclude_none=True)
    counts: Counter[str] = Counter()
    _confidence_counts(serialized, counts)
    conflicts = profile.conflicts()
    lines = [
        f"# {name} Profile Review",
        "",
        "This profile is generated for human review and is not approved for builds.",
        "",
        f"- ✓ explicit: {counts['explicit']}",
        f"- △ inferred: {counts['inferred']}",
        f"- ✓ user_confirmed: {counts['user_confirmed']}",
        f"- ? unknown: {counts['unknown']}",
        "",
        "## Conflicts",
        "",
    ]
    if conflicts:
        lines.extend(f"- CONFLICT {item}" for item in conflicts)
    else:
        lines.append("- No conflicts detected")
    lines.extend(["", "Review every unknown and inferred rule, then run `asc journal approve`. Approval never invents missing requirements.", ""])
    (journal_dir / "profile-review.md").write_text("\n".join(lines), encoding="utf-8")
    return profile
