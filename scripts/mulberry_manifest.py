"""Shared logic for the Mulberry Symbols manifest — the single source of
truth mapping Mulberry's source SVGs to this app's symbol ids and Hebrew
labels.

Both the manifest bootstrap/review tooling and `build_symbols.py` (the actual
ingester) import from here, so slug derivation is computed exactly once. Two
independent implementations of the same slug rule is the failure mode this
module exists to prevent — see the TTS cache-key/provider incident this
project already paid for once (a shared value computed in two places, one of
which forgot a field).

The manifest itself (`scripts/data/mulberry_manifest.json`) is committed —
the authored Hebrew labels are the real work product; the source SVGs are
re-derivable from the archive at any time.
"""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MULBERRY_VERSION = "3.6.1"

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ZIP = Path("/Users/omereliasaf/Downloads/mulberry-symbols.zip")
DEFAULT_MANIFEST = ROOT / "scripts" / "data" / "mulberry_manifest.json"

_CSV_NAME = "symbol-info.csv"
_SVG_DIR = "EN-symbols/"

# The 36 ids that exist today (frontend/assets/symbols/, the `symbols` table,
# board_templates.cards jsonb, calming/memory.js's POOL). Immutable forever —
# see the plan's "Why the ids can never change" section. `src` is the Mulberry
# filename stem (no .svg) this id now maps to; None means "no good Mulberry
# equivalent — keep the existing placeholder SVG untouched".
#
# label_he / keywords_he are copied verbatim from the current
# scripts/build_symbols.py SYMBOLS dict — authored once, not regenerated.
LOCKED: dict[str, dict[str, Any]] = {
    "yes": {
        "src": "correct",
        "label_he": "כן",
        "keywords_he": ["כן", "מסכים", "אישור"],
    },
    "no": {
        "src": "mistake_no_wrong",
        "label_he": "לא",
        "keywords_he": ["לא", "מסרב", "שלילה"],
    },
    "more": {
        "src": "more",
        "label_he": "עוד",
        "keywords_he": ["עוד", "עוד פעם", "להוסיף"],
    },
    "stop": {
        "src": None,
        "label_he": "מספיק",
        "keywords_he": ["מספיק", "עצור", "די", "להפסיק"],
    },
    "want": {
        "src": "want_,_to",
        "label_he": "רוצה",
        "keywords_he": ["רוצה", "אני רוצה", "בבקשה"],
    },
    "dont-want": {
        "src": None,
        "label_he": "לא רוצה",
        "keywords_he": ["לא רוצה", "לא", "מסרב"],
    },
    "i": {"src": "show_me_,_to", "label_he": "אני", "keywords_he": ["אני", "עצמי"]},
    "you": {"src": "point_,_to", "label_he": "אתה", "keywords_he": ["אתה", "את"]},
    "eat": {
        "src": "eat_,_to",
        "label_he": "לאכול",
        "keywords_he": ["לאכול", "אוכל", "רעב", "ארוחה"],
    },
    "drink": {
        "src": "drink_,_to",
        "label_he": "לשתות",
        "keywords_he": ["לשתות", "מים", "צמא", "שתייה"],
    },
    "toilet": {
        "src": "toilet_,_go_to_the",
        "label_he": "שירותים",
        "keywords_he": ["שירותים", "לשירותים", "פיפי", "קקי"],
    },
    "help": {
        "src": "help_,_to",
        "label_he": "עזרה",
        "keywords_he": ["עזרה", "עזור לי", "צריך עזרה"],
    },
    "hurt": {
        "src": "plaster",
        "label_he": "כואב",
        "keywords_he": ["כואב", "כאב", "אאוץ׳"],
    },
    "play": {
        "src": "play_,_to",
        "label_he": "לשחק",
        "keywords_he": ["לשחק", "משחק", "צעצוע"],
    },
    "break": {
        "src": "rest_,_to",
        "label_he": "הפסקה",
        "keywords_he": ["הפסקה", "מנוחה", "לנוח"],
    },
    "home": {
        "src": "house",
        "label_he": "בית",
        "keywords_he": ["בית", "הביתה", "ללכת הביתה"],
    },
    "mom": {"src": "mum_parent", "label_he": "אמא", "keywords_he": ["אמא", "אימא"]},
    "dad": {"src": "dad_parent", "label_he": "אבא", "keywords_he": ["אבא"]},
    "music": {
        "src": "music",
        "label_he": "מוזיקה",
        "keywords_he": ["מוזיקה", "שיר", "לשמוע"],
    },
    "book": {
        "src": "notebook",
        "label_he": "ספר",
        "keywords_he": ["ספר", "לקרוא", "סיפור"],
    },
    "ball": {"src": "ball", "label_he": "כדור", "keywords_he": ["כדור", "לשחק בכדור"]},
    "sleep": {
        "src": "sleep_male_,_to",
        "label_he": "לישון",
        "keywords_he": ["לישון", "שינה", "עייף", "מיטה"],
    },
    "hot": {"src": "hot", "label_he": "חם", "keywords_he": ["חם", "חום"]},
    "cold": {"src": "snow", "label_he": "קר", "keywords_he": ["קר", "קור"]},
    "happy": {
        "src": "happy_man",
        "label_he": "שמח",
        "keywords_he": ["שמח", "שמחה", "כיף"],
    },
    "sad": {
        "src": "sad_man",
        "label_he": "עצוב",
        "keywords_he": ["עצוב", "עצב", "בוכה"],
    },
    "angry": {
        "src": "angry_man",
        "label_he": "כועס",
        "keywords_he": ["כועס", "כעס", "רוגז"],
    },
    "scared": {
        "src": "afraid_man",
        "label_he": "מפחד",
        "keywords_he": ["מפחד", "פחד", "מפוחד"],
    },
    "love": {
        "src": "heart_shape",
        "label_he": "אוהב",
        "keywords_he": ["אוהב", "אהבה", "אוהבת"],
    },
    "finished": {
        "src": "finish",
        "label_he": "לסיים",
        "keywords_he": ["לסיים", "סיימתי", "גמרתי", "נגמר"],
    },
    "hello": {
        "src": "hello",
        "label_he": "שלום",
        "keywords_he": ["שלום", "היי", "להתראות"],
    },
    "thanks": {"src": None, "label_he": "תודה", "keywords_he": ["תודה", "תודה רבה"]},
    "wait": {
        "src": "wait_,_to",
        "label_he": "לחכות",
        "keywords_he": ["לחכות", "רגע", "המתנה"],
    },
    "go": {"src": "go_,_to", "label_he": "ללכת", "keywords_he": ["ללכת", "בוא", "נלך"]},
    "look": {
        "src": "look_,_to",
        "label_he": "להסתכל",
        "keywords_he": ["להסתכל", "תראה", "לראות"],
    },
    "open": {"src": "open_,_to", "label_he": "לפתוח", "keywords_he": ["לפתוח", "פתח"]},
}

# Ids in LOCKED whose Mulberry substitute is an approximation, not a direct
# match — flagged for extra review scrutiny, excluded from bulk-approve.
SUBSTITUTE_IDS = {
    "yes",
    "no",
    "love",
    "you",
    "i",
    "hurt",
    "book",
    "cold",
    "home",
    "break",
}

# Whole-category exclusions: zero relevance to a Hebrew children's AAC board,
# and Country Flags alone is 254 rows / ~6.7MB of art that would otherwise
# need Hebrew country names authored for no product value.
EXCLUDED_CATEGORIES = {"Country Flags", "Country Maps"}

_VERB_MARKER = re.compile(r"_,_")


def slugify(symbol_en: str) -> str:
    """Mulberry filename stem -> a URL/filename-safe id candidate.

    'eat_,_to' -> 'eat', 'toilet_,_go_to_the' -> 'toilet',
    'a_-_lower_case' -> 'a-lower-case', 'I' -> 'i'.
    """
    s = _VERB_MARKER.split(symbol_en, maxsplit=1)[0]
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s:
        s = "x"
    if s[0].isdigit():
        s = f"n-{s}"
    return s


@dataclass
class SourceRow:
    symbol_id: str
    category_id: str
    grammar: str
    rated: bool
    tags: str
    symbol_en: str
    category_en: str


def iter_source(zip_path: Path = DEFAULT_SOURCE_ZIP) -> list[SourceRow]:
    """Read symbol-info.csv from the archive in memory. Never extracts to
    disk — the zip is the immutable upstream, and only the subset that
    actually ships goes through the ingest pipeline in build_symbols.py."""
    with zipfile.ZipFile(zip_path) as z:
        data = z.read(_CSV_NAME).decode("utf-8-sig")
        svg_names = {
            n[len(_SVG_DIR) : -4]
            for n in z.namelist()
            if n.startswith(_SVG_DIR) and n.endswith(".svg")
        }
    rows = []
    for r in csv.DictReader(io.StringIO(data)):
        if r["symbol-en"] not in svg_names:
            raise ValueError(
                f"CSV row {r['symbol-id']} ({r['symbol-en']!r}) has no matching SVG"
            )
        rows.append(
            SourceRow(
                symbol_id=r["symbol-id"],
                category_id=r["category-id"],
                grammar=r["grammar"],
                rated=r["rated"] == "1",
                tags=r["tags"],
                symbol_en=r["symbol-en"],
                category_en=r["category-en"],
            )
        )
    return rows


def _reserved_slugs() -> dict[str, str]:
    """slug -> locked app id, for collision priority (locked ids always win)."""
    return {app_id: app_id for app_id in LOCKED}


def bootstrap(zip_path: Path = DEFAULT_SOURCE_ZIP) -> dict[str, Any]:
    """Build a fresh manifest from the source archive + LOCKED. Deterministic:
    slug collisions resolve in ascending Mulberry symbol-id order."""
    src_by_stem = {row.symbol_en: row for row in iter_source(zip_path)}
    locked_stems = {v["src"] for v in LOCKED.values() if v["src"]}

    entries: dict[str, dict[str, Any]] = {}
    used_slugs = set(LOCKED.keys())

    # Locked entries first — always present, id/label/keywords never regenerated.
    for app_id, v in LOCKED.items():
        row = src_by_stem.get(v["src"]) if v["src"] else None
        entries[row.symbol_id if row else f"locked:{app_id}"] = {
            "src": v["src"],
            "category_en": row.category_en if row else None,
            "grammar": row.grammar if row else None,
            "id": app_id,
            "label_he": v["label_he"],
            "keywords_he": list(v["keywords_he"]),
            "status": "approved",  # already-authored Hebrew — not up for re-review
            "locked": True,
            "scrutiny": "substitute" if app_id in SUBSTITUTE_IDS else None,
            "note": None
            if v["src"]
            else "no Mulberry equivalent — keeping current placeholder SVG",
            "reviewed_at": None,
        }

    # Everything else, in ascending symbol-id order for deterministic dedupe.
    for row in sorted(iter_source(zip_path), key=lambda r: int(r.symbol_id)):
        if row.symbol_en in locked_stems:
            continue  # already covered above
        if row.rated:
            entries[row.symbol_id] = _rejected_entry(row, "explicit content (rated=1)")
            continue
        if row.category_en in EXCLUDED_CATEGORIES:
            entries[row.symbol_id] = _rejected_entry(
                row, f"excluded category: {row.category_en}"
            )
            continue

        slug = slugify(row.symbol_en)
        candidate = slug
        n = 2
        while candidate in used_slugs:
            candidate = f"{slug}-{n}"
            n += 1
        used_slugs.add(candidate)

        entries[row.symbol_id] = {
            "src": row.symbol_en,
            "category_en": row.category_en,
            "grammar": row.grammar,
            "id": candidate,
            "label_he": "",
            "keywords_he": [],
            "status": "pending",
            "locked": False,
            "scrutiny": "text-glyph" if _uses_text_glyph(row) else None,
            "note": None,
            "reviewed_at": None,
        }

    return {
        "schema": SCHEMA_VERSION,
        "mulberry_version": MULBERRY_VERSION,
        "entries": entries,
    }


# Files known (from the archive scan during planning) to render via <text>/font
# glyphs rather than pure vector paths — flagged so a reviewer knows a device's
# installed fonts affect how these look.
_TEXT_GLYPH_STEMS = {
    "add",
    "half",
    "percent",
    "quarter",
    "three_quarters",
    "print",
    "inbox",
    "outbox",
    "ready",
}


def _uses_text_glyph(row: SourceRow) -> bool:
    return row.symbol_en in _TEXT_GLYPH_STEMS or row.symbol_en.startswith("algebra_")


def _rejected_entry(row: SourceRow, note: str) -> dict[str, Any]:
    return {
        "src": row.symbol_en,
        "category_en": row.category_en,
        "grammar": row.grammar,
        "id": slugify(row.symbol_en),
        "label_he": "",
        "keywords_he": [],
        "status": "rejected",
        "locked": False,
        "scrutiny": None,
        "note": note,
        "reviewed_at": None,
    }


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(manifest: dict[str, Any], path: Path = DEFAULT_MANIFEST) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def merge_review(
    manifest: dict[str, Any], review_rows: list[dict[str, Any]], *, force: bool = False
) -> dict[str, Any]:
    """Write reviewed decisions from the review Artifact back into the
    manifest. `review_rows` items: {symbol_id, id, src, label_he,
    keywords_he, status, note, reviewed_at}. Rows absent from review_rows are
    untouched (still pending). Refuses to downgrade an already-approved/edited
    row to pending/rejected without force=True — a partial or stale export
    from the artifact must never silently erase a prior approval.

    Locked entries (the 36 original ids) ARE reviewable and editable here —
    that's the whole point of flagging a substitute for scrutiny, so a
    reviewer can correct a bad art pick (`src`) or wording (`label_he`)
    without touching this module. What's locked is specifically `id`: it's
    the FK target from five tables plus board_templates/memory.js's raw
    string references, so a locked row's `id` is silently kept as-is even if
    the review row proposes a different one — never raised as an error,
    since the artifact shouldn't need to know this rule to render an
    (appropriately non-editable) id field."""
    entries = manifest["entries"]
    downgraded = []
    for r in review_rows:
        sid = r["symbol_id"]
        if sid not in entries:
            raise KeyError(f"review row references unknown symbol-id {sid}")
        current = entries[sid]
        was_decided = current["status"] in ("approved", "edited")
        now_decided = r["status"] in ("approved", "edited")
        if was_decided and not now_decided and not force:
            downgraded.append(sid)
            continue
        current.update(
            {
                "id": current["id"] if current.get("locked") else r["id"],
                "src": r.get("src", current["src"]),
                "label_he": r["label_he"],
                "keywords_he": r["keywords_he"],
                "status": r["status"],
                "note": r.get("note"),
                "reviewed_at": r.get("reviewed_at"),
            }
        )
    if downgraded and not force:
        raise ValueError(
            f"{len(downgraded)} row(s) would be downgraded from approved/edited "
            f"(e.g. {downgraded[:5]}) — pass force=True if that's really intended"
        )
    return manifest


def validate(manifest: dict[str, Any]) -> list[str]:
    """Return a list of problems; empty list = clean."""
    problems: list[str] = []
    entries = manifest["entries"]

    locked_ids = {v["id"] for v in entries.values() if v.get("locked")}
    missing_locked = set(LOCKED) - locked_ids
    if missing_locked:
        problems.append(f"missing locked ids: {sorted(missing_locked)}")

    seen_ids: dict[str, str] = {}
    for sid, e in entries.items():
        if e["status"] in ("rejected", "pending"):
            continue
        app_id = e["id"]
        if app_id in seen_ids:
            problems.append(f"duplicate id {app_id!r}: {seen_ids[app_id]} and {sid}")
        seen_ids[app_id] = sid
        if e["status"] in ("approved", "edited") and not e["label_he"]:
            problems.append(f"{sid} ({app_id}) is {e['status']} with no label_he")

    return problems


def approved_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        sid: e
        for sid, e in manifest["entries"].items()
        if e["status"] in ("approved", "edited")
    }
