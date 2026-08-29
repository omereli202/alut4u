"""Daily schedule + monthly calendar.

Reads and task completion are allowed in User Mode (the child uses the "where
are we now" view and ticks tasks off). Building the schedule and editing events
requires Caregiver Mode. Tenancy is RLS.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import children as children_repo
from app.repositories import schedule as repo
from app.schemas.schedule import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CopyDayRequest,
    ReorderRequest,
    ScheduleItemCreate,
    ScheduleItemUpdate,
    ToggleRequest,
)
from app.services.tts import cache as tts_cache

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _arg(name: str) -> str:
    v = request.args.get(name)
    if not v:
        raise ApiError(422, "missing_param", name)
    return v


def _clean(row: dict) -> dict:
    return {k: (str(v) if k in {"created_at", "completed_at"} and v else v) for k, v in row.items()}


# --- daily schedule -----------------------------------------------------


@bp.get("/day")
@require_session
def get_day():
    child_id, the_date = _arg("child_id"), _arg("date")
    _own_child_or_404(child_id)
    return jsonify(items=[_clean(i) for i in repo.list_day(g.db, child_id, the_date)])


@bp.post("/items")
@require_caregiver_mode
def create_item():
    data = parse_body(ScheduleItemCreate)
    _own_child_or_404(data.child_id)
    values = {
        "the_date": data.the_date.isoformat(),
        "title": data.title,
        "start_time": data.start_time,
        "symbol_id": data.symbol_id,
        "icon_asset_id": data.icon_asset_id,
        "sort_order": data.sort_order,
        "tts_asset_id": tts_cache.ensure_tts_asset(data.title),
    }
    return jsonify(_clean(repo.create_item(g.db, data.child_id, values))), 201


@bp.patch("/items/<item_id>")
@require_caregiver_mode
def update_item(item_id: str):
    current = repo.get_item(g.db, item_id)
    if current is None:
        raise ApiError(404, "not_found")
    data = parse_body(ScheduleItemUpdate)
    patch = data.model_dump(exclude_unset=True)
    values = {
        k: patch[k]
        for k in patch
        if k in {"title", "start_time", "symbol_id", "icon_asset_id", "sort_order"}
    }
    if "title" in values:
        values["tts_asset_id"] = tts_cache.ensure_tts_asset(values["title"])
    return jsonify(_clean(repo.update_item(g.db, item_id, values)))


@bp.delete("/items/<item_id>")
@require_caregiver_mode
def delete_item(item_id: str):
    if repo.get_item(g.db, item_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_item(g.db, item_id)
    return "", 204


@bp.put("/items/order")
@require_caregiver_mode
def reorder_items():
    data = parse_body(ReorderRequest)
    _own_child_or_404(data.child_id)
    repo.set_item_orders(g.db, {i: n for n, i in enumerate(data.order)})
    return "", 204


@bp.post("/toggle")
@require_session
def toggle():
    """Mark a task done / not done. Allowed in User Mode; idempotent so the
    offline outbox can replay it safely."""
    data = parse_body(ToggleRequest)
    if repo.get_item(g.db, data.item_id) is None:
        raise ApiError(404, "not_found")
    return jsonify(_clean(repo.set_completed(g.db, data.item_id, data.completed)))


@bp.post("/copy-day")
@require_caregiver_mode
def copy_day():
    data = parse_body(CopyDayRequest)
    _own_child_or_404(data.child_id)
    n = repo.copy_day(g.db, data.child_id, data.from_date.isoformat(), data.to_date.isoformat())
    return jsonify(copied=n)


# --- calendar ----------------------------------------------------------


@bp.get("/calendar")
@require_session
def calendar():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(
        events=[_clean(e) for e in repo.list_events(g.db, child_id, _arg("from"), _arg("to"))]
    )


@bp.post("/events")
@require_caregiver_mode
def create_event():
    data = parse_body(CalendarEventCreate)
    _own_child_or_404(data.child_id)
    values = {
        "event_date": data.event_date.isoformat(),
        "title": data.title,
        "note": data.note,
        "symbol_id": data.symbol_id,
        "icon_asset_id": data.icon_asset_id,
    }
    return jsonify(_clean(repo.create_event(g.db, data.child_id, values))), 201


@bp.patch("/events/<event_id>")
@require_caregiver_mode
def update_event(event_id: str):
    if repo.get_event(g.db, event_id) is None:
        raise ApiError(404, "not_found")
    data = parse_body(CalendarEventUpdate)
    patch = data.model_dump(exclude_unset=True)
    values = {k: patch[k] for k in patch if k in {"title", "note", "symbol_id", "icon_asset_id"}}
    if patch.get("event_date"):
        values["event_date"] = data.event_date.isoformat()
    return jsonify(_clean(repo.update_event(g.db, event_id, values)))


@bp.delete("/events/<event_id>")
@require_caregiver_mode
def delete_event(event_id: str):
    if repo.get_event(g.db, event_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_event(g.db, event_id)
    return "", 204
