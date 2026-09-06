"""schedule_templates — starter daily routines (bundled + caregiver-saved),
and applying one to a child's day (seeds schedule_items, pre-generates TTS).

Bundled rows have ``caregiver_id`` NULL; a caregiver's saved rows carry their
id. RLS ("global OR mine", migration 0019) is the boundary, so every read here
goes through the caller's client — no service role.
"""

from __future__ import annotations

from typing import Any

from app.repositories import schedule as schedule_repo
from app.repositories._base import one_or_none, rows
from app.services.tts import cache as tts_cache

_TABLE = "schedule_templates"


def _shape(row: dict) -> dict:
    """Public shape for the list endpoint — hides the raw caregiver_id."""
    return {
        "id": row["id"],
        "name_he": row["name_he"],
        "description_he": row.get("description_he"),
        "owned": row.get("caregiver_id") is not None,
    }


def list_templates(db: Any) -> list[dict]:
    """Bundled templates first (by sort_order), then the caregiver's own
    (newest first). RLS already limits the rows to bundled + mine."""
    got = rows(
        db.table(_TABLE)
        .select("id, name_he, description_he, sort_order, caregiver_id, created_at")
        .execute()
    )
    bundled = sorted(
        (r for r in got if r.get("caregiver_id") is None), key=lambda r: r["sort_order"]
    )
    mine = sorted(
        (r for r in got if r.get("caregiver_id") is not None),
        key=lambda r: r["created_at"],
        reverse=True,
    )
    return [_shape(r) for r in (*bundled, *mine)]


def get(db: Any, template_id: str) -> dict | None:
    return one_or_none(db.table(_TABLE).select("*").eq("id", template_id).execute())


def count_owned(db: Any, caregiver_id: str) -> int:
    return len(rows(db.table(_TABLE).select("id").eq("caregiver_id", caregiver_id).execute()))


def create_from_day(db: Any, caregiver_id: str, name_he: str, child_id: str, the_date: str) -> dict:
    """Snapshot a child's day into a new caregiver-owned template. Uploaded
    per-child icons (icon_asset_id) are dropped — only bundled symbols carry."""
    tasks = [
        {
            "title": it["title"],
            "start_time": it["start_time"][:5] if it["start_time"] else None,
            "symbol_id": it["symbol_id"],
        }
        for it in schedule_repo.list_day(db, child_id, the_date)
    ]
    return one_or_none(
        db.table(_TABLE)
        .insert(
            {
                "name_he": name_he,
                "caregiver_id": caregiver_id,
                "sort_order": 0,
                "spec": {"tasks": tasks},
            }
        )
        .execute()
    )


def delete_template(db: Any, template_id: str) -> None:
    db.table(_TABLE).delete().eq("id", template_id).execute()


def apply_to_child(db: Any, child_id: str, template_id: str, the_date: str) -> list[dict]:
    """Seed the child's day from a template. Appends after any tasks already on
    that date; never overwrites. Best-effort TTS pre-generation."""
    tpl = get(db, template_id)
    if not tpl:
        return []
    spec = tpl.get("spec") or {}
    base = len(schedule_repo.list_day(db, child_id, the_date))
    created: list[dict] = []
    for i, task in enumerate(spec.get("tasks", [])):
        values = {
            "the_date": the_date,
            "title": task["title"],
            "start_time": task.get("start_time"),
            "symbol_id": task.get("symbol_id"),
            "icon_asset_id": None,
            "sort_order": base + i,
            "tts_asset_id": tts_cache.ensure_tts_asset(task["title"]),
        }
        created.append(schedule_repo.create_item(db, child_id, values))
    return created
