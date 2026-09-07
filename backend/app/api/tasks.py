"""המשימות שלי (My Tasks) — a personal checklist with a token reward.

Reads and the child's completion tick are allowed in User Mode; building the
list and releasing the reward require Caregiver Mode. Tenancy is RLS.

The reward is released like the rules daily bonus and the learning milestone:
the caregiver is present and enters their PIN, once per (child, local date).
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import tasks as repo
from app.repositories import tokens as tokens_repo
from app.schemas.tasks import (
    ClaimRequest,
    ReorderRequest,
    SettingsUpdate,
    TaskCreate,
    TaskUpdate,
    ToggleRequest,
)
from app.services.tts import cache as tts_cache

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

_REWARD_KIND = "tasks"
_REWARD_REASON = "סיום כל המשימות"


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
    return {k: (str(v) if k == "created_at" and v else v) for k, v in row.items()}


def _item_out(row: dict, the_date: str) -> dict:
    return {**_clean(row), "is_done": row["completed_on"] == the_date}


# --- the child's list -------------------------------------------------


@bp.get("/day")
@require_session
def get_day():
    child_id, the_date = _arg("child_id"), _arg("date")
    _own_child_or_404(child_id)
    items = [_item_out(i, the_date) for i in repo.list_for_date(g.db, child_id, the_date)]
    settings = repo.get_settings(g.db, child_id)
    return jsonify(
        items=items,
        reward_tokens=settings["reward_tokens"],
        reward_claimed=settings["last_reward_date"] == the_date,
        all_done=bool(items) and all(i["is_done"] for i in items),
    )


@bp.post("/toggle")
@require_session
def toggle():
    """Mark a task done / not done for a given local date. Allowed in User Mode;
    idempotent so the offline outbox can replay it safely."""
    data = parse_body(ToggleRequest)
    if repo.get_item(g.db, data.task_id) is None:
        raise ApiError(404, "not_found")
    the_date = data.the_date.isoformat()
    row = repo.set_completed_on(g.db, data.task_id, the_date if data.completed else None)
    return jsonify(_item_out(row, the_date))


# --- caregiver: build the list ---------------------------------------


@bp.get("/items")
@require_caregiver_mode
def list_items():
    """The full task list (including one-off tasks already finished on an
    earlier day, which the child's /day view hides) plus the reward setting."""
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    settings = repo.get_settings(g.db, child_id)
    return jsonify(
        items=[_clean(i) for i in repo.list_all(g.db, child_id)],
        reward_tokens=settings["reward_tokens"],
    )


@bp.post("/items")
@require_caregiver_mode
def create_item():
    data = parse_body(TaskCreate)
    _own_child_or_404(data.child_id)
    values = {
        "title": data.title,
        "symbol_id": data.symbol_id,
        "recurrence": data.recurrence,
        "sort_order": data.sort_order,
        "tts_asset_id": tts_cache.ensure_tts_asset(data.title),
    }
    return jsonify(_clean(repo.create_item(g.db, data.child_id, values))), 201


@bp.patch("/items/<task_id>")
@require_caregiver_mode
def update_item(task_id: str):
    current = repo.get_item(g.db, task_id)
    if current is None:
        raise ApiError(404, "not_found")
    data = parse_body(TaskUpdate)
    patch = data.model_dump(exclude_unset=True)
    values = {k: patch[k] for k in patch if k in {"title", "symbol_id", "recurrence", "sort_order"}}
    if "title" in values:
        values["tts_asset_id"] = tts_cache.ensure_tts_asset(values["title"])
    return jsonify(_clean(repo.update_item(g.db, task_id, values)))


@bp.delete("/items/<task_id>")
@require_caregiver_mode
def delete_item(task_id: str):
    if repo.get_item(g.db, task_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_item(g.db, task_id)
    return "", 204


@bp.put("/items/order")
@require_caregiver_mode
def reorder_items():
    data = parse_body(ReorderRequest)
    _own_child_or_404(data.child_id)
    repo.set_item_orders(g.db, {i: n for n, i in enumerate(data.order)})
    return "", 204


@bp.put("/settings")
@require_caregiver_mode
def update_settings():
    data = parse_body(SettingsUpdate)
    _own_child_or_404(data.child_id)
    row = repo.upsert_settings(g.db, data.child_id, {"reward_tokens": data.reward_tokens})
    return jsonify(reward_tokens=row["reward_tokens"])


# --- caregiver: release the reward (PIN) ----------------------------


@bp.post("/claim")
@require_caregiver_mode
def claim():
    data = parse_body(ClaimRequest)
    _own_child_or_404(data.child_id)
    the_date = data.the_date.isoformat()

    items = repo.list_for_date(g.db, data.child_id, the_date)
    if not items or any(i["completed_on"] != the_date for i in items):
        raise ApiError(409, "tasks_incomplete")

    settings = repo.get_settings(g.db, data.child_id)
    if settings["last_reward_date"] == the_date:
        raise ApiError(409, "reward_already_granted")

    amount = settings["reward_tokens"]
    if amount:
        tokens_repo.add_transaction(
            g.db,
            data.child_id,
            delta=amount,
            kind=_REWARD_KIND,
            reason=_REWARD_REASON,
            created_by=g.caregiver_id,
        )
    repo.upsert_settings(g.db, data.child_id, {"last_reward_date": the_date})
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="tasks.claim",
        target_type="child",
        target_id=data.child_id,
        detail={"date": the_date, "tokens": amount},
    )
    return jsonify(
        tokens_awarded=amount,
        balance=tokens_repo.balance(g.db, data.child_id),
    ), 201
