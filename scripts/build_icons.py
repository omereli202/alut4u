#!/usr/bin/env python3
"""Generate the bundled UI icon sprite (control glyphs, not AAC content symbols
— those are frontend/assets/symbols/, see build_symbols.py).

Source: Google's Material Symbols (Outlined, weight 400), Apache-2.0, mirrored
as plain SVG by https://github.com/marella/material-symbols. Fetched once at
authoring time and committed — the shipped app never hits a CDN at runtime
(docs/design.md §2 offline rule; CLAUDE.md "no new dependencies without
discussion" — this is a one-time fetch into a static asset, not a runtime dep).

The glyph list is what docs/design.md §3 commissions plus what the Stitch
export (docs/design/stitch-export/) actually used for controls — see that
folder's README for the full audit.

Outputs:
  frontend/assets/icons/sprite.svg   (one <symbol> per glyph, id = glyph name)
  frontend/assets/icons/LICENSE

Usage: python3 scripts/build_icons.py
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "frontend" / "assets" / "icons"

SOURCE = "https://raw.githubusercontent.com/marella/material-symbols/main/svg/400/outlined/{name}.svg"

# Glyph name -> Hebrew label used as the default aria-label when a call site
# doesn't pass its own (icon() in ui.js lets any call site override this).
ICONS: dict[str, str] = {
    "lock": "מצב מטפל",
    "close": "סגירה",
    "star": "אסימון",
    "check": "אישור",
    "check_circle": "בוצע",
    "cancel": "ביטול",
    "play_arrow": "הפעלה",
    "pause": "השהיה",
    "stop_circle": "עצירה",
    "backspace": "מחיקת תו",
    "mic": "הקלטה",
    "volume_up": "הקראה",
    "calendar_month": "לוח שנה",
    "menu_book": "סיפור",
    "chevron_left": "הבא",  # RTL: "next" points left
    "chevron_right": "הקודם",  # RTL: "previous" points right
    "add": "הוספה",
    "delete": "מחיקה",
    "drag_indicator": "גרירה לשינוי סדר",
    "edit": "עריכה",
    "settings": "הגדרות",
    "celebration": "חגיגה",
    "logout": "יציאה",
    "info": "מידע",
    "warning": "אזהרה",
    "arrow_back": "חזרה",
    "undo": "ביטול פעולה",
    "remove": "הפחתה",
    "thumb_up": "כל הכבוד",
    # Added for docs/design/stitch-export-2 (PIN gate, boot screen, shared
    # states, reading & writing, story reader).
    "arrow_forward": "קדימה",
    "auto_stories": "קריאה",
    "dashboard": "לוח בקרה",
    "gpp_maybe": "אזהרת אבטחה",
    "inbox": "ריק",
    "manage_accounts": "ניהול חשבון",
    "refresh": "רענון",
    "security": "אבטחה",
    "toll": "אסימון",
    "wifi_off": "אין חיבור",
    # Added for the User-Mode home tile grid (T1.3) — no existing glyph fit
    # "communication" (mic is already claimed by voice recording) or "calm".
    "forum": "תקשורת",
    "spa": "פינת רוגע",
}

_SYMBOL_RE = re.compile(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', re.S)


def fetch(name: str) -> str:
    with urllib.request.urlopen(SOURCE.format(name=name), timeout=15) as r:
        raw = r.read().decode("utf-8")
    m = _SYMBOL_RE.search(raw)
    if not m:
        raise RuntimeError(f"couldn't parse {name}.svg: {raw[:200]}")
    view_box, inner = m.groups()
    return view_box, inner.strip()


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    symbols = []
    for name in sorted(ICONS):
        view_box, inner = fetch(name)
        symbols.append(f'<symbol id="{name}" viewBox="{view_box}">{inner}</symbol>')
        print(f"  + {name}")

    sprite = (
        '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n  '
        + "\n  ".join(symbols)
        + "\n</svg>\n"
    )
    (ICON_DIR / "sprite.svg").write_text(sprite, encoding="utf-8")

    (ICON_DIR / "LICENSE").write_text(
        "Material Symbols (Outlined, weight 400)\n"
        "Copyright Google Inc.\n"
        "Licensed under the Apache License, Version 2.0:\n"
        "https://www.apache.org/licenses/LICENSE-2.0\n\n"
        "Fetched as plain SVG via https://github.com/marella/material-symbols "
        "(also Apache-2.0) by scripts/build_icons.py. Not modified beyond\n"
        "wrapping each glyph in a <symbol> for use with <use href=\"#name\">.\n",
        encoding="utf-8",
    )
    print(f"\nWrote {len(ICONS)} icons to {ICON_DIR / 'sprite.svg'}")


if __name__ == "__main__":
    main()
