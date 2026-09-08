"""Lenient Hebrew comparison for the writing-practice check, plus a few extra
helpers for symbol search.

``normalize`` / ``matches`` are the writing-practice contract (see
``api/learning.py`` and ``test_learning.py``) — a child who writes ``שלומ`` for
``שלום`` passes, but ``הבית`` must NOT pass for ``בית``. **Do not make those two
more lenient.** Symbol search wants exactly that extra leniency, so it gets its
own functions below (``search_key``, ``tokens``, ``declitic``, ``haser``).
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


# --- symbol-search helpers (NOT part of the writing-practice contract) -------

# One-letter proclitics: bet, he, vav, kaf, lamed, mem, shin.
_CLITICS = "בהוכלמש"
_HEB_TOKEN = re.compile(r"[א-ת]+")
# A non-initial vav or yod — a mater lectionis, dropped to fold ktiv male /
# ktiv haser spellings onto one key (מכונית / מכנית -> מכנת).
_MATRES = re.compile(r"(?<=.)[וי]")


def search_key(text: str) -> str:
    """Comparison key for symbol search: ``normalize`` plus lower-casing (the
    English slugs). Deliberately separate from ``normalize`` so the
    writing-practice check never inherits search's extra leniency."""
    return normalize(text).lower()


def tokens(text: str) -> list[str]:
    """Hebrew word tokens of a string (run ``search_key`` first if needed)."""
    return _HEB_TOKEN.findall(text)


def declitic(word: str) -> list[str]:
    """The surface form first, then 1- and 2-letter clitic strips — but never a
    form shorter than 3 letters, so ``לב`` (heart) is not reduced to ``ב`` and
    ``הם`` stays ``הם``. Match if ANY returned form matches, original first."""
    out = [word]
    for n in (1, 2):
        if len(word) - n >= 3 and all(c in _CLITICS for c in word[:n]):
            out.append(word[n:])
    return out


def _deplural(word: str) -> list[str]:
    """Conservative plural/inflection folds on a token that has ALREADY been
    through :func:`search_key` (so final mem is ``מ``, not ``ם``). ``כלבים`` ->
    ``כלבימ`` -> ``כלב``; ``מכוניות`` -> ``מכונית`` (the fem ``ית`` <-> ``יות``
    swap). Only ever a whole-token candidate, never a substring probe."""
    out: list[str] = []
    if len(word) >= 6 and word.endswith("יות"):
        out.append(word[:-3] + "ית")
    if len(word) >= 5 and word[-2:] in ("ימ", "ות", "יי"):  # ים folded to ימ, ויים -> ...
        out.append(word[:-2])
    return out


def stem_forms(word: str) -> set[str]:
    """All comparison candidates for a single search token: the surface form,
    clitic-prefix strips, and plural/inflection folds (and prefix strips of
    those). Both the query token and each symbol keyword token are run through
    this, and a match is any non-empty intersection."""
    forms = set(declitic(word))
    for base in list(forms):
        forms.update(_deplural(base))
    for base in list(forms):
        forms.update(declitic(base))
    return {f for f in forms if len(f) >= 2}


def haser(word: str) -> str:
    """Fold a ktiv-male spelling onto its ktiv-haser skeleton by dropping every
    non-initial vav/yod: ``מכונית`` and ``מכנית`` both -> ``מכנת``. Lossy on
    purpose (``שיר`` -> ``שר``); only ever used as a whole-key exact match at a
    low search tier, never as a substring probe."""
    return _MATRES.sub("", word)
