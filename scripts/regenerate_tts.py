#!/usr/bin/env python3
"""Re-synthesise every stored TTS asset against the configured provider.

Fixes the fallout of the provider-scoped cache-key change: every asset
written while TTS ran against the silent dev stub shares its digest with what
a real engine would produce for the same text, so those rows are stuck
pointing at silence until something walks the tables and repoints them.

    python scripts/regenerate_tts.py                          # dry run report
    python scripts/regenerate_tts.py --apply                  # re-synthesise + repoint
    python scripts/regenerate_tts.py --apply --purge-orphans  # + delete orphaned stub assets
    python scripts/regenerate_tts.py --apply --only aac_cards schedule_items

Refuses to run against the silent stub (pass --allow-silent to override) —
that would just rewrite everything to a new, still-silent digest.

Needs the same env as the backend, with a REAL Azure key — on Railway:

    railway run --service alut4u-backend --environment dev -- \\
        python scripts/regenerate_tts.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.tts.backfill import run  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    p.add_argument(
        "--purge-orphans",
        action="store_true",
        help="also delete now-unreferenced silent-stub tts_cache assets (run this after "
        "verifying regenerated audio, in a separate invocation)",
    )
    p.add_argument(
        "--only",
        nargs="+",
        choices=["aac_cards", "schedule_items", "behavior_rules", "social_stories"],
        help="limit to these tables (skips the board-template / reading-text warm pass)",
    )
    p.add_argument(
        "--allow-silent",
        action="store_true",
        help="proceed even if the silent stub is selected (normally refused)",
    )
    args = p.parse_args()

    b = run(
        dry_run=not args.apply,
        purge_orphans=args.purge_orphans,
        only=set(args.only) if args.only else None,
        allow_silent=args.allow_silent,
    )

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"[{mode}] tts regeneration — provider={b.provider}")
    print(f"  scanned:   {b.scanned}")
    print(f"  updated:   {b.updated}")
    print(f"  unchanged: {b.unchanged}")
    print(f"  warmed:    {b.warmed}")
    print(f"  failed:    {len(b.failed)}")
    for table, row_id in b.failed:
        print(f"    FAILED {table} {row_id}")
    if args.purge_orphans:
        print(f"  purged:    {len(b.purged)}")
    return 1 if b.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
