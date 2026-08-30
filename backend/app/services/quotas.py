"""Per-caregiver monthly usage caps for the paid AI/TTS work.

Reads and writes go through the service role (system accounting), so a quota
check does not need a request-scoped Supabase client. A cap of 0 disables that
check.
"""

from __future__ import annotations

from app.config import current_settings
from app.repositories import usage as usage_repo


class QuotaExceeded(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(resource)
        self.resource = resource


def check(caregiver_id: str, *, tts_chars: int = 0, images: int = 0, llm_tokens: int = 0) -> None:
    """Raise QuotaExceeded if adding this work would exceed a cap."""
    s = current_settings()
    used = usage_repo.get_system(caregiver_id)
    for name, projected, cap in (
        ("tts_chars", used["tts_chars"] + tts_chars, s.quota_tts_chars_per_month),
        ("image_count", used["image_count"] + images, s.quota_image_count_per_month),
        ("llm_tokens", used["llm_tokens"] + llm_tokens, s.quota_llm_tokens_per_month),
    ):
        if cap and projected > cap:
            raise QuotaExceeded(name)


def within(caregiver_id: str, *, tts_chars: int = 0, images: int = 0, llm_tokens: int = 0) -> bool:
    try:
        check(caregiver_id, tts_chars=tts_chars, images=images, llm_tokens=llm_tokens)
        return True
    except QuotaExceeded:
        return False


def record(caregiver_id: str, *, tts_chars: int = 0, images: int = 0, llm_tokens: int = 0) -> None:
    usage_repo.increment(
        caregiver_id, tts_chars=tts_chars, image_count=images, llm_tokens=llm_tokens
    )
