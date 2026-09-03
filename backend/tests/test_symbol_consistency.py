"""Cross-representation consistency for the Mulberry symbol set.

Pure filesystem + text parsing — no Supabase needed, so this runs in every CI
job. Guards the exact failure mode this project has already paid for once
(the TTS cache-key/provider incident): two derived representations of one
source of truth silently drifting apart. Here the representations are the
manifest, the on-disk SVGs, the upsert migrations, and the two places that
reference symbol ids without any FK protection at all
(board_templates.cards jsonb, calming/memory.js's POOL).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mulberry_manifest as mm  # noqa: E402

SYMBOL_DIR = ROOT / "frontend" / "assets" / "symbols"
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"
MEMORY_JS = ROOT / "frontend" / "js" / "modules" / "calming" / "memory.js"
BOARD_TEMPLATES_SQL = ROOT / "supabase" / "migrations" / "0005_reference_data.sql"

# Explicit-content Mulberry filenames (rated=1) — must never appear as a
# shipped symbol id under any circumstances, regardless of how the manifest
# or ingester change in the future.
_EXPLICIT_STEMS = {"chest_female", "chest_male", "female_body", "male_body", "penis", "vagina"}


def _manifest() -> dict:
    return mm.load_manifest()


def _shipped_ids() -> set[str]:
    return {p.stem for p in SYMBOL_DIR.glob("*.svg")}


def _migration_ids() -> set[str]:
    ids = set()
    pattern = re.compile(r"^\s*\('([a-z0-9-]+)',")
    for p in MIGRATIONS_DIR.glob("*mulberry_symbols*.sql"):
        for line in p.read_text(encoding="utf-8").splitlines():
            m = pattern.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def test_all_36_original_ids_still_shipped():
    shipped = _shipped_ids()
    missing = set(mm.LOCKED) - shipped
    assert not missing, f"locked ids missing an on-disk SVG: {missing}"


def test_every_approved_manifest_row_has_an_svg():
    manifest = _manifest()
    shipped = _shipped_ids()
    for sid, e in manifest["entries"].items():
        if e["status"] not in ("approved", "edited"):
            continue
        assert e["id"] in shipped, f"{sid} ({e['id']}) is {e['status']} but has no on-disk SVG"


def test_migration_rows_match_manifest_locked_state():
    manifest = _manifest()
    migration_ids = _migration_ids()
    locked_decided = {
        e["id"]
        for e in manifest["entries"].values()
        if e.get("locked") and e["status"] in ("approved", "edited")
    }
    missing = locked_decided - migration_ids
    assert not missing, f"locked+decided ids never written to a migration: {missing}"


def test_no_orphan_svgs_outside_the_manifest():
    """Every shipped .svg must be traceable to either a locked id (the
    original 36, some kept as this project's own placeholder) or an
    approved/edited manifest row — never a leftover from a stale run."""
    manifest = _manifest()
    known = set(mm.LOCKED) | {
        e["id"] for e in manifest["entries"].values() if e["status"] in ("approved", "edited")
    }
    shipped = _shipped_ids()
    orphans = shipped - known
    assert not orphans, f"on-disk SVGs with no manifest/LOCKED backing: {orphans}"


def test_board_template_symbol_ids_resolve():
    text = BOARD_TEMPLATES_SQL.read_text(encoding="utf-8")
    ids = set(re.findall(r'"symbol_id"\s*:\s*"([^"]+)"', text))
    assert ids, "expected to find symbol_id references in the starter board templates"
    shipped = _shipped_ids()
    missing = ids - shipped
    assert not missing, f"board_templates.cards references ids with no on-disk SVG: {missing}"


def test_memory_pool_symbol_ids_resolve():
    text = MEMORY_JS.read_text(encoding="utf-8")
    m = re.search(r"const POOL\s*=\s*\[(.*?)\]", text, re.S)
    assert m, "could not find calming/memory.js's POOL array"
    ids = set(re.findall(r'"([a-z0-9-]+)"', m.group(1)))
    assert ids, "POOL parsed empty"
    shipped = _shipped_ids()
    missing = ids - shipped
    assert not missing, f"calming/memory.js's POOL references ids with no on-disk SVG: {missing}"


def test_no_rated_or_excluded_category_symbols_shipped():
    manifest = _manifest()
    shipped_srcs = {
        e["src"]
        for e in manifest["entries"].values()
        if e["status"] in ("approved", "edited") and e["src"]
    }
    leaked = shipped_srcs & _EXPLICIT_STEMS
    assert not leaked, f"explicit-content Mulberry files were shipped: {leaked}"

    excluded_in_manifest = {
        sid
        for sid, e in manifest["entries"].items()
        if e["status"] == "rejected" and e.get("note", "").startswith("excluded category")
    }
    assert excluded_in_manifest, "expected Country Flags/Maps to be pre-rejected in the manifest"
    shipped = _shipped_ids()
    for sid in excluded_in_manifest:
        e = manifest["entries"][sid]
        assert e["id"] not in shipped or e["id"] in mm.LOCKED, (
            f"a rejected/excluded row's id somehow shipped: {e['id']}"
        )


def test_manifest_json_is_well_formed_and_matches_schema_version():
    raw = json.loads(mm.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    assert raw["schema"] == mm.SCHEMA_VERSION
    assert raw["mulberry_version"] == mm.MULBERRY_VERSION
