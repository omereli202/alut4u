"""usage_counters — per caregiver, per calendar month (period 'YYYY-MM').

Incremented server-side as AI/TTS work happens; read by the caregiver via their
own client (RLS: owner select). Enforcement lives in services/quotas.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.repositories._base import one_or_none
from app.services.supabase_client import service_client

_TABLE = "usage_counters"


def current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def get(db: Any, caregiver_id: str, period: str | None = None) -> dict:
    period = period or current_period()
    row = one_or_none(
        db.table(_TABLE).select("*").eq("caregiver_id", caregiver_id).eq("period", period).execute()
    )
    return row or {
        "caregiver_id": caregiver_id,
        "period": period,
        "tts_chars": 0,
        "image_count": 0,
        "llm_tokens": 0,
    }


def increment(
    caregiver_id: str, *, tts_chars: int = 0, image_count: int = 0, llm_tokens: int = 0
) -> None:
    # Read-then-write; fine at kiosk RPS. Phase 8 replaces this with an atomic
    # Postgres RPC if contention ever matters.
    period = current_period()
    db = service_client("write_usage_counter")
    existing = one_or_none(
        db.table(_TABLE)
        .select("tts_chars, image_count, llm_tokens")
        .eq("caregiver_id", caregiver_id)
        .eq("period", period)
        .execute()
    )
    if existing is None:
        db.table(_TABLE).insert(
            {
                "caregiver_id": caregiver_id,
                "period": period,
                "tts_chars": tts_chars,
                "image_count": image_count,
                "llm_tokens": llm_tokens,
            }
        ).execute()
        return
    db.table(_TABLE).update(
        {
            "tts_chars": existing["tts_chars"] + tts_chars,
            "image_count": existing["image_count"] + image_count,
            "llm_tokens": existing["llm_tokens"] + llm_tokens,
        }
    ).eq("caregiver_id", caregiver_id).eq("period", period).execute()
