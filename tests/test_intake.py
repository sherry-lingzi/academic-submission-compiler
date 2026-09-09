from pathlib import Path
from argparse import Namespace

import pytest

from asc.intake import MockExtractor, TextRuleExtractor, create_generated_profile
from asc.models import ProfileStatus, load_profile


def test_mock_extractor():
    result = {"title": {"confidence": "unknown"}}
    assert MockExtractor(result).extract(Path("ignored"), {}) == result


def test_text_extractor_records_evidence(tmp_path: Path):
    source = tmp_path / "guide.txt"
    source.write_text("论文标题采用二号黑体居中。正文采用小四宋体。", encoding="utf-8")
    extracted = TextRuleExtractor().extract(source, {})
    assert extracted["title"]["size"]["pt"] == 22
    assert extracted["title"]["confidence"] == "explicit"
    assert extracted["title"]["provenance"]["evidence"]


def test_generated_profile_requires_approval(tmp_path: Path):
    profile = create_generated_profile("test-journal", "测试刊", None, None, tmp_path)
    assert profile.journal.id == "test-journal"
    assert (tmp_path / "profile.generated.yaml").exists()
    assert not (tmp_path / "profile.yaml").exists()


def test_approval_requires_explicit_allow_unknown(tmp_path: Path, monkeypatch):
    from asc import cli

    journal_dir = tmp_path / "journals" / "test-journal"
    journal_dir.mkdir(parents=True)
    create_generated_profile("test-journal", "测试刊", None, None, journal_dir)
    monkeypatch.setattr(cli, "_root", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="--allow-unknown"):
        cli.journal_approve_command(Namespace(id="test-journal", allow_unknown=False))
    assert cli.journal_approve_command(Namespace(id="test-journal", allow_unknown=True)) == 0
    assert load_profile(journal_dir / "profile.yaml").profile_status == ProfileStatus.approved
