from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "journals").exists():
            return candidate
    raise FileNotFoundError("cannot find project root containing pyproject.toml and journals/")


def resolve_journal(root: Path, journal_id: str) -> tuple[Path, Path]:
    journal_dir = root / "journals" / journal_id
    profile_path = journal_dir / "profile.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"approved journal profile not found: {profile_path}")
    return journal_dir, profile_path


def resolve_profile_path(root: Path, journal_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    local = journal_dir / candidate
    if local.exists():
        return local
    return root / candidate

