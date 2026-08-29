"""Pre-generate and cache TTS audio.

Card audio is synthesised once, when a card is saved — never at tap time — so
speech works offline. The cache is keyed by sha256(voice|rate|fmt|text) and
shared across all children (a ``media_assets`` row with ``child_id`` null in the
``tts`` bucket), which is the main cost lever.
"""

from __future__ import annotations

from app.config import Settings, current_settings
from app.repositories import media as media_repo
from app.services import storage
from app.services.tts import get_provider
from app.services.tts.base import TTSError, TTSRequest


def ensure_tts_asset(text: str, settings: Settings | None = None) -> str | None:
    """Return a media_assets id for the audio of ``text``, synthesising and
    caching it if needed. Returns None if TTS is unavailable (card still saves,
    just silently)."""
    s = settings or current_settings()
    text = (text or "").strip()
    if not text:
        return None

    provider = get_provider(s)
    req = TTSRequest(text=text, voice=s.azure_speech_voice)
    key = req.cache_key()

    hit = media_repo.find_tts_by_digest(key)
    if hit:
        return hit["id"]

    try:
        result = provider.synthesize(req)
    except TTSError:
        return None

    ext = "wav" if "wav" in result.mime else "mp3"
    path = f"{key}.{ext}"
    storage.upload(storage.TTS_BUCKET, path, result.audio, result.mime)

    try:
        row = media_repo.create(
            child_id=None,
            kind="tts_cache",
            storage_path=f"{storage.TTS_BUCKET}/{path}",
            mime=result.mime,
            bytes_len=len(result.audio),
            digest=key,
        )
        return row["id"]
    except Exception:
        # Lost a race on the unique(sha256) index — the other writer won.
        again = media_repo.find_tts_by_digest(key)
        return again["id"] if again else None
