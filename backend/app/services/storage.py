"""Supabase Storage wrapper.

Both buckets (``media``, ``tts``) are private. Objects are only ever read through
the backend's ``/api/media/<id>`` route, which uses the service role here.
"""

from __future__ import annotations

from app.services.supabase_client import service_client

MEDIA_BUCKET = "media"
TTS_BUCKET = "tts"


def _bucket(name: str):
    return service_client("media_storage").storage.from_(name)


def upload(bucket: str, path: str, data: bytes, content_type: str) -> None:
    _bucket(bucket).upload(
        path,
        data,
        {"content-type": content_type, "cache-control": "31536000", "upsert": "true"},
    )


def download(bucket: str, path: str) -> bytes:
    return _bucket(bucket).download(path)


def remove(bucket: str, paths: list[str]) -> None:
    if paths:
        _bucket(bucket).remove(paths)
