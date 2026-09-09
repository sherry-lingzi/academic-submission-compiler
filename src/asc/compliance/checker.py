from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Any

from asc.citations import bibliography_keys, csl_m_reasons
from asc.markdown import embed_targets, extract_citations, parse_markdown
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


def _get(meta: dict[str, Any], *path: str) -> Any:
    current: Any = meta
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _count_text(value: Any, unit: str) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        text = "\n".join(str(v) for v in value.values())
    else:
        text = str(value)
    if unit == "characters":
        return len(re.sub(r"\s+", "", text))
    return len(re.findall(r"[\u3400-\u9fff]|[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text))


def _check_bounds(section: str, label: str, count: int, constraint: Any) -> list[Finding]:
    if not constraint:
        return [Finding(section, Status.UNKNOWN, f"期刊未规定{label}限制")]
    failures: list[str] = []
    if constraint.minimum is not None and count < constraint.minimum:
        failures.append(f"少于最小值 {constraint.minimum}")
    if constraint.maximum is not None and count > constraint.maximum:
        failures.append(f"超过最大值 {constraint.maximum}")
    if failures:
        return [Finding(section, Status.FAIL, f"{label}为 {count}，{'；'.join(failures)}")]
    return [Finding(section, Status.PASS, f"{label}为 {count}")]


def check_markdown(path: Path, profile: JournalProfile, root: Path, journal_dir: Path) -> list[Finding]:
    try:
        manuscript = parse_markdown(path)
    except Exception as exc:
        return [Finding("Markdown", Status.FAIL, f"无法解析 Markdown：{exc}")]

    meta, body = manuscript.metadata, manuscript.body
    findings: list[Finding] = []
    required = {
        "title": "标题",
        "authors": "作者",
        "abstract": "摘要",
        "keywords": "关键词",
    }
    for key, label in required.items():
        findings.append(Finding("Metadata", Status.PASS if meta.get(key) else Status.FAIL, f"{label}{'已提供' if meta.get(key) else '缺失'}"))
    authors = meta.get("authors") or []
    has_affiliation = bool(meta.get("affiliations")) or any(isinstance(a, dict) and a.get("affiliation") for a in authors)
    findings.append(Finding("Metadata", Status.PASS if has_affiliation else Status.FAIL, f"作者单位{'已提供' if has_affiliation else '缺失'}"))
    if profile.funding.confidence != "unknown":
        findings.append(Finding("Metadata", Status.PASS if meta.get("funding") else Status.WARNING, "基金信息已提供" if meta.get("funding") else "期刊规则涉及基金信息，但稿件未提供"))

    abstract = meta.get("abstract")
    if isinstance(abstract, dict):
        for language, value in abstract.items():
            findings.extend(_check_bounds("Content", f"{language} 摘要长度", _count_text(value, profile.abstract_count.unit if profile.abstract_count else "words"), profile.abstract_count))
    else:
        findings.extend(_check_bounds("Content", "摘要长度", _count_text(abstract, profile.abstract_count.unit if profile.abstract_count else "words"), profile.abstract_count))
    findings.extend(_check_bounds("Content", "正文字数", _count_text(body, profile.word_count.unit if profile.word_count else "words"), profile.word_count))
    keywords = meta.get("keywords") or {}
    keyword_values = [item for values in keywords.values() for item in values] if isinstance(keywords, dict) else list(keywords)
    findings.extend(_check_bounds("Content", "关键词数量", len(keyword_values), profile.keyword_count))

    bibliography = Path(profile.citation.bibliography)
    if not bibliography.is_absolute():
        bibliography = root / bibliography
    if not bibliography.exists():
        findings.append(Finding("Citation", Status.FAIL, f"bibliography 不存在：{bibliography}"))
        known: set[str] = set()
    else:
        try:
            known = bibliography_keys(bibliography)
            findings.append(Finding("Citation", Status.PASS, f"bibliography 可读取，共 {len(known)} 条记录"))
        except Exception as exc:
            known = set()
            findings.append(Finding("Citation", Status.FAIL, f"bibliography 无法解析：{exc}"))
    cited = extract_citations(body)
    missing = sorted({citation.key for citation in cited if citation.key not in known})
    findings.append(Finding("Citation", Status.FAIL if missing else Status.PASS, f"未解析 citekey：{', '.join(missing)}" if missing else f"全部 {len(cited)} 个引用标记均可解析"))
    manual = re.findall(r"(?:\(|（)[A-Z\u3400-\u9fff][^()（）]{0,45}?\b(?:19|20)\d{2}[a-z]?(?:\)|）)", body)
    findings.append(Finding("Citation", Status.WARNING if manual else Status.PASS, f"发现 {len(manual)} 处疑似手写作者年份引用" if manual else "未发现明显手写作者年份引用"))

    csl_path = journal_dir / profile.citation.csl
    if not csl_path.exists():
        findings.append(Finding("Citation", Status.FAIL, f"CSL 不存在：{csl_path}"))
    else:
        reasons = csl_m_reasons(csl_path)
        findings.append(Finding("Citation", Status.WARNING if reasons else Status.PASS, "检测到 CSL-M 扩展；static 模式默认拒绝构建并建议 Zotero live mode" if reasons else "CSL 未检测到 CSL-M 专用标记"))

    embeds = embed_targets(body)
    for target in embeds:
        candidate = (path.parent / target).resolve()
        findings.append(Finding("Markdown", Status.PASS if candidate.exists() else Status.FAIL, f"嵌入文件{'存在' if candidate.exists() else '缺失'}：{target}"))
    note_embeds = [target for target in embeds if Path(target).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}]
    if note_embeds:
        findings.append(Finding("Markdown", Status.WARNING, "Obsidian note embed 仅展开图片；笔记嵌入当前保留为可见提示"))
    else:
        findings.append(Finding("Markdown", Status.PASS, "未发现无法处理的 Obsidian note embed"))

    if profile.anonymous_review.required:
        leaks = []
        if meta.get("authors"):
            leaks.append("作者")
        if has_affiliation:
            leaks.append("单位")
        if meta.get("funding"):
            leaks.append("基金")
        findings.append(Finding("Anonymous review", Status.WARNING if leaks else Status.PASS, f"源稿含可识别元数据（构建时会隐藏，不修改源稿）：{', '.join(leaks)}" if leaks else "未发现显式身份元数据"))
    else:
        status = Status.UNKNOWN if profile.anonymous_review.confidence == "unknown" else Status.PASS
        message = "期刊未说明是否匿名审稿" if status == Status.UNKNOWN else "该 profile 明确不要求匿名审稿"
        findings.append(Finding("Anonymous review", status, message))
    for conflict in profile.conflicts():
        findings.append(Finding("Profile", Status.FAIL, f"CONFLICT：{conflict} 存在多个候选值，须人工确认"))
    return findings


def overall_status(findings: list[Finding]) -> Status:
    statuses = {finding.status for finding in findings}
    if Status.FAIL in statuses:
        return Status.FAIL
    if Status.WARNING in statuses:
        return Status.WARNING
    if Status.UNKNOWN in statuses:
        return Status.UNKNOWN
    return Status.PASS


def render_report(profile: JournalProfile, findings: list[Finding]) -> str:
    symbols = {Status.PASS: "✓", Status.WARNING: "△", Status.FAIL: "✗", Status.UNKNOWN: "?"}
    lines = ["# Submission Compliance", "", f"Journal: {profile.journal.name}", "", f"Overall: **{overall_status(findings).value}**", ""]
    sections: list[str] = []
    for finding in findings:
        if finding.section not in sections:
            sections.append(finding.section)
    for section in sections:
        lines.extend([f"## {section}", ""])
        for finding in (item for item in findings if item.section == section):
            lines.append(f"- {symbols[finding.status]} **{finding.status.value}** {finding.message}")
        lines.append("")
    return "\n".join(lines)
