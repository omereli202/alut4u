#!/usr/bin/env python3
"""Ingest the bundled PCS / Boardmaker symbol deck into the `symbols` library.

    python scripts/build_pcs_symbols.py                     # dry-run report
    python scripts/build_pcs_symbols.py --apply             # write for real
    python scripts/build_pcs_symbols.py --contact-sheet OUT.html   # core-id review

Source is a PowerPoint export (`--source`, default
`~/Downloads/סמלים בורד מייקר כל הסמלים בעולם כמעט (2) (1).pptx`) whose 465
slides each hold a 4×3 grid of picture + Hebrew caption. The archive is read
in memory and NEVER extracted to disk — same contract as build_symbols.py.

  LICENCE: this artwork is PCS (Picture Communication Symbols, Mayer-Johnson /
  Tobii Dynavox) and is PROPRIETARY. It is bundled for `dev` only. The
  generated migration is named `*_pcs_symbols.sql`; scripts/release.sh refuses
  to apply it against the production environment. Do not promote any of this
  to `main` without a Boardmaker licence. See
  frontend/assets/symbols/pcs/LICENSE.md.

What it does (with --apply):

  - parses every `ppt/slides/slideN.xml` + its `.rels`, pairs each `<p:pic>`
    with the nearest caption `<p:sp>` below it (RTL grid: right column first)
  - assigns a FROZEN id `pcs-0001`… in deck order, persisted in
    `scripts/data/pcs_manifest.json` and keyed by the media file's sha1 so a
    re-run never reshuffles existing ids
  - flood-fills the opaque white background of each PNG to transparent (AAC
    cards render inside a colour-tinted circle — a white box looks broken)
  - writes `frontend/assets/symbols/pcs/<id>.png`
  - for the 36 locked core ids (eat, yes, mom…) that have an exact
    Hebrew-label match in the deck, re-skins `frontend/assets/symbols/<id>.svg`
    in place as a thin SVG wrapper around the PCS raster — the id and its
    `<id>.svg` file_path are untouched (every frontend render site depends on
    that; see ui.js's symbolUrl() and docs/schema.md), only the picture and
    the licence/source columns change. Recorded under `core_overrides`.
  - emits an additive migration `supabase/migrations/00NN_pcs_symbols.sql`

After --apply, by hand (as with build_symbols.py):
  - bump SYMBOLS_VERSION in frontend/js/ui.js and SHELL_CACHE in frontend/sw.js
  - apply the migration: `supabase migration up --local` (or, once a cloud DEV
    project exists, `supabase db push` to it — NEVER production; release.sh
    blocks that anyway)
  - `cd backend && ../.conda/bin/pytest tests/test_symbol_consistency.py`
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mulberry_manifest as mm  # for LOCKED (the 36 core ids + their labels)

ROOT = Path(__file__).resolve().parent.parent
SYMBOL_DIR = ROOT / "frontend" / "assets" / "symbols"
PCS_DIR = SYMBOL_DIR / "pcs"
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"
MANIFEST_PATH = ROOT / "scripts" / "data" / "pcs_manifest.json"
DEFAULT_SOURCE = (
    Path.home() / "Downloads" / "סמלים בורד מייקר כל הסמלים בעולם כמעט (2) (1).pptx"
)

SCHEMA_VERSION = 1
SYMBOL_SOURCE = "Boardmaker PCS (Mayer-Johnson / Tobii Dynavox)"
SYMBOL_LICENCE = "proprietary (PCS / Boardmaker) — dev only"

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS = {"a": _A, "p": _P}

# Caption sits below its picture; allow this much slack past the picture's
# bottom edge before giving up. Column match: nearest text box in x.
_CAPTION_SLACK_EMU = 900_000
_COLUMN_TOLERANCE_EMU = 1_200_000
# Two <p:pic> for the same media within this box count as one PowerPoint
# duplicate (some slides carry an accidental overlapping copy).
_DEDUPE_EMU = 500_000

_FLOODFILL_THRESH = 40  # near-white tolerance; pale garments/plates survive

LICENSE_MD = f"""# PCS / Boardmaker symbol set — bundled for `dev` only

The PNGs in this folder are **Picture Communication Symbols (PCS)**, authored by
Mayer-Johnson and distributed with Boardmaker (now Tobii Dynavox). They were
imported from a PowerPoint export supplied by the project owner
(`scripts/build_pcs_symbols.py`).

**PCS is proprietary. This set is NOT open-licensed** (unlike the Mulberry
Symbols at the parent folder, which are CC BY-SA 4.0).

It is bundled here to unblock design and testing on the `dev` environment. It
**must not be deployed to production / `main`** without a Boardmaker content
licence from Tobii Dynavox.

Enforcement:
- the DB rows carry `licence = '{SYMBOL_LICENCE}'`, `source = '{SYMBOL_SOURCE}'`
- the migration is named `*_pcs_symbols.sql`
- `scripts/release.sh` aborts the release if that migration is present and the
  target is the production environment

To remove the set entirely: delete this folder, delete
`supabase/migrations/*_pcs_symbols.sql` and `scripts/data/pcs_manifest.json`,
and revert the `core_overrides` re-skin of the 36 `*.svg` files (re-run
`scripts/build_symbols.py --apply`).
"""


# --------------------------------------------------------------------------- #
# 1. Parse the deck
# --------------------------------------------------------------------------- #


@dataclass
class Cell:
    media: str  # 'image123.png'
    label_he: str  # primary caption (first synonym)
    keywords_he: list[str]  # every synonym seen for this media, ordered union
    slide: int
    row: int  # 0..2, top to bottom
    col: int  # 0-based from the RIGHT (RTL reading order)


def _slide_num(name: str) -> int:
    return int(re.search(r"slide(\d+)\.xml", name).group(1))


def _split_synonyms(caption: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,،]", caption.replace("\n", " ")):
        p = re.sub(r"\s+", " ", part).strip()
        if p and p not in out:
            out.append(p)
    return out


def _parse_slide(
    zf: zipfile.ZipFile, slide_name: str
) -> list[tuple[str, str, int, int, int]]:
    """Return (media, caption, slide, row, col_from_right) per grid cell."""
    root = ET.fromstring(zf.read(slide_name))
    tree = root.find(".//p:cSld/p:spTree", _NS)
    rels = ET.fromstring(
        zf.read(re.sub(r"slides/(.*)$", r"slides/_rels/\1.rels", slide_name))
    )
    rmap = {c.get("Id"): c.get("Target") for c in rels}

    pics: list[tuple[int, int, int, str]] = []  # x, y, cy, media
    seen: set[tuple[str, int, int]] = set()
    for pic in tree.findall("p:pic", _NS):
        off = pic.find(".//a:off", _NS)
        ext = pic.find(".//a:ext", _NS)
        blip = pic.find(".//a:blip", _NS)
        if off is None or ext is None or blip is None:
            continue
        media = (rmap.get(blip.get(f"{{{_R}}}embed"), "") or "").split("/")[-1]
        if not media:
            continue
        x, y, cy = int(off.get("x")), int(off.get("y")), int(ext.get("cy"))
        key = (media, round(x / _DEDUPE_EMU), round(y / _DEDUPE_EMU))
        if key in seen:
            continue
        seen.add(key)
        pics.append((x, y, cy, media))

    texts: list[tuple[int, int, str]] = []  # x, y, caption
    for sp in tree.findall("p:sp", _NS):
        off = sp.find(".//a:off", _NS)
        txt = "".join(t.text or "" for t in sp.findall(".//a:t", _NS)).strip()
        if txt and off is not None:
            texts.append((int(off.get("x")), int(off.get("y")), txt))

    slide = _slide_num(slide_name)
    xs_desc = sorted({x for x, _, _, _ in pics}, reverse=True)  # right -> left
    ys_asc = sorted({y for _, y, _, _ in pics})
    rows: list[int] = []
    for y in ys_asc:
        if rows and y - rows[-1] < 1_000_000:
            continue
        rows.append(y)

    def row_of(y: int) -> int:
        return min(range(len(rows)), key=lambda i: abs(rows[i] - y))

    def col_of(x: int) -> int:
        return min(range(len(xs_desc)), key=lambda i: abs(xs_desc[i] - x))

    used: set[int] = set()
    out: list[tuple[str, str, int, int, int]] = []
    for x, y, cy, media in sorted(pics, key=lambda p: (p[1], -p[0])):
        cands = sorted(
            (abs(tx - x), i)
            for i, (tx, ty, _t) in enumerate(texts)
            if ty > y
            and ty < y + cy + _CAPTION_SLACK_EMU
            and i not in used
            and abs(tx - x) < _COLUMN_TOLERANCE_EMU
        )
        caption = ""
        if cands:
            i = cands[0][1]
            used.add(i)
            caption = texts[i][2]
        out.append((media, caption, slide, row_of(y), col_of(x)))
    return out


def parse_deck(source: Path) -> tuple[dict[str, Cell], list[str], int]:
    """media -> Cell (first slide occurrence wins the id; captions merge).
    Also returns the list of unlabelled media and the raw pair count."""
    cells: dict[str, Cell] = {}
    unlabelled: list[str] = []
    pairs = 0
    with zipfile.ZipFile(source) as zf:
        slide_names = sorted(
            (n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=_slide_num,
        )
        for name in slide_names:
            for media, caption, slide, row, col in _parse_slide(zf, name):
                syn = _split_synonyms(caption)
                if syn:
                    pairs += 1
                if media in cells:
                    for k in syn:
                        if k not in cells[media].keywords_he:
                            cells[media].keywords_he.append(k)
                    continue
                if not syn:
                    if media not in unlabelled:
                        unlabelled.append(media)
                    continue
                cells[media] = Cell(media, syn[0], list(syn), slide, row, col)
    # a media that only ever appeared unlabelled AND never labelled: real gap
    unlabelled = [m for m in unlabelled if m not in cells]
    return cells, unlabelled, pairs


# --------------------------------------------------------------------------- #
# 2. Image processing — white background -> transparent
# --------------------------------------------------------------------------- #


def make_transparent(png_bytes: bytes) -> bytes:
    """Flood-fill the border-connected white background to alpha 0, keeping
    interior whites (eyes, plates, shirts). Verified on the deck: a border
    flood-fill clears ~63% of pixels; a naive white->alpha colour key would
    punch holes in ~half the images."""
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    w, h = im.size
    canvas = Image.new("RGB", (w + 2, h + 2), (255, 255, 255))
    canvas.paste(im, (1, 1))

    filled = canvas.copy()
    ImageDraw.floodfill(filled, (0, 0), (255, 0, 255), thresh=_FLOODFILL_THRESH)
    # pixels floodfill changed == background (incl. the anti-alias halo)
    changed = ImageChops.difference(filled, canvas).convert("L")
    mask = changed.point(lambda v: 0 if v else 255)  # 0 = transparent, 255 = keep

    rgba = canvas.convert("RGBA")
    rgba.putalpha(mask)
    out = rgba.crop((1, 1, w + 1, h + 1))

    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _svg_wrapper(png_bytes: bytes, *, label_he: str, pcs_id: str) -> str:
    im = Image.open(io.BytesIO(png_bytes))
    w, h = im.size
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{label_he}">'
        f"<!-- PCS-WRAPPER {pcs_id} — proprietary PCS raster, dev only; "
        f"see scripts/build_pcs_symbols.py -->"
        f'<image width="{w}" height="{h}" href="data:image/png;base64,{b64}"/>'
        "</svg>\n"
    )


# --------------------------------------------------------------------------- #
# 3. Id assignment (frozen via the manifest)
# --------------------------------------------------------------------------- #


def _sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "schema": SCHEMA_VERSION,
        "source": SYMBOL_SOURCE,
        "licence": SYMBOL_LICENCE,
        "note": "dev only — see frontend/assets/symbols/pcs/LICENSE.md",
        "entries": {},
        "core_overrides": {},
        "core_picks": {},
    }


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# 4. Migration SQL
# --------------------------------------------------------------------------- #


def _sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _sql_text_array(items: list[str]) -> str:
    inner = ",".join(
        '"' + i.replace("\\", "\\\\").replace('"', '\\"') + '"' for i in items
    )
    # the whole {...} payload is one SQL string literal — an ASCII apostrophe
    # inside a keyword (e.g. "גבינת צ'דר") must be doubled or it terminates it.
    return "'" + ("{" + inner + "}").replace("'", "''") + "'"


def _next_migration_number() -> int:
    nums = [int(p.name[:4]) for p in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")]
    return (max(nums) + 1) if nums else 1


def build_migration(entries: dict, core_overrides: dict) -> tuple[Path, str]:
    rows_sql = []
    for pcs_id in sorted(entries):
        e = entries[pcs_id]
        rows_sql.append(
            f"  ({_sql_str(pcs_id)}, {_sql_str(e['file_path'])}, {_sql_str(e['label_he'])}, "
            f"{_sql_text_array(e['keywords_he'])}, {_sql_str(SYMBOL_LICENCE)}, {_sql_str(SYMBOL_SOURCE)})"
        )
    # reuse the existing pcs migration if there is one (re-runs regenerate it
    # in place); otherwise claim the next free number.
    existing = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_pcs_symbols.sql"))
    path = (
        existing[0]
        if existing
        else MIGRATIONS_DIR / f"{_next_migration_number():04d}_pcs_symbols.sql"
    )
    body = [
        "-- PCS / Boardmaker pictogram library (Mayer-Johnson / Tobii Dynavox).",
        "-- PROPRIETARY — bundled for the `dev` environment only. scripts/release.sh",
        "-- refuses to apply this file against production. Do not promote to `main`",
        "-- without a Boardmaker content licence. See",
        "-- frontend/assets/symbols/pcs/LICENSE.md.",
        "-- Generated by scripts/build_pcs_symbols.py from scripts/data/pcs_manifest.json.",
        "-- Do not edit by hand — re-run the script instead.",
        "insert into symbols (id, file_path, label_he, keywords_he, licence, source) values",
        ",\n".join(rows_sql),
        "on conflict (id) do update set",
        "  file_path = excluded.file_path, label_he = excluded.label_he,",
        "  keywords_he = excluded.keywords_he, licence = excluded.licence,",
        "  source = excluded.source;",
        "",
    ]
    if core_overrides:
        body.append(
            "-- Core-vocabulary ids re-skinned with PCS art. id and file_path (<id>.svg)"
        )
        body.append("-- are unchanged — only the picture and provenance columns move.")
        for core_id in sorted(core_overrides):
            body.append(
                f"update symbols set licence = {_sql_str(SYMBOL_LICENCE)}, "
                f"source = {_sql_str(SYMBOL_SOURCE)} where id = {_sql_str(core_id)};"
            )
        body.append("")
    return path, "\n".join(body)


# --------------------------------------------------------------------------- #
# 5. Core-id matching (the 36 locked ids -> a PCS cell)
# --------------------------------------------------------------------------- #


def match_core_ids(
    cells: dict[str, Cell], picks: dict[str, str] | None = None
) -> dict[str, dict]:
    """locked id -> {media, candidates:[media...]} for every locked id whose
    Hebrew label matches a PCS caption.

    Candidates are ranked so the auto-pick avoids Hebrew homonyms: a cell
    whose headword caption is exactly the core word (ספר = "book") outranks one
    that only carries it as a secondary synonym (ספר, מספרה = "barber"), which
    outranks a match on one of the core's *other* keywords; a tighter caption
    (fewer synonyms) breaks ties, then deck order. `picks` (core_id -> media
    filename, from the hand-editable `core_picks` in the manifest) pins it."""
    picks = picks or {}
    ordered = sorted(cells.values(), key=lambda c: (c.slide, c.row, c.col))

    out: dict[str, dict] = {}
    for core_id, meta in mm.LOCKED.items():
        primary = meta["label_he"]
        others = [k for k in meta["keywords_he"] if k != primary]
        scored: list[tuple[tuple, str]] = []
        for i, c in enumerate(ordered):
            if primary == c.label_he:
                tier = 0  # deck caption's headword is exactly the core word
            elif primary in c.keywords_he:
                tier = 1  # core word is a secondary synonym in this cell
            elif any(k == c.label_he for k in others):
                tier = 2  # a core *keyword* is the cell's headword
            elif any(k in c.keywords_he for k in others):
                tier = 3
            else:
                continue
            scored.append(((tier, len(c.keywords_he), i), c.media))
        if not scored:
            continue
        scored.sort()
        cands = [m for _s, m in scored]
        chosen = picks.get(core_id)
        if chosen and chosen in cands:
            cands = [chosen] + [m for m in cands if m != chosen]
        out[core_id] = {"media": cands[0], "candidates": cands}
    return out


# --------------------------------------------------------------------------- #
# 6. Driver
# --------------------------------------------------------------------------- #


@dataclass
class Report:
    dry_run: bool = True
    total_media: int = 0
    ingested: int = 0
    new_ids: int = 0
    reused_ids: int = 0
    unlabelled: list[str] = field(default_factory=list)
    pairs: int = 0
    core_overrides: dict = field(default_factory=dict)
    migration_path: Path | None = None


def run(*, source: Path, dry_run: bool = True) -> Report:
    cells, unlabelled, pairs = parse_deck(source)
    manifest = load_manifest()
    known = manifest["entries"]

    sha1_to_id = {e["sha1"]: pid for pid, e in known.items()}
    used_nums = sorted(int(pid.split("-")[1]) for pid in known)
    next_num = (used_nums[-1] + 1) if used_nums else 1

    rep = Report(
        dry_run=dry_run, total_media=len(cells), unlabelled=unlabelled, pairs=pairs
    )
    new_entries: dict[str, dict] = {}
    png_cache: dict[str, bytes] = {}

    ordered = sorted(cells.values(), key=lambda c: (c.slide, c.row, c.col))
    with zipfile.ZipFile(source) as zf:
        for c in ordered:
            raw = zf.read(f"ppt/media/{c.media}")
            src_sha1 = _sha1(raw)
            pcs_id = sha1_to_id.get(src_sha1)
            if pcs_id is None:
                pcs_id = f"pcs-{next_num:04d}"
                next_num += 1
                rep.new_ids += 1
            else:
                rep.reused_ids += 1
            png = make_transparent(raw)
            png_cache[pcs_id] = png
            new_entries[pcs_id] = {
                "media": c.media,
                "sha1": src_sha1,
                "file_path": f"pcs/{pcs_id}.png",
                "label_he": c.label_he,
                "keywords_he": c.keywords_he,
                "slide": c.slide,
                "cell": [c.row, c.col],
            }
            rep.ingested += 1

        core = match_core_ids(cells, manifest.get("core_picks"))
        media_to_pcs = {e["media"]: pid for pid, e in new_entries.items()}
        core_overrides = {
            cid: media_to_pcs[info["media"]]
            for cid, info in core.items()
            if info["media"] in media_to_pcs
        }
        rep.core_overrides = {
            cid: {
                "pcs_id": media_to_pcs.get(info["media"]),
                "candidates": info["candidates"],
            }
            for cid, info in core.items()
        }

        if not dry_run:
            PCS_DIR.mkdir(parents=True, exist_ok=True)
            for pcs_id, png in png_cache.items():
                (PCS_DIR / f"{pcs_id}.png").write_bytes(png)
            (PCS_DIR / "LICENSE.md").write_text(LICENSE_MD, encoding="utf-8")

            for core_id, pcs_id in core_overrides.items():
                svg = _svg_wrapper(
                    png_cache[pcs_id],
                    label_he=mm.LOCKED[core_id]["label_he"],
                    pcs_id=pcs_id,
                )
                (SYMBOL_DIR / f"{core_id}.svg").write_text(svg, encoding="utf-8")

            manifest["entries"] = new_entries
            manifest["core_overrides"] = core_overrides
            # a hand-editable record of the resolved art choice per core id —
            # change a value here (to any of its `candidates` media names, see
            # the contact sheet) and re-run --apply to swap that one symbol.
            manifest["core_picks"] = {cid: info["media"] for cid, info in core.items()}
            manifest["count"] = len(new_entries)
            save_manifest(manifest)

        path, sql = build_migration(new_entries, core_overrides)
        rep.migration_path = path
        if not dry_run:
            path.write_text(sql, encoding="utf-8")

    return rep


def _contact_sheet(source: Path, out: Path) -> None:
    cells, _unl, _pairs = parse_deck(source)
    picks = load_manifest().get("core_picks")
    core = match_core_ids(cells, picks)
    with zipfile.ZipFile(source) as zf:
        rows = []
        for core_id, meta in mm.LOCKED.items():
            info = core.get(core_id)
            thumbs = ""
            if info:
                for i, media in enumerate(info["candidates"][:12]):
                    png = make_transparent(zf.read(f"ppt/media/{media}"))
                    b64 = base64.b64encode(png).decode("ascii")
                    chosen = media == info["media"]
                    border = "#2a7" if chosen else "#ccc"
                    thumbs += (
                        f'<figure style="display:inline-block;margin:2px;text-align:center">'
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="width:72px;height:72px;object-fit:contain;border:3px solid {border};'
                        f'border-radius:8px;background:#f4f4f4">'
                        f'<figcaption style="font-size:10px;color:#999">{media}</figcaption>'
                        f"</figure>"
                    )
            else:
                thumbs = (
                    '<span style="color:#c33">— no PCS match — keeps current SVG</span>'
                )
            rows.append(
                f'<tr><td style="font-weight:700">{meta["label_he"]}<br>'
                f'<code style="color:#888">{core_id}</code></td><td>{thumbs}</td></tr>'
            )
    out.write_text(
        '<!doctype html><meta charset="utf-8"><title>PCS core-id review</title>'
        '<body style="font-family:system-ui;direction:rtl;padding:24px">'
        "<h1>36 core ids → PCS art</h1>"
        "<p>הריבוע הירוק = הבחירה. מתחת לכל תמונה שם קובץ המקור. "
        "כדי להחליף בחירה: הוסיפו/עדכנו שורה ב-<code>core_picks</code> "
        "ב-<code>scripts/data/pcs_manifest.json</code> "
        '(למשל <code>"ball": "image1638.png"</code>) והריצו <code>--apply</code> מחדש.</p>'
        '<table style="border-collapse:collapse" border="1" cellpadding="8">'
        f"{''.join(rows)}</table></body>",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--apply", action="store_true", help="write changes (default: dry run)"
    )
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument(
        "--contact-sheet", type=Path, help="write a core-id review HTML and exit"
    )
    args = ap.parse_args()

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 2

    if args.contact_sheet:
        _contact_sheet(args.source, args.contact_sheet)
        print(f"wrote {args.contact_sheet}")
        return 0

    rep = run(source=args.source, dry_run=not args.apply)
    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"[{mode}] PCS symbol ingestion")
    print(f"  distinct media (grid cells) : {rep.total_media}")
    print(
        f"  ingested rows               : {rep.ingested}  (new {rep.new_ids}, reused {rep.reused_ids})"
    )
    print(f"  image/label pairs in deck   : {rep.pairs}")
    print(f"  unlabelled media (skipped)  : {len(rep.unlabelled)}  {rep.unlabelled}")
    print(f"  core-id overrides           : {len(rep.core_overrides)} matched")
    for cid, info in sorted(rep.core_overrides.items()):
        print(
            f"      {cid:11s} -> {info['pcs_id']}   ({len(info['candidates'])} candidate(s))"
        )
    missing = sorted(set(mm.LOCKED) - set(rep.core_overrides))
    print(f"  core ids with NO match      : {missing}")
    if rep.migration_path:
        print(
            f"  migration: {rep.migration_path.name} "
            f"{'(written)' if args.apply else '(dry run — not written)'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
