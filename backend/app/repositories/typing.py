"""typing_notes + typing_settings access.

Free-composition notes for a child who types. All access is through the
caller's RLS-scoped client — a note is visible only through
``children.caregiver_id = auth.uid()``.

The note ``id`` is chosen by the client (the offline outbox is POST-only and
returns nothing), so a caregiver could POST an id that already belongs to
another tenant's child. RLS hides that row from the caller, so the insert path
hits a raw primary-key conflict — caught here and surfaced as
:class:`NoteIdConflict` for the API layer to turn into a 409.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgrest.exceptions import APIError

from app.repositories._base import one_or_none, rows

_NOTES = "typing_notes"
_SETTINGS = "typing_settings"

_DEFAULT_SETTINGS = {"font_family": "rubik", "font_scale": "md"}

_LIST_COLS = "id, title, blocks, rev, font_family, font_scale, updated_at"
_FULL_COLS = (
    "id, child_id, title, blocks, rev, font_family, font_scale, "
    "tts_asset_id, tts_text_hash, created_at, updated_at"
)


class NoteIdConflict(Exception):
    """The client-supplied note id already exists under a different owner."""


# --- notes ----------------------------------------------------------------


def list_notes(db: Any, child_id: str) -> list[dict]:
    return rows(
        db.table(_NOTES)
        .select(_LIST_COLS)
        .eq("child_id", child_id)
        .order("updated_at", desc=True)
        .execute()
    )


def get_note(db: Any, note_id: str) -> dict | None:
    return one_or_none(db.table(_NOTES).select(_FULL_COLS).eq("id", note_id).execute())


def upsert_note(db: Any, child_id: str, created_by: str, values: dict) -> dict:
    """Insert or replace the note. Rev-gated: a save whose ``rev`` is behind the
    stored row is ignored and the stored row is returned, so a stale outbox
    replay drains the queue instead of jamming it."""
    note_id = values["note_id"]
    existing = get_note(db, note_id)

    if existing is not None:
        if values["rev"] < existing["rev"]:
            return existing
        updated = one_or_none(
            db.table(_NOTES)
            .update(
                {
                    "title": values["title"],
                    "blocks": values["blocks"],
                    "rev": values["rev"],
                    "font_family": values["font_family"],
                    "font_scale": values["font_scale"],
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", note_id)
            .execute()
        )
        return updated or existing

    try:
        return one_or_none(
            db.table(_NOTES)
            .insert(
                {
                    "id": note_id,
                    "child_id": child_id,
                    "created_by": created_by,
                    "title": values["title"],
                    "blocks": values["blocks"],
                    "rev": values["rev"],
                    "font_family": values["font_family"],
                    "font_scale": values["font_scale"],
                }
            )
            .execute()
        )
    except APIError as e:
        if e.code == "23505":  # unique_violation — the id exists for another tenant
            raise NoteIdConflict from e
        raise


def delete_note(db: Any, note_id: str) -> None:
    db.table(_NOTES).delete().eq("id", note_id).execute()


def set_tts(db: Any, note_id: str, asset_id: str, text_hash: str) -> None:
    db.table(_NOTES).update({"tts_asset_id": asset_id, "tts_text_hash": text_hash}).eq(
        "id", note_id
    ).execute()


# --- settings -----------------------------------------------------------


def get_settings(db: Any, child_id: str) -> dict:
    row = one_or_none(
        db.table(_SETTINGS)
        .select("child_id, font_family, font_scale")
        .eq("child_id", child_id)
        .execute()
    )
    return row or {"child_id": child_id, **_DEFAULT_SETTINGS}


def upsert_settings(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(
        db.table(_SETTINGS)
        .upsert(
            {"child_id": child_id, "updated_at": datetime.now(UTC).isoformat(), **values},
            on_conflict="child_id",
        )
        .execute()
    )
