from __future__ import annotations

import json
from pathlib import Path

from asc.models import JournalProfile


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "schemas" / "journal-profile.schema.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(JournalProfile.model_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

