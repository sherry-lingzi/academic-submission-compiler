from pathlib import Path

import pytest

from asc.models import JournalProfile, load_profile


@pytest.fixture(scope="session")
def root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def profile(root: Path) -> JournalProfile:
    return load_profile(root / "journals" / "example-humanities-journal" / "profile.yaml")

