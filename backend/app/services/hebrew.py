"""Lenient Hebrew comparison for the writing-practice check.

Ignores niqqud, normalises final-letter forms to their base, collapses
whitespace and trims punctuation — so a child who writes ``שלומ`` for ``שלום``
still passes.
"""

from __future__ import annotations

import re

_NIQQUD = re.compile(r"[֑-ׇ]")
_PUNCT = re.compile(r"[.,;:!?׃״׳'\"()\-–—]")
_FINALS = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})


def normalize(text: str) -> str:
    text = _NIQQUD.sub("", text or "")
    text = _PUNCT.sub("", text)
    text = text.translate(_FINALS)
    return re.sub(r"\s+", " ", text).strip()


def matches(submitted: str, target: str) -> bool:
    return normalize(submitted) == normalize(target)
