"""TTS provider interface and value objects."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TTSRequest:
    text: str
    voice: str
    rate: float = 1.0  # 1.0 == natural speed
    fmt: str = "audio-24khz-48kbitrate-mono-mp3"

    def cache_key(self) -> str:
        """Stable key for the shared audio cache. Identical text+voice+rate
        across all children resolves to one cached file — the main TTS cost
        lever."""
        raw = f"{self.voice}|{self.rate}|{self.fmt}|{self.text}".encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class TTSResult:
    audio: bytes
    mime: str
    char_count: int


class TTSProvider(Protocol):
    name: str

    def synthesize(self, req: TTSRequest) -> TTSResult:
        """Render ``req`` to audio. Raises :class:`TTSError` on failure."""
        ...


class TTSError(RuntimeError):
    pass
