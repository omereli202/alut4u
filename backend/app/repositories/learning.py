"""Graded reading/writing content + attempts."""

from __future__ import annotations

from typing import Any

from app.repositories._base import one_or_none, rows
from app.services.supabase_client import service_client

_READING = "reading_texts"
_WRITING = "writing_prompts"
_ATTEMPTS = "learning_attempts"


def _svc():
    return service_client("read_learning_content")


def list_reading(level: int | None = None) -> list[dict]:
    q = _svc().table(_READING).select("*").order("level").order("id")
    if level:
        q = q.eq("level", level)
    return rows(q.execute())


def get_reading(text_id: str) -> dict | None:
    return one_or_none(_svc().table(_READING).select("*").eq("id", text_id).execute())


def list_writing(level: int | None = None) -> list[dict]:
    q = _svc().table(_WRITING).select("id, level, hint").order("level").order("id")
    if level:
        q = q.eq("level", level)
    return rows(q.execute())


def get_writing(prompt_id: str) -> dict | None:
    return one_or_none(_svc().table(_WRITING).select("*").eq("id", prompt_id).execute())


def record_attempt(
    db: Any,
    child_id: str,
    *,
    kind: str,
    ref_id: str,
    level: int,
    verdict: str,
    tokens_awarded: int,
) -> dict:
    return one_or_none(
        db.table(_ATTEMPTS)
        .insert(
            {
                "child_id": child_id,
                "kind": kind,
                "ref_id": ref_id,
                "level": level,
                "verdict": verdict,
                "tokens_awarded": tokens_awarded,
            }
        )
        .execute()
    )


def progress(db: Any, child_id: str, *, limit: int = 50) -> list[dict]:
    return rows(
        db.table(_ATTEMPTS)
        .select("id, kind, ref_id, level, verdict, tokens_awarded, created_at")
        .eq("child_id", child_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
