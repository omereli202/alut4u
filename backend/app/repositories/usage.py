"""usage_counters — per caregiver, per calendar month (period 'YYYY-MM').

Incremented server-side as AI/TTS work happens (atomic via the bump_usage RPC).
Read by the caregiver via their own client (RLS), or system-side via the
service role for quota checks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.repositories._base import one_or_none
from app.services.supabase_client import service_client

_TABLE = "usage_counters"

_EMPTY = {"tts_chars": 0, "image_count": 0, "llm_tokens": 0}


def current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _shape(row: dict | None, caregiver_id: str, period: str) -> dict:
    return {"caregiver_id": caregiver_id, "period": period, **_EMPTY, **(row or {})}


def get(db: Any, caregiver_id: str, period: str | None = None) -> dict:
    """Caregiver-facing read via their own client (RLS)."""
    period = period or current_period()
    row = one_or_none(
        db.table(_TABLE).select("*").eq("caregiver_id", caregiver_id).eq("period", period).execute()
    )
    return _shape(row, caregiver_id, period)


def get_system(caregiver_id: str, period: str | None = None) -> dict:
    """Service-role read for quota checks (no request context needed)."""
    period = period or current_period()
    db = service_client("write_usage_counter")
    row = one_or_none(
        db.table(_TABLE)
        .select("tts_chars, image_count, llm_tokens")
        .eq("caregiver_id", caregiver_id)
        .eq("period", period)
        .execute()
    )
    return _shape(row, caregiver_id, period)


def increment(
    caregiver_id: str, *, tts_chars: int = 0, image_count: int = 0, llm_tokens: int = 0
) -> None:
    service_client("write_usage_counter").rpc(
        "bump_usage",
        {
            "p_caregiver": caregiver_id,
            "p_period": current_period(),
            "p_tts": tts_chars,
            "p_images": image_count,
            "p_llm": llm_tokens,
        },
    ).execute()
