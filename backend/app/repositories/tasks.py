"""task_items + task_settings ("המשימות שלי"). Via the caller's client (RLS)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.repositories._base import one_or_none, rows

_ITEMS = "task_items"
_SETTINGS = "task_settings"

_ITEM_FIELDS = (
    "id, child_id, title, symbol_id, tts_asset_id, recurrence, sort_order, completed_on, created_at"
)

_DEFAULT_SETTINGS = {"reward_tokens": 1, "last_reward_date": None}


# --- task items --------------------------------------------------------


def list_all(db: Any, child_id: str) -> list[dict]:
    return rows(
        db.table(_ITEMS).select(_ITEM_FIELDS).eq("child_id", child_id).order("sort_order").execute()
    )


def list_for_date(db: Any, child_id: str, the_date: str) -> list[dict]:
    """Tasks relevant to ``the_date``: recurring ones always; one-off ones only
    while unfinished or finished exactly on that date."""
    return [
        r
        for r in list_all(db, child_id)
        if r["recurrence"] == "daily" or r["completed_on"] is None or r["completed_on"] == the_date
    ]


def get_item(db: Any, task_id: str) -> dict | None:
    return one_or_none(db.table(_ITEMS).select(_ITEM_FIELDS).eq("id", task_id).execute())


def create_item(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_ITEMS).insert({"child_id": child_id, **values}).execute())


def update_item(db: Any, task_id: str, values: dict) -> dict | None:
    if not values:
        return get_item(db, task_id)
    return one_or_none(db.table(_ITEMS).update(values).eq("id", task_id).execute())


def delete_item(db: Any, task_id: str) -> None:
    db.table(_ITEMS).delete().eq("id", task_id).execute()


def set_item_orders(db: Any, id_to_order: dict[str, int]) -> None:
    for task_id, order in id_to_order.items():
        db.table(_ITEMS).update({"sort_order": order}).eq("id", task_id).execute()


def set_completed_on(db: Any, task_id: str, the_date: str | None) -> dict | None:
    return one_or_none(
        db.table(_ITEMS).update({"completed_on": the_date}).eq("id", task_id).execute()
    )


# --- task settings ----------------------------------------------------


def get_settings(db: Any, child_id: str) -> dict:
    """The child's task settings, or the default when no row exists yet."""
    row = one_or_none(
        db.table(_SETTINGS)
        .select("child_id, reward_tokens, last_reward_date")
        .eq("child_id", child_id)
        .execute()
    )
    return row or {"child_id": child_id, **_DEFAULT_SETTINGS}


def upsert_settings(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(
        db.table(_SETTINGS)
        .upsert(
            {
                "child_id": child_id,
                "updated_at": datetime.now(UTC).isoformat(),
                **values,
            }
        )
        .execute()
    )
