"""social_stories rows + their page-illustration assets."""

from __future__ import annotations

from typing import Any

from app.repositories import media as media_repo
from app.repositories._base import one_or_none, rows
from app.services import storage

_TABLE = "social_stories"
_FIELDS = (
    "id, child_id, title, protagonist, situation, schedule, goal, pages, "
    "character_sheet, review_notes, created_at"
)


def store_page_image(child_id: str, data: bytes, mime: str) -> str:
    digest = media_repo.sha256(data)
    ext = "svg" if "svg" in mime else ("png" if "png" in mime else "jpg")
    path = f"{child_id}/{digest}.{ext}"
    storage.upload(storage.MEDIA_BUCKET, path, data, mime)
    row = media_repo.create(
        child_id=child_id,
        kind="story_image",
        storage_path=f"{storage.MEDIA_BUCKET}/{path}",
        mime=mime,
        bytes_len=len(data),
        digest=digest,
    )
    return row["id"]


def create_story(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_TABLE).insert({"child_id": child_id, **values}).execute())


def list_stories(db: Any, child_id: str) -> list[dict]:
    return rows(
        db.table(_TABLE)
        .select("id, title, pages, created_at")
        .eq("child_id", child_id)
        .order("created_at", desc=True)
        .execute()
    )


def get_story(db: Any, story_id: str) -> dict | None:
    return one_or_none(db.table(_TABLE).select(_FIELDS).eq("id", story_id).execute())


def set_page_image(db: Any, story_id: str, page_index: int, asset_id: str) -> dict | None:
    """Attach an illustration to one page. Returns the updated row, or None if
    the story is gone / not visible or that page already has art (lost race)."""
    row = get_story(db, story_id)
    if row is None:
        return None
    pages = list(row["pages"])
    if page_index >= len(pages) or pages[page_index].get("image_asset_id"):
        return None
    pages[page_index] = {**pages[page_index], "image_asset_id": asset_id}
    return one_or_none(db.table(_TABLE).update({"pages": pages}).eq("id", story_id).execute())


def update_story_text(
    db: Any, story_id: str, *, title: str | None, pages: list[dict]
) -> dict | None:
    """Rewrite the page texts (and TTS ids) and optionally the title. Images and
    every other field are left untouched."""
    values: dict = {"pages": pages}
    if title:
        values["title"] = title
    return one_or_none(db.table(_TABLE).update(values).eq("id", story_id).execute())


def delete_story(db: Any, story_id: str) -> None:
    db.table(_TABLE).delete().eq("id", story_id).execute()
