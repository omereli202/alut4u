"""The curated colouring-page shortlist must stay valid.

Pure filesystem — runs in every CI job. Guards the failure mode where a future
symbol regeneration (build_symbols.py) silently empties the painting gallery,
or a curated id stops being colourable.

"Colourable" here uses the same resolved-style classifier the frontend
(js/modules/painting/pages.js) uses: an OUTLINE has a resolved stroke != none
(or no fill at all); a REGION has no stroke and a real colour fill. A page
needs >= 1 outline and >= 2 regions and no <text>/<image>.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SYMBOL_DIR = ROOT / "frontend" / "assets" / "symbols"
PAGES_JS = ROOT / "frontend" / "js" / "modules" / "painting" / "pages.js"
SW_JS = ROOT / "frontend" / "sw.js"
UI_JS = ROOT / "frontend" / "js" / "ui.js"

_NS = "{http://www.w3.org/2000/svg}"
_SHAPES = {"path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}


def _curated() -> list[str]:
    m = re.search(r"export const CURATED = \[(.*?)\]", PAGES_JS.read_text(), re.S)
    assert m, "could not find CURATED in pages.js"
    return re.findall(r'"([a-z0-9-]+)"', m.group(1))


def _classify(path: Path) -> tuple[int, int, bool]:
    root = ET.parse(path).getroot()
    css: dict[str, dict] = {}
    for style in root.iter(_NS + "style"):
        for rule in re.finditer(r"\.([A-Za-z0-9_-]+)\s*\{([^}]*)\}", style.text or ""):
            decl = {}
            for kv in rule.group(2).split(";"):
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    decl[k.strip()] = v.strip()
            css[rule.group(1)] = decl
    has_text = root.find(f".//{_NS}text") is not None or root.find(f".//{_NS}image") is not None

    outlines = regions = 0

    def walk(el: ET.Element, inherited: dict) -> None:
        nonlocal outlines, regions
        cur = dict(inherited)
        for c in (el.get("class") or "").split():
            cur.update(css.get(c, {}))
        for k in ("fill", "stroke"):
            if el.get(k) is not None:
                cur[k] = el.get(k)
        for kv in (el.get("style") or "").split(";"):
            if ":" in kv:
                a, b = kv.split(":", 1)
                cur[a.strip()] = b.strip()
        tag = el.tag.replace(_NS, "")
        if tag in _SHAPES:
            stroke = (cur.get("stroke") or "none").lower()
            fill = cur.get("fill")
            if stroke and stroke != "none":
                outlines += 1
            elif fill and fill.lower() != "none":
                regions += 1
            elif fill is None:
                outlines += 1
        for child in el:
            walk(child, cur)

    walk(root, {})
    return outlines, regions, has_text


def test_curated_ids_exist_and_are_colourable():
    bad = []
    for sid in _curated():
        f = SYMBOL_DIR / f"{sid}.svg"
        if not f.exists():
            bad.append(f"{sid}: missing")
            continue
        outlines, regions, has_text = _classify(f)
        if has_text or outlines < 1 or regions < 2:
            bad.append(f"{sid}: outlines={outlines} regions={regions} text/image={has_text}")
    assert not bad, "curated colouring pages no longer valid:\n" + "\n".join(bad)


def test_sw_paint_pages_match_curated_and_symbol_version():
    curated = set(_curated())
    sw = SW_JS.read_text()
    m = re.search(r"const PAINT_PAGES = \[(.*?)\]", sw, re.S)
    assert m, "PAINT_PAGES not found in sw.js"
    sw_ids = set(re.findall(r'"([a-z0-9-]+)"', m.group(1)))
    assert sw_ids == curated, f"sw.js PAINT_PAGES drift: {sw_ids ^ curated}"

    sw_v = re.search(r'SYMBOLS_ASSET_V = "([^"]+)"', sw).group(1)
    ui_v = re.search(r'SYMBOLS_VERSION = "([^"]+)"', UI_JS.read_text()).group(1)
    assert sw_v == ui_v, f"sw.js SYMBOLS_ASSET_V ({sw_v}) != ui.js SYMBOLS_VERSION ({ui_v})"
