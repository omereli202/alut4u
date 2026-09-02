"""Azure Speech adapter for Israeli-Hebrew neural voices.

Uses the REST synthesis endpoint (no SDK dependency). SSML wraps the text so we
can control rate and keep the door open for per-phrase prosody later.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

import httpx

from app.config import Settings
from app.services.tts.base import TTSError, TTSProvider, TTSRequest, TTSResult

_ENDPOINT = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


class AzureHebrewTTS(TTSProvider):
    name = "azure-he"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.azure_speech_key
        self._region = settings.azure_speech_region
        self._default_voice = settings.azure_speech_voice
        self._timeout = settings.azure_speech_timeout_seconds

    def synthesize(self, req: TTSRequest) -> TTSResult:
        if not self._key:
            raise TTSError("AZURE_SPEECH_KEY is not configured")

        voice = req.voice or self._default_voice
        ssml = (
            '<speak version="1.0" xml:lang="he-IL">'
            f'<voice name="{voice}">'
            f'<prosody rate="{req.rate:g}">{escape(req.text)}</prosody>'
            "</voice></speak>"
        )
        try:
            r = httpx.post(
                _ENDPOINT.format(region=self._region),
                headers={
                    "Ocp-Apim-Subscription-Key": self._key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": req.fmt,
                    "User-Agent": "alut4u",
                },
                content=ssml.encode("utf-8"),
                timeout=self._timeout,
            )
        except httpx.HTTPError as e:  # network / timeout
            raise TTSError(f"azure request failed: {e}") from e

        if r.status_code != 200:
            raise TTSError(f"azure returned {r.status_code}: {r.text[:200]}")

        mime = "audio/mpeg" if "mp3" in req.fmt else "application/octet-stream"
        return TTSResult(audio=r.content, mime=mime, char_count=len(req.text))
