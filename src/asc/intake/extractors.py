from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
import re
from typing import Any


class ProfileExtractor(ABC):
    """Provider-neutral contract: source text in, schema-shaped data out."""

    @abstractmethod
    def extract(self, source: Path, schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MockExtractor(ProfileExtractor):
    def __init__(self, result: dict[str, Any]):
        self.result = result

    def extract(self, source: Path, schema: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(self.result)


class TextRuleExtractor(ProfileExtractor):
    """Small deterministic MVP parser for explicit rules in TXT/Markdown guides."""

    def extract(self, source: Path, schema: dict[str, Any]) -> dict[str, Any]:
        text = source.read_text(encoding="utf-8-sig")
        rules: dict[str, Any] = {}
        patterns = {
            "title": r"标题[^。\n]{0,20}?(?P<size>二号|小二|三号|小三|四号|小四|五号|小五|\d+(?:\.\d+)?\s*pt)[^。\n]{0,20}?(?P<font>黑体|宋体|楷体|仿宋|Times New Roman)?",
            "body": r"正文[^。\n]{0,20}?(?P<size>小四|五号|10\.5\s*pt|12\s*pt)[^。\n]{0,20}?(?P<font>宋体|仿宋|楷体|Times New Roman)?",
        }
        size_map = {"二号": 22.0, "小二": 18.0, "三号": 16.0, "小三": 15.0, "四号": 14.0, "小四": 12.0, "五号": 10.5, "小五": 9.0}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            size_text = match.group("size").replace(" ", "")
            pt = size_map[size_text] if size_text in size_map else float(re.sub(r"[^0-9.]", "", size_text))
            rule: dict[str, Any] = {
                "size": {"chinese_name": size_text if "号" in size_text else None, "pt": pt},
                "confidence": "explicit",
                "provenance": {"source": source.name, "evidence": match.group(0).strip()},
            }
            if match.groupdict().get("font"):
                rule["font"] = {"east_asia": match.group("font")}
            rules[field] = rule
        return rules
