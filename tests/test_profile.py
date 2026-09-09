from pathlib import Path

import pytest
from pydantic import ValidationError

from asc.models import JournalProfile, StyleRule, load_profile


def test_valid_profile(root: Path):
    profile = load_profile(root / "journals/example-humanities-journal/profile.yaml")
    assert profile.journal.test_only
    assert profile.body.font.east_asia == "宋体"
    assert profile.body.size.pt == 12


def test_invalid_explicit_rule_without_provenance():
    with pytest.raises(ValidationError):
        StyleRule.model_validate({"confidence": "explicit", "font": {"east_asia": "宋体"}})


def test_conflicting_rule(profile: JournalProfile):
    changed = profile.model_copy(deep=True)
    changed.body.candidates = [{"value": 12, "source": "guide"}, {"value": 10.5, "source": "template"}]
    assert "body" in changed.conflicts()


def test_schema_contains_core_fields():
    schema = JournalProfile.model_json_schema()
    for field in ("journal", "document", "title", "body", "citation", "output"):
        assert field in schema["properties"]


def test_journal_profiles_change_typography(root: Path):
    regular = load_profile(root / "journals/example-humanities-journal/profile.yaml")
    compact = load_profile(root / "journals/example-compact-journal/profile.yaml")
    assert regular.body.font.east_asia == "宋体"
    assert compact.body.font.east_asia == "仿宋"
    assert regular.body.size.pt != compact.body.size.pt
