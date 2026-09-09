from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import string
import subprocess
import tempfile
from zipfile import ZipFile

from asc.citations import better_bibtex_ready, csl_m_reasons
from asc.compliance import check_markdown
from asc.docx import format_docx, inspect_docx
from asc.findings import Finding, Status, overall_status, render_report
from asc.models import JournalProfile, ProfileStatus, load_profile
from asc.markdown import extract_citations, parse_markdown
from asc.paths import resolve_journal, resolve_profile_resource


@dataclass(frozen=True)
class BuildResult:
    source_findings: tuple[Finding, ...]
    docx_findings: tuple[Finding, ...]
    final_status: Status
    command: tuple[str, ...]
    docx: Path
    report: Path
    mode: str

    @property
    def findings_status(self) -> Status:
        """Compatibility alias for ASC 0.1 callers."""
        return self.final_status


def live_docx_stats(path: Path, citekeys: set[str]) -> tuple[int, set[str]]:
    xml_parts: list[str] = []
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith(".xml"):
                xml_parts.append(archive.read(name).decode("utf-8", errors="ignore"))
    xml = "\n".join(xml_parts)
    fields = xml.count("ZOTERO_ITEM CSL_CITATION")
    unresolved = {key for key in citekeys if f"@{key}" in xml}
    return fields, unresolved


def output_basename(manuscript: Path, journal_id: str) -> str:
    manuscript_name = manuscript.parent.name if manuscript.stem.lower() in {"paper", "manuscript"} else manuscript.stem
    return f"{manuscript_name}-{journal_id}"


def select_mode(profile: JournalProfile, live_zotero: bool | None) -> str:
    return ("live-zotero" if live_zotero else "static") if live_zotero is not None else profile.citation.default_mode


def render_output_filename(pattern: str, manuscript: Path, profile: JournalProfile, mode: str) -> str:
    allowed = {"manuscript", "journal", "journal_id", "mode"}
    fields = {field for _, field, _, _ in string.Formatter().parse(pattern) if field}
    unknown = fields - allowed
    if unknown:
        raise ValueError(f"output.filename_pattern has unsupported placeholders: {', '.join(sorted(unknown))}")
    manuscript_name = manuscript.parent.name if manuscript.stem.lower() in {"paper", "manuscript"} else manuscript.stem
    values = {
        "manuscript": manuscript_name,
        "journal": profile.journal.id,
        "journal_id": profile.journal.id,
        "mode": "live" if mode == "live-zotero" else "static",
    }
    rendered = pattern.format(**values).strip()
    if mode == "live-zotero" and "{mode}" not in pattern and rendered.lower().endswith(".docx"):
        rendered = rendered[:-5] + "-live.docx"
    if not rendered or rendered in {".", ".."}:
        raise ValueError("output.filename_pattern produced an empty or unsafe filename")
    if Path(rendered).is_absolute() or "/" in rendered or "\\" in rendered or ".." in rendered:
        raise ValueError("output.filename_pattern must produce a filename, not a path")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', rendered):
        raise ValueError("output.filename_pattern produced Windows-invalid filename characters")
    if rendered.lower().count(".docx") != 1 or not rendered.lower().endswith(".docx"):
        raise ValueError("output.filename_pattern must end in exactly one `.docx`")
    stem = rendered[:-5]
    if not stem.strip(" ."):
        raise ValueError("output.filename_pattern produced an empty basename")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if stem.rstrip(" .").upper() in reserved:
        raise ValueError("output.filename_pattern produced a reserved Windows filename")
    return rendered


def _metadata_args(profile: JournalProfile) -> list[str]:
    args: list[str] = []
    for language in ("zh", "en"):
        separator = getattr(profile.keywords, language).separator
        fallback = "；" if language == "zh" else "; "
        args.append(f"--metadata=asc-keywords-{language}-separator:{separator if separator is not None else fallback}")
    if profile.anonymous_review.required:
        for field in ("authors", "affiliations", "funding", "email", "orcid", "correspondence", "acknowledgements"):
            if getattr(profile.anonymous_review, f"hide_{field}"):
                args.append(f"--metadata=asc-hide-{field}:true")
    return args


def pandoc_command(
    root: Path,
    manuscript: Path,
    journal_dir: Path,
    profile: JournalProfile,
    intermediate: Path,
    live_zotero: bool = False,
) -> list[str]:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("Pandoc 未安装或不在 PATH；运行 asc doctor 查看详情")
    resource_paths = [manuscript.parent.resolve(), root.resolve()]
    for configured in profile.obsidian.attachment_paths:
        path = Path(configured)
        path = path.resolve() if path.is_absolute() else (root / path).resolve()
        if path.exists() and path not in resource_paths:
            resource_paths.append(path)
    command = [
        pandoc,
        str(manuscript),
        "--standalone",
        "--from=markdown+citations+footnotes+wikilinks_title_after_pipe-implicit_figures",
        "--to=docx",
        f"--output={intermediate}",
        f"--resource-path={os.pathsep.join(str(path) for path in resource_paths)}",
        f"--lua-filter={resolve_profile_resource(root, journal_dir, 'filters/obsidian.lua', must_exist=True)}",
        f"--lua-filter={resolve_profile_resource(root, journal_dir, 'filters/semantic-metadata.lua', must_exist=True)}",
        *_metadata_args(profile),
    ]
    reference_doc = resolve_profile_resource(root, journal_dir, profile.output.reference_docx)
    if reference_doc.exists():
        command.append(f"--reference-doc={reference_doc}")
    if live_zotero:
        filter_path = resolve_profile_resource(root, journal_dir, "filters/zotero.lua", must_exist=True)
        command.extend((f"--lua-filter={filter_path}", "--metadata=zotero_client:zotero"))
        if profile.citation.zotero_style:
            command.append(f"--metadata=zotero_csl-style:{profile.citation.zotero_style}")
    else:
        bibliography = resolve_profile_resource(root, journal_dir, profile.citation.bibliography, must_exist=True)
        csl = resolve_profile_resource(root, journal_dir, profile.citation.csl, must_exist=True)
        command.extend(("--citeproc", f"--bibliography={bibliography}", f"--csl={csl}", f"--metadata=lang:{profile.citation.locale}"))
    return command


def _sensitive_values(metadata: dict, profile: JournalProfile) -> set[str]:
    values: set[str] = set()
    rule = profile.anonymous_review
    for author in metadata.get("authors") or []:
        if not isinstance(author, dict):
            if rule.hide_authors:
                values.add(str(author))
            continue
        if rule.hide_authors and author.get("name"):
            values.add(str(author["name"]))
        if rule.hide_affiliations and author.get("affiliation"):
            values.add(str(author["affiliation"]))
        if rule.hide_email and author.get("email"):
            values.add(str(author["email"]))
        if rule.hide_orcid and author.get("orcid"):
            values.add(str(author["orcid"]))
    for field in ("email", "orcid", "correspondence", "acknowledgements"):
        if getattr(rule, f"hide_{field}") and metadata.get(field):
            values.add(str(metadata[field]))
    if rule.hide_funding:
        for item in metadata.get("funding") or []:
            if isinstance(item, dict):
                values.update(str(value) for value in item.values() if value)
            elif item:
                values.add(str(item))
    return values


def build(manuscript: Path, journal_id: str, root: Path, live_zotero: bool | None = None, allow_csl_m: bool = False) -> BuildResult:
    manuscript = manuscript.resolve()
    journal_dir, profile_path = resolve_journal(root, journal_id)
    profile = load_profile(profile_path)
    mode = select_mode(profile, live_zotero)
    use_live = mode == "live-zotero"
    filename = render_output_filename(profile.output.filename_pattern, manuscript, profile, mode)
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    output_path = dist / filename
    report_path = dist / f"{Path(filename).stem}-report.md"

    source_findings = check_markdown(manuscript, profile, root, journal_dir)
    if profile.profile_status != ProfileStatus.approved or overall_status(source_findings) == Status.FAIL:
        empty_docx = Finding("DOCX Formatting Compliance", Status.UNKNOWN, "DOCX was not generated because preflight failed")
        report_path.write_text(render_report(profile, [*source_findings, empty_docx], output_path=str(output_path)), encoding="utf-8")
        messages = "; ".join(item.message for item in source_findings if item.status == Status.FAIL)
        raise RuntimeError(f"构建前检查失败：{messages}; report: {report_path}")

    csl = resolve_profile_resource(root, journal_dir, profile.citation.csl, must_exist=not use_live)
    reasons = csl_m_reasons(csl) if csl.exists() else []
    if reasons and not use_live and not allow_csl_m and not profile.citation.allow_csl_m_static:
        raise RuntimeError("检测到 CSL-M 专用标记，Pandoc citeproc 可能误排；请使用 --live-zotero，或在核验后显式传入 --allow-csl-m")
    if use_live:
        ready, detail = better_bibtex_ready()
        if not ready:
            raise RuntimeError(f"Zotero Live Mode 需要正在运行的 Zotero + Better BibTeX：{detail}")

    manuscript_data = parse_markdown(manuscript)
    citekeys = {item.key for item in extract_citations(manuscript_data.body)}
    with tempfile.TemporaryDirectory(prefix="asc-build-") as temporary:
        intermediate = Path(temporary) / "intermediate.docx"
        command = pandoc_command(root, manuscript, journal_dir, profile, intermediate, use_live)
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode:
            raise RuntimeError(f"Pandoc 构建失败：\n{completed.stderr.strip() or completed.stdout.strip()}")
        if use_live:
            fields, unresolved = live_docx_stats(intermediate, citekeys)
            if unresolved or (citekeys and fields == 0):
                detail = f"；未解析 citekey：{', '.join(sorted(unresolved))}" if unresolved else ""
                raise RuntimeError(f"Zotero live citation 未生成有效 Word fields{detail}。确认 citekey 存在于当前 Zotero library。")
        format_docx(intermediate, output_path, profile)

    docx_findings = inspect_docx(output_path, profile, _sensitive_values(manuscript_data.metadata, profile))
    fields, unresolved = live_docx_stats(output_path, citekeys)
    citation_post = Finding(
        "Citation Compliance",
        Status.FAIL if unresolved or (use_live and citekeys and fields == 0) else Status.PASS,
        f"Post-build unresolved citekeys: {', '.join(sorted(unresolved))}" if unresolved else (f"Live Zotero fields generated: {fields}" if use_live else "No citekeys remain in generated DOCX"),
    )
    all_findings = [*source_findings, citation_post, *docx_findings]
    final_status = overall_status(all_findings)
    report_path.write_text(render_report(profile, all_findings, build_command=command, output_path=str(output_path)), encoding="utf-8")
    return BuildResult(tuple(source_findings), tuple(docx_findings), final_status, tuple(command), output_path, report_path, mode)
