from pathlib import Path
import importlib

from zipfile import ZipFile

from asc.compiler import live_docx_stats, output_basename, pandoc_command, render_output_filename, select_mode


def test_output_naming():
    assert output_basename(Path("C:/研究/example-paper/paper.md"), "journal-a") == "example-paper-journal-a"
    assert output_basename(Path("C:/研究/article.md"), "journal-b") == "article-journal-b"


def test_command_handles_windows_paths(monkeypatch, tmp_path: Path, profile):
    build_module = importlib.import_module("asc.compiler.build")
    monkeypatch.setattr(build_module.shutil, "which", lambda _: "C:/Program Files/Pandoc/pandoc.exe")
    root = tmp_path / "中文 project"
    journal = root / "journals/example-humanities-journal"
    journal.mkdir(parents=True)
    (root / "filters").mkdir()
    for name in ("obsidian.lua", "semantic-metadata.lua"):
        (root / "filters" / name).write_text("", encoding="utf-8")
    (root / "bibliography").mkdir()
    (root / "bibliography" / "references.json").write_text("[]", encoding="utf-8")
    (journal / "citation.csl").write_text("<style/>", encoding="utf-8")
    manuscript = root / "稿件 folder/paper.md"
    manuscript.parent.mkdir()
    output = tmp_path / "中间 文档.docx"
    command = pandoc_command(root, manuscript, journal, profile, output)
    assert command[0] == "C:/Program Files/Pandoc/pandoc.exe"
    assert str(manuscript) in command
    assert any("中间 文档.docx" in arg for arg in command)
    assert any("-implicit_figures" in arg for arg in command)
    assert not any(arg.startswith('"') for arg in command)


def test_static_and_live_are_independent(monkeypatch, tmp_path: Path, profile):
    build_module = importlib.import_module("asc.compiler.build")
    monkeypatch.setattr(build_module.shutil, "which", lambda _: "pandoc")
    root = tmp_path
    journal = root / "journals/j"
    journal.mkdir(parents=True)
    (root / "filters").mkdir()
    for name in ("zotero.lua", "obsidian.lua", "semantic-metadata.lua"):
        (root / "filters" / name).write_text("", encoding="utf-8")
    (root / "bibliography").mkdir()
    (root / "bibliography" / "references.json").write_text("[]", encoding="utf-8")
    (journal / "citation.csl").write_text("<style/>", encoding="utf-8")
    manuscript = root / "paper.md"
    static = pandoc_command(root, manuscript, journal, profile, root / "a.docx", False)
    live = pandoc_command(root, manuscript, journal, profile, root / "b.docx", True)
    assert "--citeproc" in static
    assert "--citeproc" not in live
    assert any("zotero.lua" in arg for arg in live)


def test_invalid_live_docx_is_detected(tmp_path: Path):
    path = tmp_path / "invalid-live.docx"
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", "<w:t>@missing</w:t>")
    fields, unresolved = live_docx_stats(path, {"missing"})
    assert fields == 0
    assert unresolved == {"missing"}


def test_profile_output_filename_is_safe(profile):
    profile.output.filename_pattern = "{manuscript}-{journal_id}-{mode}.docx"
    assert render_output_filename(profile.output.filename_pattern, Path("C:/中文 路径/paper.md"), profile, "static") == "中文 路径-example-humanities-journal-static.docx"
    for unsafe in ("../x.docx", "{manuscript}/x.docx", "x.docx.docx", "CON.docx", "x:{mode}.docx"):
        profile.output.filename_pattern = unsafe
        import pytest
        with pytest.raises(ValueError):
            render_output_filename(unsafe, Path("paper.md"), profile, "static")


def test_profile_default_mode_and_cli_override(profile):
    profile.citation.default_mode = "live-zotero"
    assert select_mode(profile, None) == "live-zotero"
    assert select_mode(profile, False) == "static"
    profile.citation.default_mode = "static"
    assert select_mode(profile, True) == "live-zotero"
