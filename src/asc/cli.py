from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from pydantic import ValidationError

from asc.citations import better_bibtex_ready
from asc.compiler import build
from asc.compliance import Status, check_markdown, overall_status, render_report
from asc.docx import generate_reference_docx, inspect_docx
from asc.intake import TextRuleExtractor, create_generated_profile
from asc.models import JournalProfile, load_profile
from asc.paths import find_project_root, resolve_journal


def _root() -> Path:
    return find_project_root()


def _command_version(name: str) -> tuple[bool, str]:
    executable = shutil.which(name)
    if not executable:
        return False, "not installed"
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, errors="replace", timeout=4)
        first = (result.stdout or result.stderr).splitlines()[0]
        return result.returncode == 0, first
    except Exception as exc:
        return False, str(exc)


def doctor_command(_: argparse.Namespace) -> int:
    rows: list[tuple[str, bool | None, str]] = [("Python", True, platform.python_version())]
    for name, optional in (("Pandoc", False), ("Git", False), ("curl", True), ("Quarto", True)):
        ok, detail = _command_version(name.lower())
        suffix = " (needed by live mode)" if name == "curl" and not ok else " (optional)" if optional and not ok else ""
        rows.append((name, None if optional and not ok else ok, detail + suffix))
    ready, detail = better_bibtex_ready()
    zotero_paths = [Path("C:/Program Files/Zotero/zotero.exe"), Path.home() / "AppData/Local/Zotero/zotero.exe"]
    zotero = shutil.which("zotero") or next((str(path) for path in zotero_paths if path.exists()), None)
    rows.append(("Zotero", bool(zotero) or ready, zotero or (detail if ready else "not found in common Windows locations")))
    rows.append(("Better BibTeX", ready, detail if ready else "local API unavailable; start Zotero with Better BibTeX for live mode"))
    for name, ok, detail in rows:
        symbol = "✓" if ok is True else "△" if ok is None else "✗"
        print(f"{symbol} {name}: {detail}")
    return 0 if all(ok is not False for name, ok, _ in rows if name in {"Python", "Pandoc", "Git"}) else 1


def check_command(args: argparse.Namespace) -> int:
    root = _root()
    journal_dir, profile_path = resolve_journal(root, args.journal)
    profile = load_profile(profile_path)
    findings = check_markdown(Path(args.manuscript).resolve(), profile, root, journal_dir)
    report = render_report(profile, findings)
    print(report)
    return 1 if overall_status(findings) == Status.FAIL else 0


def build_command(args: argparse.Namespace) -> int:
    result = build(Path(args.manuscript), args.journal, _root(), args.live_zotero, args.allow_csl_m)
    print(f"DOCX: {result.docx}")
    print(f"REPORT: {result.report}")
    print(f"STATUS: {result.findings_status.value}")
    return 0


def inspect_command(args: argparse.Namespace) -> int:
    root = _root()
    _, profile_path = resolve_journal(root, args.journal)
    findings = inspect_docx(Path(args.docx).resolve(), load_profile(profile_path))
    for item in findings:
        symbol = "✓" if item.ok else "✗"
        print(f"{symbol} {item.label}: expected {item.expected}; detected {item.detected}")
    return 0 if all(item.ok for item in findings) else 1


def journal_list_command(_: argparse.Namespace) -> int:
    root = _root()
    for directory in sorted((root / "journals").iterdir()):
        if directory.is_dir() and (directory / "profile.yaml").exists():
            profile = load_profile(directory / "profile.yaml")
            suffix = " [TEST]" if profile.journal.test_only else ""
            print(f"{profile.journal.id}\t{profile.journal.name}{suffix}")
    return 0


def journal_create_command(args: argparse.Namespace) -> int:
    root = _root()
    journal_dir = root / "journals" / args.id
    journal_dir.mkdir(parents=True, exist_ok=True)
    source = Path(args.source).resolve() if args.source else None
    copied_source = None
    if source:
        if source.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("MVP intake currently accepts .txt and .md; PDF/DOCX/HTML adapters are reserved")
        source_dir = journal_dir / "source"
        source_dir.mkdir(exist_ok=True)
        copied_source = source_dir / source.name
        shutil.copy2(source, copied_source)
    profile = create_generated_profile(args.id, args.name, copied_source, TextRuleExtractor() if copied_source else None, journal_dir)
    print(journal_dir / "profile.generated.yaml")
    print(journal_dir / "profile-review.md")
    print(f"Generated {profile.journal.name}; review before approval")
    return 0


def journal_approve_command(args: argparse.Namespace) -> int:
    journal_dir = _root() / "journals" / args.id
    generated = journal_dir / "profile.generated.yaml"
    if not generated.exists():
        raise FileNotFoundError(generated)
    profile = load_profile(generated)
    if profile.conflicts():
        raise RuntimeError(f"cannot approve unresolved conflicts: {', '.join(profile.conflicts())}")
    shutil.copy2(generated, journal_dir / "profile.yaml")
    print(journal_dir / "profile.yaml")
    return 0


def journal_inspect_command(args: argparse.Namespace) -> int:
    journal_dir = _root() / "journals" / args.id
    profile_path = journal_dir / ("profile.yaml" if (journal_dir / "profile.yaml").exists() else "profile.generated.yaml")
    profile = load_profile(profile_path)
    print(json.dumps(profile.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2))
    if profile.conflicts():
        print(f"CONFLICT: {', '.join(profile.conflicts())}")
        return 1
    return 0


def journal_reference_command(args: argparse.Namespace) -> int:
    journal_dir, profile_path = resolve_journal(_root(), args.id)
    profile = load_profile(profile_path)
    target = journal_dir / profile.output.reference_docx
    generate_reference_docx(target, profile)
    print(target)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="asc", description="Academic Submission Compiler")
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="detect local dependencies")
    doctor.set_defaults(handler=doctor_command)
    check = commands.add_parser("check", help="check semantic Markdown")
    check.add_argument("manuscript")
    check.add_argument("--journal", required=True)
    check.set_defaults(handler=check_command)
    build_parser = commands.add_parser("build", help="compile DOCX and compliance report")
    build_parser.add_argument("manuscript")
    build_parser.add_argument("--journal", required=True)
    build_parser.add_argument("--live-zotero", action="store_true")
    build_parser.add_argument("--allow-csl-m", action="store_true", help="explicitly accept Pandoc citeproc risk")
    build_parser.set_defaults(handler=build_command)
    inspect = commands.add_parser("inspect", help="inspect generated DOCX formatting")
    inspect.add_argument("docx")
    inspect.add_argument("--journal", required=True)
    inspect.set_defaults(handler=inspect_command)
    journal = commands.add_parser("journal", help="manage journal profiles")
    journal_commands = journal.add_subparsers(dest="journal_command", required=True)
    listing = journal_commands.add_parser("list")
    listing.set_defaults(handler=journal_list_command)
    create = journal_commands.add_parser("create")
    create.add_argument("--id", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--source")
    create.set_defaults(handler=journal_create_command)
    approve = journal_commands.add_parser("approve")
    approve.add_argument("id")
    approve.set_defaults(handler=journal_approve_command)
    journal_inspect = journal_commands.add_parser("inspect")
    journal_inspect.add_argument("id")
    journal_inspect.set_defaults(handler=journal_inspect_command)
    reference = journal_commands.add_parser("reference")
    reference.add_argument("id")
    reference.set_defaults(handler=journal_reference_command)
    return root


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    try:
        args = parser().parse_args(argv)
        return int(args.handler(args))
    except (FileNotFoundError, ValueError, RuntimeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
