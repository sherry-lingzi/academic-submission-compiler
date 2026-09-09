from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


_CITEKEY = re.compile(r"(?<![\w@])@([A-Za-z0-9_:.#$%&+?<>~/\\-]+)")


@dataclass(frozen=True)
class AcademicMarkdown:
    path: Path
    metadata: dict[str, Any]
    body: str
    raw: str


@dataclass(frozen=True)
class Citation:
    key: str
    locator: str | None = None
    narrative: bool = False


def parse_markdown(path: Path) -> AcademicMarkdown:
    raw = path.read_text(encoding="utf-8-sig")
    metadata: dict[str, Any] = {}
    body = raw
    if raw.startswith("---"):
        lines = raw.splitlines(keepends=True)
        closing = next((i for i in range(1, len(lines)) if lines[i].strip() in {"---", "..."}), None)
        if closing is None:
            raise ValueError("YAML front matter is not closed")
        loaded = yaml.safe_load("".join(lines[1:closing])) or {}
        if not isinstance(loaded, dict):
            raise ValueError("YAML front matter must be a mapping")
        metadata = loaded
        body = "".join(lines[closing + 1 :])
    return AcademicMarkdown(path=path, metadata=metadata, body=body, raw=raw)


def prose_without_code(text: str) -> str:
    output: list[str] = []
    in_fence = False
    fence = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        result: list[str] = []
        in_inline = False
        for char in line:
            if char == "`":
                in_inline = not in_inline
                result.append(" ")
            elif not in_inline:
                result.append(char)
        output.append("".join(result))
    return "\n".join(output)


def extract_citations(text: str) -> list[Citation]:
    prose = prose_without_code(text)
    citations: list[Citation] = []
    for match in _CITEKEY.finditer(prose):
        bracket_start = prose.rfind("[", 0, match.start())
        previous_close = prose.rfind("]", 0, match.start())
        bracket_end = prose.find("]", match.end())
        locator = None
        narrative = bracket_start <= previous_close or bracket_end < 0
        if not narrative:
            tail = prose[match.end() : bracket_end]
            locator_match = re.search(r",\s*(?:p{1,2}\.?\s*)?([^;]+)", tail, re.IGNORECASE)
            if locator_match:
                locator = locator_match.group(1).strip()
        citations.append(Citation(match.group(1), locator, narrative))
    return citations


def wikilink_targets(text: str) -> list[str]:
    return [m.group(1).split("|", 1)[0].split("#", 1)[0].strip() for m in re.finditer(r"(?<!!)\[\[([^\]]+)\]\]", prose_without_code(text))]


def embed_targets(text: str) -> list[str]:
    return [m.group(1).split("|", 1)[0].split("#", 1)[0].strip() for m in re.finditer(r"!\[\[([^\]]+)\]\]", prose_without_code(text))]
