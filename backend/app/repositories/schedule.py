"""schedule_items + calendar_events. Via the caller's client (RLS)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.repositories._base import one_or_none, rows

_ITEMS = "schedule_items"
_EVENTS = "calendar_events"

_ITEM_FIELDS = (
    "id, child_id, the_date, title, start_time, symbol_id, icon_asset_id, "
    "tts_asset_id, sort_order, is_completed, completed_at, created_at"
)
_EVENT_FIELDS = "id, child_id, event_date, title, note, symbol_id, icon_asset_id, created_at"


# --- schedule items -------------------------------------------------------


def list_day(db: Any, child_id: str, the_date: str) -> list[dict]:
    return rows(
        db.table(_ITEMS)
        .select(_ITEM_FIELDS)
        .eq("child_id", child_id)
        .eq("the_date", the_date)
        .order("sort_order")
        .order("start_time")
        .execute()
    )


def get_item(db: Any, item_id: str) -> dict | None:
    return one_or_none(db.table(_ITEMS).select(_ITEM_FIELDS).eq("id", item_id).execute())


def create_item(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_ITEMS).insert({"child_id": child_id, **values}).execute())


def update_item(db: Any, item_id: str, values: dict) -> dict | None:
    if not values:
        return get_item(db, item_id)
    return one_or_none(db.table(_ITEMS).update(values).eq("id", item_id).execute())


def delete_item(db: Any, item_id: str) -> None:
    db.table(_ITEMS).delete().eq("id", item_id).execute()


def set_item_orders(db: Any, id_to_order: dict[str, int]) -> None:
    for item_id, order in id_to_order.items():
        db.table(_ITEMS).update({"sort_order": order}).eq("id", item_id).execute()


def set_completed(db: Any, item_id: str, completed: bool) -> dict | None:
    patch = {"is_completed": completed}
    patch["completed_at"] = datetime.now(UTC).isoformat() if completed else None
    return one_or_none(db.table(_ITEMS).update(patch).eq("id", item_id).execute())


def copy_day(db: Any, child_id: str, from_date: str, to_date: str) -> int:
    src = list_day(db, child_id, from_date)
    if not src:
        return 0
    payload = [
        {
            "child_id": child_id,
            "the_date": to_date,
            "title": it["title"],
            "start_time": it["start_time"],
            "symbol_id": it["symbol_id"],
            "icon_asset_id": it["icon_asset_id"],
            "tts_asset_id": it["tts_asset_id"],
            "sort_order": it["sort_order"],
        }
        for it in src
    ]
    db.table(_ITEMS).insert(payload).execute()
    return len(payload)


# --- calendar events -----------------------------------------------------


def list_events(db: Any, child_id: str, from_date: str, to_date: str) -> list[dict]:
    return rows(
        db.table(_EVENTS)
        .select(_EVENT_FIELDS)
        .eq("child_id", child_id)
        .gte("event_date", from_date)
        .lte("event_date", to_date)
        .order("event_date")
        .execute()
    )


def get_event(db: Any, event_id: str) -> dict | None:
    return one_or_none(db.table(_EVENTS).select(_EVENT_FIELDS).eq("id", event_id).execute())


def create_event(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_EVENTS).insert({"child_id": child_id, **values}).execute())


def update_event(db: Any, event_id: str, values: dict) -> dict | None:
    if not values:
        return get_event(db, event_id)
    return one_or_none(db.table(_EVENTS).update(values).eq("id", event_id).execute())


def delete_event(db: Any, event_id: str) -> None:
    db.table(_EVENTS).delete().eq("id", event_id).execute()
