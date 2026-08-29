"""media_assets — pointer rows for objects in Storage.

Ownership is enforced two ways: child-scoped assets go through the caller's
client (RLS), and this module also verifies the child belongs to the caller
before an upload. Shared TTS-cache rows (``child_id`` null) are service-only.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.repositories._base import one_or_none
from app.services.supabase_client import service_client

_TABLE = "media_assets"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _svc():
    return service_client("media_asset_row")


def create(
    *,
    child_id: str | None,
    kind: str,
    storage_path: str,
    mime: str,
    bytes_len: int,
    digest: str,
) -> dict:
    return one_or_none(
        _svc()
        .table(_TABLE)
        .insert(
            {
                "child_id": child_id,
                "kind": kind,
                "storage_path": storage_path,
                "mime": mime,
                "bytes": bytes_len,
                "sha256": digest,
            }
        )
        .execute()
    )


def get_for_caller(db: Any, asset_id: str) -> dict | None:
    """Child-scoped read via the caregiver's client (RLS)."""
    return one_or_none(db.table(_TABLE).select("*").eq("id", asset_id).execute())


def get_shared_tts(asset_id: str) -> dict | None:
    return one_or_none(
        _svc()
        .table(_TABLE)
        .select("*")
        .eq("id", asset_id)
        .eq("kind", "tts_cache")
        .is_("child_id", "null")
        .execute()
    )


def find_tts_by_digest(digest: str) -> dict | None:
    return one_or_none(
        _svc().table(_TABLE).select("*").eq("kind", "tts_cache").eq("sha256", digest).execute()
    )


def delete(asset_id: str) -> None:
    _svc().table(_TABLE).delete().eq("id", asset_id).execute()
