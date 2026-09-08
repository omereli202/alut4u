"""Painting cap + input-validation enforcement (pydantic, no Supabase needed)."""

from __future__ import annotations

import uuid

import pytest

from app.schemas.painting import MAX_STROKES, MAX_TOTAL_POINTS, PaintingUpsert


def _base(**over):
    b = {
        "child_id": "c",
        "painting_id": str(uuid.uuid4()),
        "page": {"kind": "blank"},
        "strokes": [{"c": "#000000", "w": 0.02, "e": 0, "p": [0.1, 0.1, 0.2, 0.2]}],
        "fills": [],
        "rev": 1,
    }
    b.update(over)
    return b


def test_ok_minimal():
    PaintingUpsert.model_validate(_base())


def test_too_many_strokes():
    stroke = {"c": "#000000", "w": 0.02, "e": 0, "p": [0.1, 0.1, 0.2, 0.2]}
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(_base(strokes=[stroke] * (MAX_STROKES + 1)))


def test_stroke_point_array_capped():
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(
            _base(strokes=[{"c": "#000000", "w": 0.02, "e": 0, "p": [0.5] * 2002}])
        )


def test_total_points_ceiling():
    # 100 strokes each just under the per-stroke cap -> over the 60k total
    big = {"c": "#000000", "w": 0.02, "e": 0, "p": [0.5] * 1998}
    n = (MAX_TOTAL_POINTS // 999) + 2
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(_base(strokes=[big] * n))


def test_bad_colour_rejected():
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(
            _base(strokes=[{"c": "javascript:x", "w": 0.02, "e": 0, "p": [0.1, 0.1, 0.2, 0.2]}])
        )


def test_odd_length_point_array():
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(
            _base(strokes=[{"c": "#000000", "w": 0.02, "e": 0, "p": [0.1, 0.1, 0.2]}])
        )


def test_coordinate_out_of_range():
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(
            _base(strokes=[{"c": "#000000", "w": 0.02, "e": 0, "p": [0.1, 0.1, 3.0, 0.2]}])
        )


def test_bad_region_key_rejected():
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(_base(fills=[{"r": "not a key", "c": "#000000"}]))


def test_symbol_page_needs_id():
    with pytest.raises(ValueError):
        PaintingUpsert.model_validate(_base(page={"kind": "symbol"}))
