from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from asc.models import ProfileStatus, dump_profile, load_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate ASC Journal Profile 1.0 YAML to 2.0")
    parser.add_argument("profiles", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.profiles:
        profile = load_profile(path)
        if path.name == "profile.yaml":
            profile.profile_status = ProfileStatus.approved
            profile.approved_at = profile.approved_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        dump_profile(profile, path)
        print(path)


if __name__ == "__main__":
    main()
