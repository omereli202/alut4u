"""social_stories rows + their page-illustration assets."""

from __future__ import annotations

from typing import Any

from app.repositories import media as media_repo
from app.repositories._base import one_or_none, rows
from app.services import storage

_TABLE = "social_stories"
_FIELDS = "id, child_id, title, protagonist, situation, goal, pages, created_at"


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
        .select("id, title, created_at")
        .eq("child_id", child_id)
        .order("created_at", desc=True)
        .execute()
    )


def get_story(db: Any, story_id: str) -> dict | None:
    return one_or_none(db.table(_TABLE).select(_FIELDS).eq("id", story_id).execute())


def delete_story(db: Any, story_id: str) -> None:
    db.table(_TABLE).delete().eq("id", story_id).execute()
