"""Ranked symbol search — lexical tiers + a semantic backfill.

The library is ~1,000 rows (Mulberry, production) up to ~5,600 (dev, with the
PCS set), all held in memory by ``repositories.symbols._all()``. This module
turns that snapshot into a searchable :class:`Index` once per worker and ranks
a query against it.

Nine tiers, best first:

    0  label == q                      (unchanged from the old flat search)
    1  label.startswith(q)
    2  q in keywords
    3  search_key(q) is a full label/keyword key      (niqqud, finals, case)
    4  a de-cliticised query token hits a symbol stem  (הכלב -> כלב, plurals)
    5  ktiv-male/haser skeleton match   (מכנית -> מכונית)
    6  raw substring of label / keyword / id           (old tiers 3-5)
    7  normalized substring of "label + keywords"
    8  fuzzy: difflib ratio >= FUZZY_CUTOFF against a label
    9  SEMANTIC BACKFILL — fastText cosine neighbours, only to fill the page

Tier 9 is strict backfill: ``room = limit - len(everything above)``. A query
with a full page of lexical hits gets zero semantic rows, exact intent is never
displaced, and ``total`` never exceeds ``limit`` (so the picker's "showing N of
M" hint fires exactly as often as before this change).

Semantic search needs the precomputed vectors under ``app/data/symbol_vectors/``
(built by ``scripts/build_symbol_vectors.py``). If they're absent — a fresh
checkout, a CI job without them — :func:`_vectors` returns ``None`` and tiers
0-8 carry on unchanged.
"""

from __future__ import annotations

import difflib
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.services import hebrew as heb

_log = logging.getLogger("app.symbols")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "symbol_vectors"
_SCHEMA = 1

# Absolute cosine floor for a semantic hit. Set from
# `build_symbol_vectors.py --eval` (p99.5 of the random-pair distribution).
# A rebuild that would change this is a deliberate, reviewed edit — never read
# it back from meta.json at runtime.
SEMANTIC_MIN_COS = 0.34
# Also require cos >= this * the best cosine for the query, so a strong match
# trims its own co-hyponym tail and a weak query contributes nothing.
SEMANTIC_REL_GATE = 0.72
# Never backfill more than this many related-by-meaning rows onto a page.
SEMANTIC_MAX = 24
FUZZY_CUTOFF = 0.82

_LIMIT_DEFAULT = 60


# --- precomputed vectors ---------------------------------------------------


@dataclass(frozen=True)
class _Vectors:
    symbols: np.ndarray  # (S, D) float32 — unit, post-processed
    id_to_row: dict[str, int]
    words: np.ndarray  # (V, D) float16 memmap — unit, NOT post-processed
    word_index: dict[str, int]
    mean: np.ndarray  # (D,) float32
    pc: np.ndarray  # (D,) float32
    dim: int


@lru_cache(maxsize=1)
def _vectors() -> _Vectors | None:
    if not (DATA_DIR / "meta.json").exists():
        _log.info("symbol vectors not built — semantic search disabled")
        return None
    try:
        meta = json.loads((DATA_DIR / "meta.json").read_text("utf-8"))
        if meta.get("schema") != _SCHEMA:
            _log.warning("symbol vectors: schema %s != %s — disabled", meta.get("schema"), _SCHEMA)
            return None
        dim = int(meta["dim"])
        symbols = np.load(DATA_DIR / "symbols.f16.npy", allow_pickle=False).astype(np.float32)
        words = np.load(DATA_DIR / "words.f16.npy", mmap_mode="r", allow_pickle=False)
        keys = (DATA_DIR / "words.txt").read_text("utf-8").split("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        _log.warning(
            "symbol vectors present but unreadable — semantic search disabled", exc_info=True
        )
        return None

    if symbols.shape != (len(meta["ids"]), dim) or words.shape[1] != dim:
        _log.warning("symbol vectors: shape mismatch — disabled")
        return None

    # words.txt is frequency-ordered; first occurrence of a key wins. The
    # per-batch "extra" table is appended and overrides on collision (its
    # tokens are guaranteed relevant to a shipped symbol).
    word_index = {k: i for i, k in enumerate(keys) if k}
    try:
        extra_keys = (DATA_DIR / "words_extra.txt").read_text("utf-8").split("\n")
        extra = np.load(DATA_DIR / "words_extra.f16.npy", mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError):
        extra_keys, extra = [], None
    if extra is not None and extra.shape[1] == dim:
        base = len(keys)
        words = np.concatenate([np.asarray(words), np.asarray(extra)], axis=0)
        for i, k in enumerate(extra_keys):
            if k:
                word_index[k] = base + i

    return _Vectors(
        symbols=np.ascontiguousarray(symbols),
        id_to_row={sid: i for i, sid in enumerate(meta["ids"])},
        words=words,
        word_index=word_index,
        mean=np.asarray(meta["mean"], dtype=np.float32),
        pc=np.asarray(meta["pc"], dtype=np.float32),
        dim=dim,
    )


def reset_cache() -> None:
    _vectors.cache_clear()


# --- the searchable index -----------------------------------------------


@dataclass(frozen=True)
class Index:
    rows: tuple[dict, ...]
    keys: tuple[frozenset[str], ...]  # search_key(label) + search_key(each kw)
    stems: tuple[frozenset[str], ...]  # declitic'd single tokens of the above
    haser_keys: tuple[frozenset[str], ...]  # haser() of every entry in `keys`
    blob: tuple[str, ...]  # search_key("label  kw kw ...")
    label_key: tuple[str, ...]  # search_key(label) — fuzzy candidate strings
    by_label_key: dict[str, tuple[int, ...]]  # label_key -> row indices (labels aren't unique)
    matrix: np.ndarray | None  # (len(rows), D) float32; a zero row = no vector


def build_index(rows: tuple[dict, ...]) -> Index:
    keys: list[frozenset[str]] = []
    stems: list[frozenset[str]] = []
    haser_keys: list[frozenset[str]] = []
    blob: list[str] = []
    label_key: list[str] = []

    for s in rows:
        label = s.get("label_he") or ""
        kws = s.get("keywords_he") or []
        row_keys = {heb.search_key(label)} | {heb.search_key(k) for k in kws}
        row_keys.discard("")
        row_stems: set[str] = set()
        for k in row_keys:
            for tok in heb.tokens(k):
                row_stems.update(heb.stem_forms(tok))
        keys.append(frozenset(row_keys))
        stems.append(frozenset(row_stems))
        haser_keys.append(frozenset(heb.haser(k) for k in row_keys))
        blob.append(heb.search_key(label + " " + " ".join(kws)))
        label_key.append(heb.search_key(label))

    by_label_key: dict[str, list[int]] = {}
    for i, lk in enumerate(label_key):
        by_label_key.setdefault(lk, []).append(i)

    return Index(
        rows=rows,
        keys=tuple(keys),
        stems=tuple(stems),
        haser_keys=tuple(haser_keys),
        blob=tuple(blob),
        label_key=tuple(label_key),
        by_label_key={k: tuple(v) for k, v in by_label_key.items()},
        matrix=_aligned_matrix(rows),
    )


def _aligned_matrix(rows: tuple[dict, ...]) -> np.ndarray | None:
    vecs = _vectors()
    if vecs is None:
        return None
    m = np.zeros((len(rows), vecs.dim), dtype=np.float32)
    for i, r in enumerate(rows):
        j = vecs.id_to_row.get(r["id"])
        if j is not None:
            m[i] = vecs.symbols[j]
    return np.ascontiguousarray(m)


# --- query embedding ---------------------------------------------------


def embed(query: str) -> np.ndarray | None:
    """The query, in the same space as ``Index.matrix``. ``None`` when the
    vectors are unavailable or no query token is in the word table."""
    vecs = _vectors()
    if vecs is None:
        return None
    picked: list[np.ndarray] = []
    for tok in heb.tokens(heb.search_key(query)):
        for form in heb.declitic(tok):  # surface form first
            j = vecs.word_index.get(form)
            if j is not None:
                picked.append(np.asarray(vecs.words[j], dtype=np.float32))
                break
    if not picked:  # guard BEFORE np.mean([]) — filterwarnings=error
        return None
    v = np.mean(picked, axis=0)
    v = v - vecs.mean
    v = v - float(v @ vecs.pc) * vecs.pc
    n = float(np.linalg.norm(v))
    if n < 1e-6:  # guard BEFORE the divide
        return None
    return (v / n).astype(np.float32)


# --- search ----------------------------------------------------------


def search(index: Index, query: str, *, limit: int = _LIMIT_DEFAULT) -> tuple[list[dict], int]:
    q = (query or "").strip()
    if not q:
        return list(index.rows[:limit]), len(index.rows)

    kq = heb.search_key(q)
    tq: set[str] = set()
    for tok in heb.tokens(kq):
        tq.update(heb.stem_forms(tok))
    hq = heb.haser(kq)

    def lexical_tier(i: int, s: dict) -> int | None:
        label = s.get("label_he") or ""
        kws = s.get("keywords_he") or []
        tiers = (
            label == q,
            label.startswith(q),
            q in kws,
            kq in index.keys[i],
            bool(tq & index.stems[i]),
            bool(hq) and hq in index.haser_keys[i],
            q in label or any(q in kw for kw in kws) or q in s["id"],
            bool(kq) and kq in index.blob[i],
        )
        return next((t for t, hit in enumerate(tiers) if hit), None)

    scored: list[tuple[int, int, float]] = []
    for i, s in enumerate(index.rows):
        t = lexical_tier(i, s)
        if t is not None:
            scored.append((t, i, 0.0))
    seen = {i for _t, i, _sc in scored}

    if len(scored) < limit:  # tier 8 — fuzzy typos
        for i, ratio in _fuzzy(index, kq, seen, limit - len(scored)):
            scored.append((8, i, -ratio))
            seen.add(i)

    room = min(SEMANTIC_MAX, limit - len(scored))
    if room > 0:  # tier 9 — related by meaning
        for i, cos in _semantic(index, q, seen, room):
            scored.append((9, i, -cos))
            seen.add(i)

    scored.sort(key=lambda t: (t[0], t[2], t[1]))
    return [index.rows[i] for _t, i, _sc in scored[:limit]], len(scored)


def _fuzzy(index: Index, kq: str, seen: set[int], k: int) -> list[tuple[int, float]]:
    if not kq or k <= 0:
        return []
    cands = difflib.get_close_matches(
        kq, index.by_label_key.keys(), n=k + len(seen), cutoff=FUZZY_CUTOFF
    )
    out: list[tuple[int, float]] = []
    for cand in cands:
        ratio = difflib.SequenceMatcher(None, kq, cand).ratio()
        for i in index.by_label_key[cand]:
            if i not in seen:
                out.append((i, ratio))
                seen.add(i)
                break
        if len(out) == k:
            break
    return out


def _semantic(index: Index, query: str, seen: set[int], k: int) -> list[tuple[int, float]]:
    if index.matrix is None or k <= 0:
        return []
    qv = embed(query)
    if qv is None:
        return []
    sims = index.matrix @ qv  # (N,) float32
    best = float(sims.max(initial=0.0))
    if best < SEMANTIC_MIN_COS:
        return []
    floor = max(SEMANTIC_MIN_COS, SEMANTIC_REL_GATE * best)
    out: list[tuple[int, float]] = []
    for i in np.argsort(-sims)[: k + len(seen)].tolist():
        if i in seen or float(sims[i]) < floor:
            continue
        out.append((i, float(sims[i])))
        if len(out) == k:
            break
    return out
