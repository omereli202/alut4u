"""children + module_settings access. Always via the caller's client — RLS
(``caregiver_id = auth.uid()``) is the tenancy boundary. Never accept a
caller-supplied ``caregiver_id``.
"""

from __future__ import annotations

from typing import Any

from app.repositories._base import one_or_none, rows

_CHILDREN = "children"
_MODULES = "module_settings"

_MODULE_KEYS = (
    "aac_enabled",
    "schedule_enabled",
    "rules_enabled",
    "calming_enabled",
    "social_stories_enabled",
    "reading_writing_enabled",
)


def list_children(db: Any, *, include_inactive: bool = False) -> list[dict]:
    q = db.table(_CHILDREN).select("*").order("created_at")
    if not include_inactive:
        q = q.eq("is_active", True)
    return rows(q.execute())


def get_child(db: Any, child_id: str) -> dict | None:
    return one_or_none(db.table(_CHILDREN).select("*").eq("id", child_id).execute())


def create_child(
    db: Any,
    *,
    caregiver_id: str,
    name: str,
    birth_date: str | None,
    avatar_seed: str | None,
    consent_basis: str,
) -> dict:
    resp = (
        db.table(_CHILDREN)
        .insert(
            {
                "caregiver_id": caregiver_id,
                "name": name,
                "birth_date": birth_date,
                "avatar_seed": avatar_seed,
                "consent_basis": consent_basis,
            }
        )
        .execute()
    )
    return one_or_none(resp)


def update_child(db: Any, child_id: str, patch: dict) -> dict | None:
    allowed = {k: v for k, v in patch.items() if k in {"name", "birth_date", "avatar_seed"}}
    if not allowed:
        return get_child(db, child_id)
    return one_or_none(db.table(_CHILDREN).update(allowed).eq("id", child_id).execute())


def deactivate_child(db: Any, child_id: str) -> None:
    db.table(_CHILDREN).update({"is_active": False}).eq("id", child_id).execute()


# --- module_settings ---------------------------------------------------------


def get_modules(db: Any, child_id: str) -> dict | None:
    return one_or_none(db.table(_MODULES).select("*").eq("child_id", child_id).execute())


def update_modules(db: Any, child_id: str, patch: dict) -> dict | None:
    allowed = {k: bool(v) for k, v in patch.items() if k in _MODULE_KEYS}
    if not allowed:
        return get_modules(db, child_id)
    return one_or_none(db.table(_MODULES).update(allowed).eq("child_id", child_id).execute())
