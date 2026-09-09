from pathlib import Path

from asc.citations import bibliography_keys, csl_m_reasons


def test_csl_json_and_bib_keys(root: Path):
    assert "hayles1999" in bibliography_keys(root / "bibliography/references.json")
    assert "liu2020" in bibliography_keys(root / "bibliography/references.bib")


def test_csl_m_detection(tmp_path: Path):
    style = tmp_path / "style.csl"
    style.write_text('<style version="1.0" default-locale-sort="zh-CN"/>', encoding="utf-8")
    assert "default-locale-sort" in csl_m_reasons(style)


def test_standard_csl_not_flagged(root: Path):
    assert not csl_m_reasons(root / "journals/example-humanities-journal/citation.csl")

