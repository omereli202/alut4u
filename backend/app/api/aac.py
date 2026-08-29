"""AAC board — categories and cards.

Reads (the board) are allowed in User Mode; the child's device needs them.
All writes require Caregiver Mode. Tenancy is RLS: an id that isn't the
caregiver's simply isn't found → 404.

When a card's spoken text changes and it has no caregiver-supplied audio, its
TTS audio is (re)generated on save so tap-to-speak works offline.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import aac as repo
from app.repositories import children as children_repo
from app.repositories import symbols as symbols_repo
from app.schemas.aac import (
    CardCreate,
    CardUpdate,
    CategoryCreate,
    CategoryUpdate,
    ReorderRequest,
)
from app.services.tts import cache as tts_cache

bp = Blueprint("aac", __name__, url_prefix="/api/aac")


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _card_out(row: dict) -> dict:
    return {**row, "created_at": str(row.get("created_at"))}


# --- board (one call) ------------------------------------------------------


@bp.get("/board")
@require_session
def board():
    child_id = _require_arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(
        categories=repo.list_categories(g.db, child_id),
        cards=[_card_out(c) for c in repo.list_cards(g.db, child_id)],
    )


# --- categories ----------------------------------------------------------


@bp.post("/categories")
@require_caregiver_mode
def create_category():
    data = parse_body(CategoryCreate)
    _own_child_or_404(data.child_id)
    existing = repo.list_categories(g.db, data.child_id)
    row = repo.create_category(
        g.db, data.child_id, name=data.name, color=data.color, sort_order=len(existing)
    )
    return jsonify(row), 201


@bp.patch("/categories/<category_id>")
@require_caregiver_mode
def update_category(category_id: str):
    if repo.get_category(g.db, category_id) is None:
        raise ApiError(404, "not_found")
    data = parse_body(CategoryUpdate)
    row = repo.update_category(g.db, category_id, data.model_dump(exclude_none=True))
    return jsonify(row)


@bp.delete("/categories/<category_id>")
@require_caregiver_mode
def delete_category(category_id: str):
    if repo.get_category(g.db, category_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_category(g.db, category_id)
    return "", 204


@bp.put("/categories/order")
@require_caregiver_mode
def reorder_categories():
    data = parse_body(ReorderRequest)
    _own_child_or_404(data.child_id)
    repo.set_orders(g.db, repo.CATS_TABLE, {cid: i for i, cid in enumerate(data.order)})
    return "", 204


# --- cards --------------------------------------------------------------


@bp.post("/cards")
@require_caregiver_mode
def create_card():
    data = parse_body(CardCreate)
    _own_child_or_404(data.child_id)
    _validate_symbol(data.symbol_id)

    tts_text = (data.tts_text or data.label).strip()
    values = {
        "category_id": data.category_id,
        "label": data.label,
        "tts_text": tts_text,
        "symbol_id": data.symbol_id,
        "icon_asset_id": data.icon_asset_id,
        "grid_order": data.grid_order,
        "tts_asset_id": tts_cache.ensure_tts_asset(tts_text),
    }
    row = repo.create_card(g.db, data.child_id, values)
    return jsonify(_card_out(row)), 201


@bp.get("/cards/<card_id>")
@require_session
def get_card(card_id: str):
    row = repo.get_card(g.db, card_id)
    if row is None:
        raise ApiError(404, "not_found")
    return jsonify(_card_out(row))


@bp.patch("/cards/<card_id>")
@require_caregiver_mode
def update_card(card_id: str):
    current = repo.get_card(g.db, card_id)
    if current is None:
        raise ApiError(404, "not_found")
    data = parse_body(CardUpdate)
    _validate_symbol(data.symbol_id)

    patch = data.model_dump(exclude_unset=True)
    values = {
        k: patch[k]
        for k in patch
        if k
        in {
            "label",
            "tts_text",
            "category_id",
            "symbol_id",
            "icon_asset_id",
            "audio_asset_id",
            "grid_order",
        }
    }

    # Regenerate TTS if the spoken text changed and there is no caregiver audio.
    new_label = values.get("label", current["label"])
    new_tts = values.get("tts_text") or new_label
    audio = values.get("audio_asset_id", current["audio_asset_id"])
    text_changed = "label" in values or "tts_text" in values
    if text_changed and not audio:
        values["tts_text"] = new_tts.strip()
        values["tts_asset_id"] = tts_cache.ensure_tts_asset(values["tts_text"])

    row = repo.update_card(g.db, card_id, values)
    return jsonify(_card_out(row))


@bp.delete("/cards/<card_id>")
@require_caregiver_mode
def delete_card(card_id: str):
    if repo.get_card(g.db, card_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_card(g.db, card_id)
    return "", 204


@bp.put("/cards/order")
@require_caregiver_mode
def reorder_cards():
    data = parse_body(ReorderRequest)
    _own_child_or_404(data.child_id)
    repo.set_orders(g.db, repo.CARDS_TABLE, {cid: i for i, cid in enumerate(data.order)})
    return "", 204


# --- helpers ------------------------------------------------------------


def _require_arg(name: str) -> str:
    from flask import request

    v = request.args.get(name)
    if not v:
        raise ApiError(422, "missing_param", name)
    return v


def _validate_symbol(symbol_id: str | None) -> None:
    if symbol_id and not symbols_repo.exists(symbol_id):
        raise ApiError(422, "unknown_symbol", symbol_id)
