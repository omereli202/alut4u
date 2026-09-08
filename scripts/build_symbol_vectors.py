#!/usr/bin/env python3
"""Precompute the fastText vectors that power fuzzy + semantic symbol search.

    python scripts/build_symbol_vectors.py                 # dry run: coverage + diagnostics
    python scripts/build_symbol_vectors.py --apply
    python scripts/build_symbol_vectors.py --probe "אוטו,גור,כלב,שמח"
    python scripts/build_symbol_vectors.py --eval          # label round-trip + threshold suggestion

LOCAL ONLY. Needs `fasttext` and the ~7GB `cc.he.300.bin`, neither of which is
a backend dependency:

    pip install fasttext-wheel numpy
    # download cc.he.300.bin.gz from https://fasttext.cc/docs/en/crawl-vectors.html
    gunzip ~/Downloads/cc.he.300.bin.gz

Writes six files under `backend/app/data/symbol_vectors/` — see docs/symbols.md
§ "Symbol vectors". `words.*` (the 20k core Hebrew table) is only rewritten when
its key list changes; the small per-symbol / per-batch files change every run.

The pooling + post-processing here MUST stay byte-identical to
`backend/app/services/symbol_search.py::embed` — build and runtime share one
arithmetic. Any change to `post()` invalidates every stored vector; regenerate,
re-run `--eval`, and paste the suggested SEMANTIC_MIN_COS into that module.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import mulberry_manifest as mm
from app.services import hebrew as heb

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "backend" / "app" / "data" / "symbol_vectors"
DEFAULT_MODEL = Path.home() / "Downloads" / "cc.he.300.bin"

SCHEMA = 1
DEFAULT_VOCAB = 20_000
_HEB_WORD = re.compile(r"^[א-ת]{2,}$")
_LABEL_W = 1.0
_KEYWORD_W = 0.5


# --- model (lazy) ----------------------------------------------------------


def _load_model(path: Path):
    try:
        import fasttext
    except ImportError as e:
        raise SystemExit(
            "fasttext is a LOCAL-ONLY build dependency (deliberately not in "
            "backend/pyproject.toml). Install it once:\n"
            "    pip install fasttext-wheel\n"
            "and download cc.he.300.bin (~7GB) — see docs/symbols.md § Symbol vectors."
        ) from e
    if not path.exists():
        raise SystemExit(
            f"model not found: {path}\n(pass --model, or drop cc.he.300.bin in ~/Downloads)"
        )
    print(f"loading {path} …", flush=True)
    return fasttext.load_model(str(path))


# --- shared arithmetic (mirror of symbol_search.embed) -------------------


def _unit(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=-1, keepdims=True)
    return np.divide(m, n, out=np.zeros_like(m), where=n > 1e-9)


def _pool(unit_rows: list[np.ndarray], weights: list[float]) -> np.ndarray | None:
    if not unit_rows:
        return None
    w = np.asarray(weights, dtype=np.float32)[:, None]
    return (np.asarray(unit_rows, dtype=np.float32) * w).sum(0) / float(w.sum())


def _post(v: np.ndarray, mean: np.ndarray, pc: np.ndarray) -> np.ndarray:
    v = v - mean
    v = v - (v @ pc) * pc
    n = np.linalg.norm(v)
    return v / n if n > 1e-6 else v


# --- manifest --------------------------------------------------------------


def _approved(manifest: dict) -> list[dict]:
    """Every approved/edited entry — the exact set build_symbols.py ships.
    (Not `_entries_to_ingest`: its PCS-reskin skip is about SVG clobbering.)"""
    return sorted(
        (
            e
            for e in manifest["entries"].values()
            if e["status"] in ("approved", "edited")
        ),
        key=lambda e: e["id"],
    )


def _symbol_terms(entry: dict) -> list[tuple[str, float]]:
    """[(word, weight)] for one symbol. label tokens @1.0, distinct keyword
    tokens @0.5. `keywords[0]` is usually a copy of the label — deduped."""
    label = heb.search_key(entry["label_he"])
    seen = set(heb.tokens(label))
    out = [(w, _LABEL_W) for w in seen]
    for kw in entry.get("keywords_he") or []:
        for w in heb.tokens(heb.search_key(kw)):
            if w not in seen:
                seen.add(w)
                out.append((w, _KEYWORD_W))
    return out


# --- build ---------------------------------------------------------------


def build(model, entries: list[dict], vocab: int) -> dict:
    dim = model.get_dimension()

    # 1. core word table: top `vocab` frequency-ordered Hebrew types.
    core_keys: list[str] = []
    core_surface: list[str] = []
    seen_keys: set[str] = set()
    for w in model.get_words():  # frequency order
        nk = heb.search_key(w)
        if not _HEB_WORD.fullmatch(nk) or nk in seen_keys:
            continue
        seen_keys.add(nk)
        core_keys.append(nk)
        core_surface.append(w)
        if len(core_keys) >= vocab:
            break
    core_raw = np.asarray(
        [model.get_word_vector(w) for w in core_surface], dtype=np.float32
    )
    core_unit = _unit(core_raw)

    # 2. post-processing params, computed over the core matrix.
    mean = core_unit.mean(0)
    centred = core_unit - mean
    _u, _s, vt = np.linalg.svd(centred, full_matrices=False)
    pc = vt[0].astype(np.float32)

    # 3. per-symbol vectors.
    ids: list[str] = []
    rows: list[np.ndarray] = []
    empty: list[str] = []
    core_lookup = {k: i for i, k in enumerate(core_keys)}
    for e in entries:
        terms = _symbol_terms(e)
        units, weights = [], []
        for w, wt in terms:
            j = core_lookup.get(w)
            unit = core_unit[j] if j is not None else _unit(model.get_word_vector(w))
            units.append(np.asarray(unit, dtype=np.float32))
            weights.append(wt)
        pooled = _pool(units, weights)
        ids.append(e["id"])
        if pooled is None:
            empty.append(e["id"])
            rows.append(np.zeros(dim, dtype=np.float32))
        else:
            rows.append(_post(pooled, mean, pc))
    symbols = np.asarray(rows, dtype=np.float32)

    # 4. extra word table: symbol tokens missing from core (unit, NOT post).
    extra_seen: set[str] = set()
    for e in entries:
        for kw in [e["label_he"], *(e.get("keywords_he") or [])]:
            for w in heb.tokens(heb.search_key(kw)):
                if w not in core_lookup:
                    extra_seen.add(w)
    extra_keys = sorted(extra_seen)
    extra_raw = np.asarray(
        [model.get_word_vector(k) for k in extra_keys], dtype=np.float32
    ).reshape(-1, dim)
    extra_unit = _unit(extra_raw)

    return {
        "dim": dim,
        "ids": ids,
        "symbols": symbols.astype(np.float16),
        "core_keys": core_keys,
        "core_unit": core_unit.astype(np.float16),
        "extra_keys": extra_keys,
        "extra_unit": extra_unit.astype(np.float16),
        "mean": mean.astype(np.float32),
        "pc": pc,
        "empty": empty,
        "hebrew_types": len(seen_keys),
    }


# --- diagnostics -------------------------------------------------------


def _rank(built: dict, qv: np.ndarray) -> np.ndarray:
    return built["symbols"].astype(np.float32) @ qv


def _embed_query(built: dict, q: str) -> np.ndarray | None:
    idx = {k: i for i, k in enumerate(built["core_keys"])}
    idx.update(
        {k: len(built["core_keys"]) + i for i, k in enumerate(built["extra_keys"])}
    )
    table = np.concatenate(
        [built["core_unit"].astype(np.float32), built["extra_unit"].astype(np.float32)],
        axis=0,
    )
    picked = []
    for tok in heb.tokens(heb.search_key(q)):
        for form in heb.declitic(tok):
            j = idx.get(form)
            if j is not None:
                picked.append(table[j])
                break
    if not picked:
        return None
    v = _post(np.mean(picked, axis=0), built["mean"], built["pc"])
    n = np.linalg.norm(v)
    return v / n if n > 1e-6 else None


def diagnostics(built: dict, entries: list[dict]) -> dict:
    S = built["symbols"].astype(np.float32)
    n = len(entries)

    # label round-trip: each symbol's own label must retrieve it via cosine.
    top1 = top5 = 0
    for i, e in enumerate(entries):
        qv = _embed_query(built, e["label_he"])
        if qv is None:
            continue
        order = np.argsort(-(S @ qv))
        if order[0] == i:
            top1 += 1
        if i in order[:5]:
            top5 += 1

    # random-pair cosine distribution (post-processed symbol vectors).
    rng = np.random.default_rng(0)
    a = rng.integers(0, n, 20000)
    b = rng.integers(0, n, 20000)
    keep = a != b
    pair = (S[a[keep]] * S[b[keep]]).sum(1)
    pcts = {p: float(np.percentile(pair, p)) for p in (50, 90, 95, 99, 99.5)}

    return {
        "top1": top1,
        "top5": top5,
        "n": n,
        "random_pair_pct": pcts,
        "suggested_min_cos": round(pcts[99.5], 3),
    }


def _probe(built: dict, entries: list[dict], queries: list[str]) -> None:
    labels = [e["label_he"] for e in entries]
    for q in queries:
        qv = _embed_query(built, q)
        if qv is None:
            print(f"  {q:10} → (no query token in the word table)")
            continue
        order = np.argsort(-_rank(built, qv))[:10]
        parts = [f"{labels[i]} {float(_rank(built, qv)[i]):.2f}" for i in order]
        print(f"  {q:10} → " + " | ".join(parts))


# --- io ----------------------------------------------------------------


def _write_npy(path: Path, arr: np.ndarray) -> None:
    np.save(path, arr, allow_pickle=False)


def write(built: dict, diag: dict, model_path: Path, vocab: int) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    _write_npy(OUT_DIR / "symbols.f16.npy", built["symbols"])
    _write_npy(OUT_DIR / "words_extra.f16.npy", built["extra_unit"])
    (OUT_DIR / "words_extra.txt").write_text(
        "\n".join(built["extra_keys"]), encoding="utf-8"
    )

    # words.* only if the key list changed (git hygiene — many batches to come).
    wt = OUT_DIR / "words.txt"
    new_keys = "\n".join(built["core_keys"])
    if not wt.exists() or wt.read_text("utf-8") != new_keys:
        wt.write_text(new_keys, encoding="utf-8")
        _write_npy(OUT_DIR / "words.f16.npy", built["core_unit"])
        print(f"  words.*: rewritten ({len(built['core_keys'])} keys)")
    else:
        print(f"  words.*: unchanged ({len(built['core_keys'])} keys)")

    meta = {
        "schema": SCHEMA,
        "dim": built["dim"],
        "ids": built["ids"],
        "model": model_path.name,
        "vocab": vocab,
        "built_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        "counts": {
            "symbols": len(built["ids"]),
            "empty": len(built["empty"]),
            "core": len(built["core_keys"]),
            "extra": len(built["extra_keys"]),
        },
        "diagnostics": diag,
        "mean": [float(x) for x in built["mean"]],
        "pc": [float(x) for x in built["pc"]],
    }
    (OUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --- main ------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--apply", action="store_true", help="write the files (default: dry run)"
    )
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    p.add_argument("--vocab", type=int, default=DEFAULT_VOCAB)
    p.add_argument("--probe", default="", help="comma-separated queries to eyeball")
    p.add_argument(
        "--eval", action="store_true", help="print label round-trip + threshold"
    )
    args = p.parse_args()

    manifest = mm.load_manifest()
    entries = _approved(manifest)
    model = _load_model(args.model)
    built = build(model, entries, args.vocab)
    diag = diagnostics(built, entries)

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"\n[{mode}] symbol vectors")
    print(
        f"  symbols:  {diag['n']} approved+edited   ({len(built['empty'])} with no embeddable token)"
    )
    print(
        f"  vocab:    core {len(built['core_keys'])} (of {built['hebrew_types']} Hebrew types)  extra {len(built['extra_keys'])}"
    )
    print(
        f"  label round-trip: top-1 {diag['top1']}/{diag['n']} ({diag['top1'] / diag['n']:.1%})   top-5 {diag['top5']}/{diag['n']} ({diag['top5'] / diag['n']:.1%})"
    )
    rp = diag["random_pair_pct"]
    print(
        f"  random-pair cosine: p50 {rp[50]:.3f}  p95 {rp[95]:.3f}  p99 {rp[99]:.3f}  p99.5 {rp[99.5]:.3f}"
    )
    print(
        f"  → suggested SEMANTIC_MIN_COS = {diag['suggested_min_cos']}  (paste into app/services/symbol_search.py)"
    )

    probes = [q.strip() for q in args.probe.split(",") if q.strip()]
    if probes or args.eval:
        print("  probes:")
        _probe(
            built, entries, probes or ["אוטו", "גור", "כלב", "לאכול", "שמח", "מכנית"]
        )

    if args.apply:
        write(built, diag, args.model, args.vocab)
        print(
            "\n  next: paste the suggested SEMANTIC_MIN_COS, then commit "
            "backend/app/data/symbol_vectors/ and run pytest."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
