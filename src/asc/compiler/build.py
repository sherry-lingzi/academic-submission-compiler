from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from asc.citations import better_bibtex_ready, csl_m_reasons
from asc.compliance import Status, check_markdown, overall_status, render_report
from asc.docx import format_docx
from asc.models import JournalProfile, load_profile
from asc.markdown import extract_citations, parse_markdown
from asc.paths import resolve_journal, resolve_profile_path


@dataclass(frozen=True)
class BuildResult:
    docx: Path
    report: Path
    findings_status: Status
    command: tuple[str, ...]


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
    command = [
        pandoc,
        str(manuscript),
        "--standalone",
        "--from=markdown+citations+footnotes+wikilinks_title_after_pipe-implicit_figures",
        "--to=docx",
        f"--output={intermediate}",
        f"--resource-path={os.pathsep.join((str(manuscript.parent), str(root)))}",
        f"--lua-filter={root / 'filters' / 'obsidian.lua'}",
        f"--lua-filter={root / 'filters' / 'semantic-metadata.lua'}",
    ]
    reference_doc = resolve_profile_path(root, journal_dir, profile.output.reference_docx)
    if reference_doc.exists():
        command.append(f"--reference-doc={reference_doc}")
    if profile.anonymous_review.required:
        command.append("--metadata=asc-anonymous:true")
    if live_zotero:
        filter_path = root / "filters" / "zotero.lua"
        if not filter_path.exists():
            raise RuntimeError("Better BibTeX 官方 zotero.lua 未安装到 filters/zotero.lua")
        command.extend((f"--lua-filter={filter_path}", "--metadata=zotero_client:zotero"))
        if profile.citation.zotero_style:
            command.append(f"--metadata=zotero_csl-style:{profile.citation.zotero_style}")
    else:
        bibliography = resolve_profile_path(root, journal_dir, profile.citation.bibliography)
        csl = resolve_profile_path(root, journal_dir, profile.citation.csl)
        command.extend(("--citeproc", f"--bibliography={bibliography}", f"--csl={csl}", f"--metadata=lang:{profile.citation.locale}"))
    return command


def build(manuscript: Path, journal_id: str, root: Path, live_zotero: bool = False, allow_csl_m: bool = False) -> BuildResult:
    manuscript = manuscript.resolve()
    journal_dir, profile_path = resolve_journal(root, journal_id)
    profile = load_profile(profile_path)
    findings = check_markdown(manuscript, profile, root, journal_dir)
    status = overall_status(findings)
    if status == Status.FAIL:
        messages = "; ".join(item.message for item in findings if item.status == Status.FAIL)
        raise RuntimeError(f"构建前检查失败：{messages}")
    csl = resolve_profile_path(root, journal_dir, profile.citation.csl)
    reasons = csl_m_reasons(csl)
    if reasons and not live_zotero and not allow_csl_m and not profile.citation.allow_csl_m_static:
        raise RuntimeError("检测到 CSL-M 专用标记，Pandoc citeproc 可能误排；请使用 --live-zotero，或在核验后显式传入 --allow-csl-m")
    if live_zotero:
        ready, detail = better_bibtex_ready()
        if not ready:
            raise RuntimeError(f"Zotero Live Mode 需要正在运行的 Zotero + Better BibTeX：{detail}")

    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    basename = output_basename(manuscript, journal_id)
    if live_zotero:
        basename += "-live"
    output_path = dist / f"{basename}.docx"
    report_path = dist / f"{basename}-report.md"
    with tempfile.TemporaryDirectory(prefix="asc-build-") as temporary:
        intermediate = Path(temporary) / "intermediate.docx"
        command = pandoc_command(root, manuscript, journal_dir, profile, intermediate, live_zotero)
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode:
            raise RuntimeError(f"Pandoc 构建失败：\n{completed.stderr.strip() or completed.stdout.strip()}")
        if live_zotero:
            citekeys = {item.key for item in extract_citations(parse_markdown(manuscript).body)}
            fields, unresolved = live_docx_stats(intermediate, citekeys)
            if unresolved or (citekeys and fields == 0):
                detail = f"；未解析 citekey：{', '.join(sorted(unresolved))}" if unresolved else ""
                raise RuntimeError(f"Zotero live citation 未生成有效 Word fields{detail}。确认示例 citekey 存在于当前 Zotero library。")
        format_docx(intermediate, output_path, profile)
    report_path.write_text(render_report(profile, findings), encoding="utf-8")
    return BuildResult(output_path, report_path, status, tuple(command))
