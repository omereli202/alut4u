"""aac_categories + aac_cards. Always via the caller's client — RLS scopes to
the caregiver's children. The API layer verifies child ownership before calling.
"""

from __future__ import annotations

from typing import Any

from app.repositories._base import one_or_none, rows

_CATS = "aac_categories"
_CARDS = "aac_cards"

_CARD_FIELDS = (
    "id, child_id, category_id, label, tts_text, symbol_id, icon_asset_id, "
    "audio_asset_id, tts_asset_id, grid_order, created_at"
)


# --- categories ------------------------------------------------------------


def list_categories(db: Any, child_id: str) -> list[dict]:
    return rows(db.table(_CATS).select("*").eq("child_id", child_id).order("sort_order").execute())


def create_category(
    db: Any, child_id: str, *, name: str, color: str | None, sort_order: int
) -> dict:
    return one_or_none(
        db.table(_CATS)
        .insert({"child_id": child_id, "name": name, "color": color, "sort_order": sort_order})
        .execute()
    )


def update_category(db: Any, category_id: str, patch: dict) -> dict | None:
    allowed = {k: v for k, v in patch.items() if k in {"name", "color", "sort_order"}}
    if not allowed:
        return one_or_none(db.table(_CATS).select("*").eq("id", category_id).execute())
    return one_or_none(db.table(_CATS).update(allowed).eq("id", category_id).execute())


def delete_category(db: Any, category_id: str) -> None:
    db.table(_CATS).delete().eq("id", category_id).execute()


def get_category(db: Any, category_id: str) -> dict | None:
    return one_or_none(db.table(_CATS).select("*").eq("id", category_id).execute())


# --- cards ----------------------------------------------------------------


def list_cards(db: Any, child_id: str, *, category_id: str | None = None) -> list[dict]:
    q = db.table(_CARDS).select(_CARD_FIELDS).eq("child_id", child_id)
    if category_id is not None:
        q = q.eq("category_id", category_id)
    return rows(q.order("grid_order").execute())


def get_card(db: Any, card_id: str) -> dict | None:
    return one_or_none(db.table(_CARDS).select(_CARD_FIELDS).eq("id", card_id).execute())


def create_card(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_CARDS).insert({"child_id": child_id, **values}).execute())


def update_card(db: Any, card_id: str, values: dict) -> dict | None:
    if not values:
        return get_card(db, card_id)
    return one_or_none(db.table(_CARDS).update(values).eq("id", card_id).execute())


def delete_card(db: Any, card_id: str) -> None:
    db.table(_CARDS).delete().eq("id", card_id).execute()


def set_orders(db: Any, table: str, id_to_order: dict[str, int]) -> None:
    """Persist a new ordering. One UPDATE per row — fine for board-sized lists."""
    for row_id, order in id_to_order.items():
        db.table(table).update({"grid_order" if table == _CARDS else "sort_order": order}).eq(
            "id", row_id
        ).execute()


CARDS_TABLE = _CARDS
CATS_TABLE = _CATS
