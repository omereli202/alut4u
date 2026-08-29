"""Silent stub TTS — used in local dev / CI when no real engine is configured,
so the pre-generate → cache → offline-playback pipeline is still exercisable.
Never selected in production (see get_provider)."""

from __future__ import annotations

import struct

from app.services.tts.base import TTSProvider, TTSRequest, TTSResult

_SAMPLE_RATE = 16_000


def _silent_wav(seconds: float) -> bytes:
    n = int(_SAMPLE_RATE * seconds)
    data = b"\x00\x00" * n
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, _SAMPLE_RATE, _SAMPLE_RATE * 2, 2, 16)
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


class SilentTTS(TTSProvider):
    name = "silent"

    def synthesize(self, req: TTSRequest) -> TTSResult:
        # ~90ms per character, min 0.4s — roughly speech-length so UI timing is real.
        seconds = max(0.4, len(req.text) * 0.09)
        return TTSResult(audio=_silent_wav(seconds), mime="audio/wav", char_count=len(req.text))
