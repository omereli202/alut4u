#!/usr/bin/env python3
"""Inactivity retention sweep. Dry-run unless --apply is passed.

    python scripts/retention_purge.py            # report only
    python scripts/retention_purge.py --apply    # warn + purge for real

Schedule via cron / Railway cron. Needs the same env as the backend
(SUPABASE_* + SESSION_TOKEN_ENC_KEY + SUPABASE_JWT_SECRET).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.retention import run  # noqa: E402


def main() -> int:
    apply = "--apply" in sys.argv
    sweep = run(dry_run=not apply)
    mode = "APPLIED" if apply else "DRY RUN"
    print(f"[{mode}] retention sweep")
    print(f"  warned: {len(sweep.warned)}")
    print(f"  purged: {len(sweep.purged)}")
    for cid in sweep.purged:
        print(f"    purge {cid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
