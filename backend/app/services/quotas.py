"""Per-caregiver monthly usage caps for the paid AI/TTS work.

Enforcement is best-effort (read-then-check); the real teeth land in Phase 8.
A limit of 0 disables that check (dev default for some).
"""

from __future__ import annotations

from typing import Any

from app.config import current_settings
from app.repositories import usage as usage_repo


class QuotaExceeded(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(resource)
        self.resource = resource


def check(
    db: Any, caregiver_id: str, *, tts_chars: int = 0, images: int = 0, llm_tokens: int = 0
) -> None:
    s = current_settings()
    used = usage_repo.get(db, caregiver_id)
    checks = [
        ("tts_chars", used["tts_chars"] + tts_chars, s.quota_tts_chars_per_month),
        ("image_count", used["image_count"] + images, s.quota_image_count_per_month),
        ("llm_tokens", used["llm_tokens"] + llm_tokens, s.quota_llm_tokens_per_month),
    ]
    for name, projected, cap in checks:
        if cap and projected > cap:
            raise QuotaExceeded(name)


def record(caregiver_id: str, *, tts_chars: int = 0, images: int = 0, llm_tokens: int = 0) -> None:
    usage_repo.increment(
        caregiver_id, tts_chars=tts_chars, image_count=images, llm_tokens=llm_tokens
    )
