from __future__ import annotations

import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


def bibliography_keys(path: Path) -> set[str]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            raise ValueError("CSL JSON bibliography must be an array")
        return {str(item["id"]) for item in data if isinstance(item, dict) and item.get("id")}
    text = path.read_text(encoding="utf-8-sig")
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", text))


def csl_m_reasons(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig").lower()
    reasons: list[str] = []
    for marker in ("1.1mlz", "citationstyles.org/schema/rng/1.1mlz", "juris-m", "court-class", "container-multiple", "default-locale-sort", "multi-layout", "jurisdiction"):
        if marker in text:
            reasons.append(marker)
    return reasons


def better_bibtex_ready(timeout: float = 0.8) -> tuple[bool, str]:
    payload = b'{"jsonrpc":"2.0","method":"api.ready","params":[],"id":1}'
    request = Request(
        "http://127.0.0.1:23119/better-bibtex/json-rpc",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = data.get("result", {})
        return True, f"Zotero {result.get('zotero', '?')} / Better BibTeX {result.get('betterbibtex', '?')}"
    except Exception as exc:  # local optional service; preserve a friendly diagnostic
        return False, str(exc)
