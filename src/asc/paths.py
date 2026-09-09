from __future__ import annotations

from pathlib import Path
from typing import Iterable


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


def resolve_profile_resource(root: Path, journal_dir: Path, value: str, *, must_exist: bool = False) -> Path:
    """Resolve all profile resources with one deterministic policy."""
    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        local = (journal_dir / candidate).resolve()
        resolved = local if local.exists() else (root / candidate).resolve()
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"profile resource not found: {value} (resolved to {resolved})")
    return resolved


def resolve_profile_path(root: Path, journal_dir: Path, value: str) -> Path:
    """Compatibility alias for callers written against ASC 0.1."""
    return resolve_profile_resource(root, journal_dir, value)


def attachment_candidates(manuscript: Path, target: str, root: Path, attachment_paths: Iterable[str]) -> list[Path]:
    requested = Path(target)
    if requested.is_absolute():
        return [requested.resolve()] if requested.exists() else []
    candidates = [(manuscript.parent / requested).resolve()]
    for configured in attachment_paths:
        base = Path(configured)
        if not base.is_absolute():
            base = root / base
        candidates.append((base / requested).resolve())
    candidates.append((root / requested).resolve())
    unique: list[Path] = []
    for candidate in candidates:
        if candidate.exists() and candidate not in unique:
            unique.append(candidate)
    return unique


def resolve_attachment(manuscript: Path, target: str, root: Path, attachment_paths: Iterable[str]) -> Path | None:
    candidates = attachment_candidates(manuscript, target, root, attachment_paths)
    if len(candidates) > 1:
        rendered = ", ".join(str(path) for path in candidates)
        raise ValueError(f"AMBIGUOUS attachment `{target}`: {rendered}")
    return candidates[0] if candidates else None
