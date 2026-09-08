"""services.symbol_search — tier logic and the semantic backfill.

Pure unit tests. No Supabase, no fastText. The `fake_vectors` fixture writes a
tiny 4-d vector set with ``mean = pc = 0`` so ``_post`` is the identity and
every cosine assertion is a plain dot product you can check by hand.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from app.services import symbol_search as ss

D = 6

# Unit vectors (NOT post-processed — mean=pc=0 makes post the identity).
# axes: 0 car, 1 dog, 2 table, 4 pup; 3 and 5 are unused ("far" directions).
WORDS: dict[str, list[float]] = {
    "מכונית": [1.0, 0, 0, 0, 0, 0],
    "אוטו": [0.96, 0.28, 0, 0, 0, 0],  # cos .96 with מכונית
    "כלב": [0, 1.0, 0, 0, 0, 0],
    "גור": [0, 1.0, 0, 0, 0, 0],  # identical to כלב for the gate maths
    "שולחנ": [0, 0, 1.0, 0, 0, 0],  # normalized key: final ן folded to נ
    "פילפ": [0, 0.6, 0, 0, 0.8, 0],  # cos .6 with גור — a relative-gate plant
    "רחוק": [0, 0, 0, 0.7, 0, 0.7],  # ~0 cos with every symbol — below the floor
}
SYMBOLS = {"car": "מכונית", "dog": "כלב", "table": "שולחנ", "pup": "פילפ"}


def _unit(a: np.ndarray) -> np.ndarray:
    return a / np.linalg.norm(a, axis=-1, keepdims=True)


@pytest.fixture
def fake_vectors(tmp_path, monkeypatch):
    d = tmp_path / "symbol_vectors"
    d.mkdir()
    keys = list(WORDS)
    W = _unit(np.array([WORDS[k] for k in keys], dtype=np.float32))
    S = _unit(np.array([WORDS[SYMBOLS[i]] for i in SYMBOLS], dtype=np.float32))
    np.save(d / "words.f16.npy", W.astype(np.float16))
    np.save(d / "symbols.f16.npy", S.astype(np.float16))
    (d / "words.txt").write_text("\n".join(keys), encoding="utf-8")
    np.save(d / "words_extra.f16.npy", np.zeros((1, D), dtype=np.float16))
    (d / "words_extra.txt").write_text("", encoding="utf-8")
    (d / "meta.json").write_text(
        json.dumps(
            {"schema": 1, "dim": D, "ids": list(SYMBOLS), "mean": [0.0] * D, "pc": [0.0] * D}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ss, "DATA_DIR", d)
    ss.reset_cache()
    yield d
    ss.reset_cache()


def _rows():
    return (
        {"id": "car", "label_he": "מכונית", "keywords_he": ["מכונית", "רכב"]},
        {"id": "dog", "label_he": "כלב", "keywords_he": ["כלב", "חיה"]},
        {"id": "table", "label_he": "שולחן", "keywords_he": []},
        {"id": "pup", "label_he": "פילפ", "keywords_he": []},
        {"id": "cat", "label_he": "חתול", "keywords_he": ["חתול", "חיה"]},
    )


def _ids(index, q, **kw):
    hits, total = ss.search(index, q, **kw)
    return [h["id"] for h in hits], total


# --- lexical tiers (no vectors needed) --------------------------------


def test_missing_files_leave_lexical_search_working(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "DATA_DIR", tmp_path / "nope")
    ss.reset_cache()
    idx = ss.build_index(_rows())
    assert ss._vectors() is None and idx.matrix is None
    assert _ids(idx, "מכונית")[0] == ["car"]  # tier 0
    assert _ids(idx, "מכנית")[0] == ["car"]  # tier 5 (ktiv haser)
    assert _ids(idx, "הכלב")[0] == ["dog"]  # tier 4 (clitic)
    assert _ids(idx, "כלבים")[0] == ["dog"]  # tier 4 (plural)
    assert _ids(idx, "שולחן")[0] == ["table"]  # tier 3 (final-letter fold)
    assert _ids(idx, "xyzzy")[0] == []


def test_clitic_never_strips_a_short_real_word(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "DATA_DIR", tmp_path / "nope")
    ss.reset_cache()
    rows = ({"id": "heart", "label_he": "לב", "keywords_he": []}, *_rows())
    idx = ss.build_index(rows)
    # "לב" must reach the heart via an exact tier, and must NOT strip to "ב"
    assert _ids(idx, "לב")[0][0] == "heart"


# --- semantic backfill ------------------------------------------------


def test_exact_label_outranks_a_semantic_neighbour(fake_vectors):
    idx = ss.build_index(_rows())
    ids, _ = _ids(idx, "כלב", limit=5)
    assert ids[0] == "dog"  # tier 0, never displaced by anything semantic


def test_synonym_found_by_meaning(fake_vectors):
    idx = ss.build_index(_rows())
    ids, _ = _ids(idx, "אוטו", limit=5)
    assert "car" in ids  # only reachable via tier 9


def test_semantic_is_backfill_only(fake_vectors):
    idx = ss.build_index(_rows())
    # one lexical hit, no room -> zero semantic rows, total is the lexical count
    ids, total = _ids(idx, "כלב", limit=1)
    assert ids == ["dog"]
    assert total == 1


def test_oov_query_degrades_without_warning(fake_vectors, recwarn):
    idx = ss.build_index(_rows())
    assert ss.embed("קרשמזץ") is None
    ids, total = _ids(idx, "קרשמזץ")
    assert ids == [] and total == 0
    assert not recwarn.list  # numpy mean/divide guards, under filterwarnings=error


def test_weak_neighbour_is_gated_out(fake_vectors):
    idx = ss.build_index(_rows())
    # "רחוק" sits at ~0.2 cos with every symbol — below SEMANTIC_MIN_COS
    ids, _ = _ids(idx, "רחוק", limit=5)
    assert ids == []


def test_relative_gate_trims_the_co_hyponym_tail(fake_vectors):
    idx = ss.build_index(_rows())
    # "גור": dog ~.94, pup ~.52. floor = max(MIN, 0.72*.94) ~ .68 -> pup trimmed.
    ids, _ = _ids(idx, "גור", limit=5)
    assert "dog" in ids
    assert "pup" not in ids


def test_symbol_without_a_vector_is_still_lexical(fake_vectors):
    # "cat" is in the rows but not in meta["ids"] -> zero matrix row
    idx = ss.build_index(_rows())
    ids, _ = _ids(idx, "חתול", limit=5)
    assert ids == ["cat"]  # tier 0 lexical; never a semantic hit (its vector is 0)
    cat_i = next(i for i, r in enumerate(idx.rows) if r["id"] == "cat")
    assert float(np.linalg.norm(idx.matrix[cat_i])) == 0.0


def test_schema_mismatch_disables_vectors(fake_vectors):
    (fake_vectors / "meta.json").write_text(
        json.dumps(
            {"schema": 99, "dim": D, "ids": list(SYMBOLS), "mean": [0.0] * D, "pc": [0.0] * D}
        ),
        encoding="utf-8",
    )
    ss.reset_cache()
    assert ss._vectors() is None
