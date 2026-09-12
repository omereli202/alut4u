"""Cross-representation consistency for the bundled symbol sets.

Pure filesystem + text parsing — no Supabase needed, so this runs in every CI
job. Guards the exact failure mode this project has already paid for once
(the TTS cache-key/provider incident): two derived representations of one
source of truth silently drifting apart. Here the representations are the
manifest(s), the on-disk artwork, the upsert migrations, and the two places
that reference symbol ids without any FK protection at all
(board_templates.cards jsonb, calming/memory.js's POOL).

Two sets:
  - Mulberry Symbols (CC BY-SA 4.0) — scripts/mulberry_manifest.py + *.svg
  - PCS / Boardmaker (proprietary, DEV ONLY) — scripts/build_pcs_symbols.py +
    pcs/*.png + scripts/data/pcs_manifest.json. Its tests skip when the set
    isn't present (it's removable per pcs/LICENSE.md).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mulberry_manifest as mm  # noqa: E402

SYMBOL_DIR = ROOT / "frontend" / "assets" / "symbols"
PCS_DIR = SYMBOL_DIR / "pcs"
PCS_MANIFEST = ROOT / "scripts" / "data" / "pcs_manifest.json"
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"
MEMORY_JS = ROOT / "frontend" / "js" / "modules" / "calming" / "memory.js"
VECTOR_DIR = ROOT / "backend" / "app" / "data" / "symbol_vectors"
VECTOR_META = VECTOR_DIR / "meta.json"


def _board_templates_sql() -> str:
    """Every migration that inserts/updates board_templates rows, concatenated
    in filename (= applied) order. board_templates.spec has no FK on
    symbol_id, and templates are seeded via a chain of migrations (0005's
    original seed, 0021's nested-branch update, 0030's rewrite, ...) rather
    than one file — checking only 0005 would silently stop covering the
    starter boards a real child actually gets the moment a later migration
    replaces their content."""
    texts = [
        p.read_text(encoding="utf-8")
        for p in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if "board_templates" in p.read_text(encoding="utf-8")
    ]
    assert texts, "expected at least one migration touching board_templates"
    return "\n".join(texts)


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


_vectors_skip = pytest.mark.skipif(
    not VECTOR_META.exists(),
    reason="symbol vectors not generated — run scripts/build_symbol_vectors.py --apply",
)


@_vectors_skip
def test_every_approved_manifest_row_has_a_vector():
    """After every `build_symbols.py --apply`, re-run
    `scripts/build_symbol_vectors.py --apply` — same drift class as the SVG
    guard above. A missing vector only degrades that symbol to lexical-only
    search, but a red build makes the omission visible."""
    ids = set(json.loads(VECTOR_META.read_text("utf-8"))["ids"])
    manifest = _manifest()
    missing = {
        e["id"]
        for e in manifest["entries"].values()
        if e["status"] in ("approved", "edited") and e["id"] not in ids
    }
    assert not missing, (
        f"{len(missing)} approved symbols have no vector — re-run "
        f"scripts/build_symbol_vectors.py --apply: {sorted(missing)[:10]}"
    )


@_vectors_skip
def test_no_orphan_vectors():
    ids = set(json.loads(VECTOR_META.read_text("utf-8"))["ids"])
    approved = {
        e["id"] for e in _manifest()["entries"].values() if e["status"] in ("approved", "edited")
    }
    assert not (ids - approved), f"vectors for non-approved ids: {sorted(ids - approved)[:10]}"


@_vectors_skip
def test_vector_files_are_internally_consistent():
    """meta ids == symbols rows == meta dim cols; words.txt lines == words rows.
    Catches a half-finished build_symbol_vectors.py run."""
    import numpy as np

    meta = json.loads(VECTOR_META.read_text("utf-8"))
    n, d = len(meta["ids"]), meta["dim"]
    assert len(meta["mean"]) == d and len(meta["pc"]) == d
    syms = np.load(VECTOR_DIR / "symbols.f16.npy", allow_pickle=False)
    assert syms.shape == (n, d), syms.shape
    words = np.load(VECTOR_DIR / "words.f16.npy", allow_pickle=False)
    keys = (VECTOR_DIR / "words.txt").read_text("utf-8").split("\n")
    assert words.shape == (len(keys), d), (words.shape, len(keys))


@_vectors_skip
def test_label_roundtrip_accuracy():
    """Each symbol's own label, embedded and cosine-ranked against the semantic
    band alone, should retrieve that symbol — a free ~1,000-example eval. A
    regression here means the build/runtime pooling or post() drifted apart.
    Floors are the first real run's numbers minus a safety margin."""
    import numpy as np

    from app.services import symbol_search as ss

    ss.reset_cache()
    vecs = ss._vectors()
    assert vecs is not None
    S = vecs.symbols.astype(np.float32)
    meta = json.loads(VECTOR_META.read_text("utf-8"))
    manifest = _manifest()
    label_by_id = {
        e["id"]: e["label_he"]
        for e in manifest["entries"].values()
        if e["status"] in ("approved", "edited")
    }
    top1 = top5 = n = 0
    for i, sid in enumerate(meta["ids"]):
        qv = ss.embed(label_by_id[sid])
        if qv is None:
            continue
        n += 1
        order = np.argsort(-(S @ qv))
        top1 += int(order[0] == i)
        top5 += int(i in order[:5])
    assert n > 900
    assert top1 / n >= 0.85, f"label round-trip top-1 {top1}/{n}"
    assert top5 / n >= 0.95, f"label round-trip top-5 {top5}/{n}"


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
    text = _board_templates_sql()
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


# --------------------------------------------------------------------------- #
# PCS / Boardmaker set (proprietary, dev only) — skips when not installed.
# --------------------------------------------------------------------------- #

_PCS_ID_RE = re.compile(r"^pcs-\d{4}$")


def _pcs_manifest() -> dict:
    if not PCS_MANIFEST.exists():
        pytest.skip("PCS symbol set not installed (scripts/build_pcs_symbols.py --apply)")
    return json.loads(PCS_MANIFEST.read_text(encoding="utf-8"))


def _pcs_shipped_ids() -> set[str]:
    return {p.stem for p in PCS_DIR.glob("*.png")}


def _pcs_migration() -> Path:
    hits = list(MIGRATIONS_DIR.glob("*_pcs_symbols.sql"))
    assert len(hits) == 1, f"expected exactly one *_pcs_symbols.sql migration, found {hits}"
    return hits[0]


def test_pcs_ids_are_well_formed():
    manifest = _pcs_manifest()
    bad = [pid for pid in manifest["entries"] if not _PCS_ID_RE.match(pid)]
    assert not bad, f"PCS ids not matching pcs-NNNN: {bad[:10]}"


def test_pcs_every_manifest_row_has_a_png():
    manifest = _pcs_manifest()
    shipped = _pcs_shipped_ids()
    missing = set(manifest["entries"]) - shipped
    assert not missing, f"PCS manifest rows with no on-disk PNG: {sorted(missing)[:10]}"


def test_pcs_no_orphan_pngs():
    manifest = _pcs_manifest()
    orphans = _pcs_shipped_ids() - set(manifest["entries"])
    assert not orphans, f"pcs/*.png files with no manifest row: {sorted(orphans)[:10]}"


def test_pcs_migration_rows_match_manifest():
    manifest = _pcs_manifest()
    text = _pcs_migration().read_text(encoding="utf-8")
    migration_ids = set(re.findall(r"\('(pcs-\d{4})',", text))
    assert migration_ids == set(manifest["entries"]), (
        "PCS migration and manifest disagree on which ids exist — re-run "
        "scripts/build_pcs_symbols.py --apply"
    )


def test_pcs_file_paths_are_subfoldered_pngs():
    manifest = _pcs_manifest()
    for pid, e in manifest["entries"].items():
        assert e["file_path"] == f"pcs/{pid}.png", (pid, e["file_path"])


def test_pcs_core_overrides_are_reskinned_svg_wrappers():
    """Each re-skinned core id keeps its `<id>.svg` file_path (schema.md
    invariant) but the file is now a wrapper around the PCS raster."""
    manifest = _pcs_manifest()
    for core_id, pcs_id in manifest.get("core_overrides", {}).items():
        assert core_id in mm.LOCKED, f"core override {core_id!r} is not a locked id"
        assert _PCS_ID_RE.match(pcs_id), (core_id, pcs_id)
        svg = (SYMBOL_DIR / f"{core_id}.svg").read_text(encoding="utf-8")
        assert f"PCS-WRAPPER {pcs_id}" in svg, f"{core_id}.svg is not the PCS wrapper for {pcs_id}"


def test_pcs_set_is_flagged_proprietary_and_dev_only():
    """Guard against an accidental relicensing — this set must never be
    described as free/open, and the release guard keys off the migration name."""
    manifest = _pcs_manifest()
    blob = json.dumps(manifest, ensure_ascii=False).lower()
    assert "proprietary" in blob and "dev only" in blob
    assert (PCS_DIR / "LICENSE.md").exists()
    release = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    assert "pcs_symbols" in release, "release.sh lost its PCS production guard"


def test_pcs_board_and_memory_refs_still_resolve_against_both_sets():
    """The two FK-less id reference sites resolve against svg-on-disk ∪ PCS
    manifest ids, so a future switch of a starter card to a pcs-* id is
    covered here instead of only failing at runtime."""
    known = _shipped_ids()
    if PCS_MANIFEST.exists():
        known = known | set(json.loads(PCS_MANIFEST.read_text(encoding="utf-8"))["entries"])

    board_sql = _board_templates_sql()
    board_ids = set(re.findall(r'"symbol_id"\s*:\s*"([^"]+)"', board_sql))
    pool_match = re.search(r"const POOL\s*=\s*\[(.*?)\]", MEMORY_JS.read_text("utf-8"), re.S)
    pool_ids = set(re.findall(r'"([a-z0-9-]+)"', pool_match.group(1)))

    assert not (board_ids - known), f"board template ids unresolved: {board_ids - known}"
    assert not (pool_ids - known), f"memory POOL ids unresolved: {pool_ids - known}"
