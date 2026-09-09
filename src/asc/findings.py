from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from asc.models import JournalProfile


class Status(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Finding:
    section: str
    status: Status
    message: str
    rule_path: str | None = None
    expected: str | None = None
    detected: str | None = None

    @property
    def ok(self) -> bool:
        return self.status != Status.FAIL

    @property
    def label(self) -> str:
        return self.rule_path or self.message


def overall_status(findings: Iterable[Finding]) -> Status:
    statuses = {finding.status for finding in findings}
    if Status.FAIL in statuses:
        return Status.FAIL
    if Status.WARNING in statuses:
        return Status.WARNING
    if Status.UNKNOWN in statuses:
        return Status.UNKNOWN
    return Status.PASS


REPORT_SECTIONS = (
    "Source / Markdown Compliance",
    "Citation Compliance",
    "DOCX Formatting Compliance",
    "Anonymous Review",
    "Profile / Unknown Rules",
)


def render_report(
    profile: JournalProfile,
    findings: list[Finding],
    *,
    build_command: Iterable[str] | None = None,
    output_path: str | None = None,
) -> str:
    symbols = {Status.PASS: "✓", Status.WARNING: "△", Status.FAIL: "✗", Status.UNKNOWN: "?"}
    lines = [
        "# Submission Compliance",
        "",
        f"Journal: {profile.journal.name}",
        "",
        f"Overall: **{overall_status(findings).value}**",
        "",
    ]
    if build_command:
        lines.extend(["Build command: `" + " ".join(str(part) for part in build_command) + "`", ""])
    if output_path:
        lines.extend([f"Output: `{output_path}`", ""])
    for section in REPORT_SECTIONS:
        lines.extend([f"## {section}", ""])
        selected = [item for item in findings if item.section == section]
        if not selected:
            lines.append("- ? **UNKNOWN** No checks were produced for this section.")
        for finding in selected:
            line = f"- {symbols[finding.status]} **{finding.status.value}** {finding.message}"
            if finding.expected is not None or finding.detected is not None:
                line += f" (required: {finding.expected or 'unknown'}; generated: {finding.detected or 'unknown'})"
            lines.append(line)
        lines.append("")
    coverage = profile.coverage()
    lines.extend(
        [
            "## Profile Coverage",
            "",
            f"- Explicit rules: {coverage['explicit']}",
            f"- Inferred rules: {coverage['inferred']}",
            f"- User-confirmed rules: {coverage['user_confirmed']}",
            f"- Unknown rules: {len(profile.unknown_rules())}",
            f"- System fallbacks used: {coverage['system_default']}",
            f"- Unsupported configured rules: {coverage['unsupported']}",
            f"- Conflicts: {coverage['conflict']}",
            "",
        ]
    )
    return "\n".join(lines)
