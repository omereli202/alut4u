"""paintings + painting_pages access ("בוא נצייר").

All access is through the caller's RLS-scoped client — a painting is visible
only through ``children.caregiver_id = auth.uid()``.

``paintings.id`` is chosen by the client (the offline outbox is POST-only and
returns nothing), so a caregiver could POST an id that already belongs to
another tenant's child. RLS hides that row, so the insert hits a raw
primary-key conflict — caught here and surfaced as :class:`PaintingIdConflict`
for the API layer to turn into a 409. Same contract as typing_notes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from postgrest.exceptions import APIError

from app.repositories._base import one_or_none, rows

_PAINTINGS = "paintings"
_PAGES = "painting_pages"

# The list route must stay cheap: a gallery of 40 paintings should not pull
# every stroke. Full strokes/fills come only from the detail route.
_LIST_COLS = "id, title, page, rev, created_at, updated_at"
_FULL_COLS = "id, child_id, title, page, strokes, fills, rev, created_at, updated_at"


class PaintingIdConflict(Exception):
    """The client-supplied painting id already exists under a different owner."""


# --- paintings ----------------------------------------------------------


def list_paintings(db: Any, child_id: str) -> list[dict]:
    return rows(
        db.table(_PAINTINGS)
        .select(_LIST_COLS)
        .eq("child_id", child_id)
        .order("updated_at", desc=True)
        .execute()
    )


def get_painting(db: Any, painting_id: str) -> dict | None:
    return one_or_none(db.table(_PAINTINGS).select(_FULL_COLS).eq("id", painting_id).execute())


def upsert_painting(db: Any, child_id: str, created_by: str, values: dict) -> dict:
    """Insert or replace. Rev-gated: a save whose ``rev`` is behind the stored
    row is ignored and the stored row returned, so a stale outbox replay drains
    the queue instead of jamming it."""
    painting_id = values["painting_id"]
    existing = get_painting(db, painting_id)

    if existing is not None:
        if values["rev"] < existing["rev"]:
            return existing
        updated = one_or_none(
            db.table(_PAINTINGS)
            .update(
                {
                    "title": values["title"],
                    "page": values["page"],
                    "strokes": values["strokes"],
                    "fills": values["fills"],
                    "rev": values["rev"],
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", painting_id)
            .execute()
        )
        return updated or existing

    try:
        return one_or_none(
            db.table(_PAINTINGS)
            .insert(
                {
                    "id": painting_id,
                    "child_id": child_id,
                    "created_by": created_by,
                    "title": values["title"],
                    "page": values["page"],
                    "strokes": values["strokes"],
                    "fills": values["fills"],
                    "rev": values["rev"],
                }
            )
            .execute()
        )
    except APIError as e:
        if e.code == "23505":  # unique_violation — the id exists for another tenant
            raise PaintingIdConflict from e
        raise


def delete_painting(db: Any, painting_id: str) -> None:
    db.table(_PAINTINGS).delete().eq("id", painting_id).execute()


# --- caregiver-curated colouring pages ---------------------------------


def list_pages(db: Any, child_id: str) -> list[dict]:
    return rows(
        db.table(_PAGES)
        .select("symbol_id, sort_order")
        .eq("child_id", child_id)
        .order("sort_order")
        .execute()
    )


def set_pages(db: Any, child_id: str, symbol_ids: list[str]) -> list[dict]:
    """Replace the child's extra colouring pages. Delete-then-insert keeps
    sort_order = list index without a diff (precedent: schedule reorder)."""
    db.table(_PAGES).delete().eq("child_id", child_id).execute()
    if symbol_ids:
        db.table(_PAGES).insert(
            [
                {"child_id": child_id, "symbol_id": sid, "sort_order": i}
                for i, sid in enumerate(symbol_ids)
            ]
        ).execute()
    return list_pages(db, child_id)
