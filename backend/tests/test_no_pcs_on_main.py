"""MAIN-ONLY guard — must never exist on `dev`.

`dev` bundles the proprietary PCS / Boardmaker symbol set for internal use;
`main` (→ production) must not carry a byte of it. The dev→main promotion runs
a strip commit (see supabase/migrations/0029_mainonly_mulberry_symbols_no_pcs.sql)
and this test is what keeps the strip honest on every future promotion — CI on
`main` fails loudly if any PCS artefact creeps back.

If a promotion merge re-introduces PCS, delete the offending paths and
regenerate the strip; do not weaken this test.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_pcs_symbol_assets():
    pcs_dir = ROOT / "frontend" / "assets" / "symbols" / "pcs"
    assert not pcs_dir.exists(), f"proprietary PCS art is present at {pcs_dir}"


def test_no_pcs_migration():
    hits = list((ROOT / "supabase" / "migrations").glob("*_pcs_symbols.sql"))
    assert not hits, f"PCS seed migration present on main: {hits}"


def test_no_pcs_manifest_or_builder():
    for p in (
        ROOT / "scripts" / "data" / "pcs_manifest.json",
        ROOT / "scripts" / "build_pcs_symbols.py",
    ):
        assert not p.exists(), f"PCS tooling present on main: {p}"


def test_no_pcs_wrapped_core_svgs():
    """The 34 core ids re-skinned in place over PCS raster on dev must be back
    to Mulberry line art here."""
    sym = ROOT / "frontend" / "assets" / "symbols"
    offenders = [p.name for p in sym.glob("*.svg") if "PCS-WRAPPER" in p.read_text(encoding="utf-8")]
    assert not offenders, f"SVGs still wrapping PCS raster: {offenders}"


def test_no_pcs_id_arm_in_symbol_url():
    ui = (ROOT / "frontend" / "js" / "ui.js").read_text(encoding="utf-8")
    # the comment mentioning pcs- is fine; an actual code path is not
    assert 'startsWith("pcs-")' not in ui, "symbolUrl() still has the pcs- id arm"
