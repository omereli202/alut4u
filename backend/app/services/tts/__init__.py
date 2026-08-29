"""Text-to-speech provider abstraction.

The rest of the app depends only on :class:`TTSProvider` and :func:`get_provider`.
Swapping Azure for another engine (or adding voice cloning later) is a new
adapter file plus one line here — no module code changes.
"""

from __future__ import annotations

from app.config import Settings, current_settings
from app.services.tts.base import TTSProvider, TTSRequest, TTSResult

__all__ = ["TTSProvider", "TTSRequest", "TTSResult", "get_provider"]


def get_provider(settings: Settings | None = None) -> TTSProvider:
    s = settings or current_settings()
    from app.services.tts.azure_he import AzureHebrewTTS

    return AzureHebrewTTS(s)
