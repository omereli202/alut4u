from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Style = Literal["h1", "h2", "p"]
FontFamily = Literal["rubik", "assistant", "heebo"]
FontScale = Literal["sm", "md", "lg", "xl"]

MAX_BLOCKS = 200
MAX_BLOCK_CHARS = 2000
MAX_NOTE_CHARS = 20_000
MAX_SPEAK_CHARS = 1500


class Block(BaseModel):
    t: Style
    s: str = Field(max_length=MAX_BLOCK_CHARS)


class NoteUpsert(BaseModel):
    child_id: str
    note_id: UUID
    title: str = Field(default="", max_length=120)
    blocks: list[Block] = Field(default_factory=list, max_length=MAX_BLOCKS)
    rev: int = Field(ge=1)
    font_family: FontFamily = "rubik"
    font_scale: FontScale = "md"
    # Written by outbox.flush() on replay; accepted so validation passes, unused
    # (the note_id + rev pair is what makes a replay idempotent).
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def _total_length(self) -> NoteUpsert:
        if sum(len(b.s) for b in self.blocks) > MAX_NOTE_CHARS:
            raise ValueError(f"note exceeds {MAX_NOTE_CHARS} characters")
        return self


class SpeakRequest(BaseModel):
    child_id: str


class TypingSettingsUpdate(BaseModel):
    child_id: str
    font_family: FontFamily | None = None
    font_scale: FontScale | None = None
