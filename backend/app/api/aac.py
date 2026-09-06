"""AAC board — categories and cards.

Reads (the board) are allowed in User Mode; the child's device needs them.
All writes require Caregiver Mode. Tenancy is RLS: an id that isn't the
caregiver's simply isn't found → 404.

When a card's spoken text changes and it has no caregiver-supplied audio, its
TTS audio is (re)generated on save so tap-to-speak works offline.
"""

from __future__ import annotations

from collections import defaultdict

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


# Categories nest (אוכל ‹ ארוחת בוקר ‹ ביצת עין), capped so the child's
# drill-down never gets deeper than this. Root categories are level 1.
_MAX_CATEGORY_DEPTH = 4


def _cat_depth(by_id: dict[str, dict], cat_id: str | None) -> int:
    """1 for a root category, +1 per ancestor. `by_id` is the child's full flat
    category list keyed by id."""
    depth = 0
    seen: set[str] = set()
    while cat_id and cat_id in by_id and cat_id not in seen:
        seen.add(cat_id)
        depth += 1
        cat_id = by_id[cat_id].get("parent_id")
    return max(depth, 1)


def _subtree_height(children_of: dict[str, list[str]], cat_id: str) -> int:
    """Levels from `cat_id` down to its deepest descendant, inclusive (1 = leaf)."""
    kids = children_of.get(cat_id, ())
    if not kids:
        return 1
    return 1 + max(_subtree_height(children_of, k) for k in kids)


def _is_ancestor(by_id: dict[str, dict], ancestor_id: str, node_id: str | None) -> bool:
    seen: set[str] = set()
    while node_id and node_id not in seen:
        if node_id == ancestor_id:
            return True
        seen.add(node_id)
        node_id = by_id.get(node_id, {}).get("parent_id")
    return False


@bp.post("/categories")
@require_caregiver_mode
def create_category():
    data = parse_body(CategoryCreate)
    _own_child_or_404(data.child_id)
    _validate_symbol(data.symbol_id)

    existing = repo.list_categories(g.db, data.child_id)
    parent_id = data.parent_id or None
    if parent_id is not None:
        by_id = {c["id"]: c for c in existing}
        if parent_id not in by_id:
            raise ApiError(422, "bad_parent")
        if _cat_depth(by_id, parent_id) + 1 > _MAX_CATEGORY_DEPTH:
            raise ApiError(422, "too_deep")

    siblings = [c for c in existing if (c.get("parent_id") or None) == parent_id]
    row = repo.create_category(
        g.db,
        data.child_id,
        name=data.name,
        color=data.color,
        sort_order=len(siblings),
        parent_id=parent_id,
        symbol_id=data.symbol_id,
        icon_asset_id=data.icon_asset_id,
    )
    return jsonify(row), 201


@bp.patch("/categories/<category_id>")
@require_caregiver_mode
def update_category(category_id: str):
    current = repo.get_category(g.db, category_id)
    if current is None:
        raise ApiError(404, "not_found")
    data = parse_body(CategoryUpdate)
    _validate_symbol(data.symbol_id)

    patch = data.model_dump(exclude_unset=True)
    if "parent_id" in patch:
        new_parent = patch["parent_id"] or None
        cats = repo.list_categories(g.db, current["child_id"])
        by_id = {c["id"]: c for c in cats}
        if new_parent is not None:
            if new_parent == category_id or new_parent not in by_id:
                raise ApiError(422, "bad_parent")
            if _is_ancestor(by_id, category_id, new_parent):
                raise ApiError(422, "category_cycle")
            children_of: dict[str, list[str]] = defaultdict(list)
            for c in cats:
                if c.get("parent_id"):
                    children_of[c["parent_id"]].append(c["id"])
            if _cat_depth(by_id, new_parent) + _subtree_height(children_of, category_id) > (
                _MAX_CATEGORY_DEPTH
            ):
                raise ApiError(422, "too_deep")
        patch["parent_id"] = new_parent

    row = repo.update_category(g.db, category_id, patch)
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
