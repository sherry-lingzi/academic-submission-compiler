from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from asc.citations import bibliography_keys, csl_m_reasons
from asc.findings import Finding, Status, overall_status, render_report
from asc.markdown import embed_targets, extract_citations, parse_markdown
from asc.models import Confidence, JournalProfile, ProfileStatus, SourceKind
from asc.paths import attachment_candidates, resolve_profile_resource


SOURCE = "Source / Markdown Compliance"
CITATION = "Citation Compliance"
ANONYMOUS = "Anonymous Review"
PROFILE = "Profile / Unknown Rules"


def _count_text(value: Any, unit: str) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        text = "\n".join(str(v) for v in value.values())
    else:
        text = str(value)
    if unit == "items":
        return len(value) if isinstance(value, (list, tuple, set)) else int(bool(text.strip()))
    if unit == "characters":
        return len(re.sub(r"\s+", "", text))
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[\u3400-\u9fff]", text))


def _check_bounds(label: str, count: int, constraint: Any) -> list[Finding]:
    if not constraint:
        return [Finding(SOURCE, Status.UNKNOWN, f"{label}: journal requirement unknown")]
    failures: list[str] = []
    if constraint.minimum is not None and count < constraint.minimum:
        failures.append(f"below minimum {constraint.minimum}")
    if constraint.maximum is not None and count > constraint.maximum:
        failures.append(f"above maximum {constraint.maximum}")
    if failures:
        return [Finding(SOURCE, Status.FAIL, f"{label}: {count} ({'; '.join(failures)})")]
    if constraint.confidence == Confidence.unknown or constraint.source_kind == SourceKind.system_default:
        return [Finding(SOURCE, Status.UNKNOWN, f"{label}: journal requirement unknown; observed {count} using ASC fallback unit `{constraint.unit}`")]
    return [Finding(SOURCE, Status.PASS, f"{label}: {count} {constraint.unit}")]


def _identity_values(meta: dict[str, Any], key: str) -> list[str]:
    values: list[str] = []
    direct = meta.get(key)
    if direct:
        values.append(str(direct))
    for author in meta.get("authors") or []:
        if isinstance(author, dict) and author.get(key):
            values.append(str(author[key]))
    return values


def check_markdown(path: Path, profile: JournalProfile, root: Path, journal_dir: Path) -> list[Finding]:
    try:
        manuscript = parse_markdown(path)
    except Exception as exc:
        return [Finding(SOURCE, Status.FAIL, f"Cannot parse Markdown: {exc}")]

    meta, body = manuscript.metadata, manuscript.body
    findings: list[Finding] = []
    for key, label in {"title": "Title", "authors": "Authors", "abstract": "Abstract", "keywords": "Keywords"}.items():
        findings.append(Finding(SOURCE, Status.PASS if meta.get(key) else Status.FAIL, f"{label} {'present' if meta.get(key) else 'missing'}"))
    authors = meta.get("authors") or []
    has_affiliation = bool(meta.get("affiliations")) or any(isinstance(a, dict) and a.get("affiliation") for a in authors)
    findings.append(Finding(SOURCE, Status.PASS if has_affiliation else Status.FAIL, f"Affiliations {'present' if has_affiliation else 'missing'}"))
    if profile.funding.confidence != Confidence.unknown:
        findings.append(Finding(SOURCE, Status.PASS if meta.get("funding") else Status.WARNING, "Funding present" if meta.get("funding") else "Profile has a funding rule but manuscript has no funding metadata"))

    abstract = meta.get("abstract") or {}
    if not isinstance(abstract, dict):
        abstract = {"zh": abstract}
    for language in ("zh", "en"):
        variant = getattr(profile.abstract, language)
        findings.extend(_check_bounds(f"{language.upper()} abstract count", _count_text(abstract.get(language), variant.count.unit if variant.count else ("characters" if language == "zh" else "words")), variant.count))
    findings.extend(_check_bounds("Body count", _count_text(body, profile.word_count.unit if profile.word_count else "words"), profile.word_count))

    keywords = meta.get("keywords") or {}
    if not isinstance(keywords, dict):
        keywords = {"zh": keywords}
    for language in ("zh", "en"):
        values = keywords.get(language) or []
        variant = getattr(profile.keywords, language)
        findings.extend(_check_bounds(f"{language.upper()} keywords count", _count_text(values, "items"), variant.count))

    bibliography = resolve_profile_resource(root, journal_dir, profile.citation.bibliography)
    if not bibliography.exists():
        findings.append(Finding(CITATION, Status.FAIL, f"Bibliography missing: {bibliography}"))
        known: set[str] = set()
    else:
        try:
            known = bibliography_keys(bibliography)
            findings.append(Finding(CITATION, Status.PASS, f"Bibliography readable with {len(known)} records"))
        except Exception as exc:
            known = set()
            findings.append(Finding(CITATION, Status.FAIL, f"Bibliography cannot be parsed: {exc}"))
    cited = extract_citations(body)
    missing = sorted({citation.key for citation in cited if citation.key not in known})
    findings.append(Finding(CITATION, Status.FAIL if missing else Status.PASS, f"Unresolved citekeys: {', '.join(missing)}" if missing else f"All {len(cited)} citation markers resolve"))
    manual = re.findall(r"(?:\(|（)[A-Z\u3400-\u9fff][^()（）]{0,45}?\b(?:19|20)\d{2}[a-z]?(?:\)|）)", body)
    findings.append(Finding(CITATION, Status.WARNING if manual else Status.PASS, f"Found {len(manual)} possible manually formatted author-year citations" if manual else "No obvious manually formatted author-year citations"))

    csl_path = resolve_profile_resource(root, journal_dir, profile.citation.csl)
    if not csl_path.exists():
        findings.append(Finding(CITATION, Status.FAIL, f"CSL missing: {csl_path}"))
    else:
        reasons = csl_m_reasons(csl_path)
        findings.append(Finding(CITATION, Status.WARNING if reasons else Status.PASS, "CSL-M extensions detected; static mode requires explicit override" if reasons else "No CSL-M-only markers detected"))

    for target in embed_targets(body):
        candidates = attachment_candidates(path, target, root, profile.obsidian.attachment_paths)
        if len(candidates) > 1:
            findings.append(Finding(SOURCE, Status.FAIL, f"AMBIGUOUS attachment `{target}`: {', '.join(str(item) for item in candidates)}"))
        else:
            findings.append(Finding(SOURCE, Status.PASS if candidates else Status.FAIL, f"Attachment {'resolved' if candidates else 'missing'}: {target}"))
    note_embeds = [target for target in embed_targets(body) if Path(target).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}]
    findings.append(Finding(SOURCE, Status.WARNING if note_embeds else Status.PASS, "Note embeds remain visible placeholders" if note_embeds else "No unsupported note embeds"))

    if profile.anonymous_review.required:
        leaks: list[str] = []
        checks = [
            (profile.anonymous_review.hide_authors and bool(meta.get("authors")), "authors"),
            (profile.anonymous_review.hide_affiliations and has_affiliation, "affiliations"),
            (profile.anonymous_review.hide_funding and bool(meta.get("funding")), "funding"),
            (profile.anonymous_review.hide_email and bool(_identity_values(meta, "email")), "email"),
            (profile.anonymous_review.hide_orcid and bool(_identity_values(meta, "orcid")), "ORCID"),
            (profile.anonymous_review.hide_correspondence and bool(meta.get("correspondence")), "correspondence"),
            (profile.anonymous_review.hide_acknowledgements and bool(meta.get("acknowledgements")), "acknowledgements"),
        ]
        leaks = [name for present, name in checks if present]
        findings.append(Finding(ANONYMOUS, Status.WARNING if leaks else Status.PASS, f"Source contains identity data that the anonymous build must remove: {', '.join(leaks)}" if leaks else "No configured identity fields found in source"))
    else:
        unknown = profile.anonymous_review.confidence == Confidence.unknown
        findings.append(Finding(ANONYMOUS, Status.UNKNOWN if unknown else Status.PASS, "Journal anonymous-review requirement unknown; no anonymization applied" if unknown else "Profile explicitly does not require anonymous review"))

    if profile.profile_status != ProfileStatus.approved:
        findings.append(Finding(PROFILE, Status.FAIL, f"Profile status is `{profile.profile_status.value}`; build requires `approved`"))
    for conflict in profile.conflicts():
        findings.append(Finding(PROFILE, Status.FAIL, f"CONFLICT: {conflict} has multiple candidates"))
    for unsupported in profile.unsupported_configured():
        findings.append(Finding(PROFILE, Status.FAIL, f"Profile field `{unsupported}` is configured, but ASC 0.2.0 does not implement this rule", rule_path=unsupported))
    unknown_rules = profile.unknown_rules()
    if unknown_rules:
        findings.append(Finding(PROFILE, Status.UNKNOWN, f"{len(unknown_rules)} journal requirements remain unknown; configured system fallbacks are not journal compliance: {', '.join(unknown_rules)}"))
    else:
        findings.append(Finding(PROFILE, Status.PASS, "No unknown journal requirements or system fallbacks"))
    return findings


__all__ = ["Finding", "Status", "check_markdown", "overall_status", "render_report"]
