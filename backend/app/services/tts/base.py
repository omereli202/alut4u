"""TTS provider interface and value objects."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TTSRequest:
    text: str
    voice: str
    provider: str  # TTSProvider.name of the renderer — part of the key so a
    # stub-rendered asset (see SilentTTS) can never satisfy a lookup meant for
    # a real engine's output. Required, not defaulted: a default would let a
    # future call site silently reintroduce that collision. See the
    # silent-audio poisoning incident this fixed.
    rate: float = 1.0  # 1.0 == natural speed
    fmt: str = "audio-24khz-48kbitrate-mono-mp3"

    def cache_key(self) -> str:
        """Stable key for the shared audio cache. Identical provider+text+
        voice+rate across all children resolves to one cached file — the main
        TTS cost lever."""
        raw = f"{self.provider}|{self.voice}|{self.rate}|{self.fmt}|{self.text}".encode()
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
