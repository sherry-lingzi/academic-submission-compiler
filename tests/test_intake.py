from pathlib import Path

from asc.intake import MockExtractor, TextRuleExtractor, create_generated_profile


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

