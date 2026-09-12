from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Modified Fitzgerald Key (softened palette — frontend/css/tokens.css's
# --pos-* tokens). Kept in sync with the check constraint in
# supabase/migrations/0029_aac_part_of_speech.sql.
PartOfSpeech = Literal[
    "pronoun", "verb", "adjective", "noun", "social", "question", "negation", "little", "adverb"
]


class CategoryCreate(BaseModel):
    child_id: str
    name: str = Field(min_length=1, max_length=40)
    color: str | None = Field(default=None, max_length=16)
    parent_id: str | None = None
    symbol_id: str | None = None
    icon_asset_id: str | None = None

    @model_validator(mode="after")
    def _one_visual(self) -> CategoryCreate:
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("a category has either a symbol or an uploaded icon, not both")
        return self


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, max_length=16)
    parent_id: str | None = None
    symbol_id: str | None = None
    icon_asset_id: str | None = None

    @model_validator(mode="after")
    def _one_visual(self) -> CategoryUpdate:
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("a category has either a symbol or an uploaded icon, not both")
        return self


class CardCreate(BaseModel):
    child_id: str
    label: str = Field(min_length=1, max_length=40)
    tts_text: str | None = Field(default=None, max_length=200)
    category_id: str | None = None
    symbol_id: str | None = None
    icon_asset_id: str | None = None
    part_of_speech: PartOfSpeech | None = None
    grid_order: int = 0

    @model_validator(mode="after")
    def _one_visual(self) -> CardCreate:
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("a card has either a symbol or an uploaded icon, not both")
        return self


class CardUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=40)
    tts_text: str | None = Field(default=None, max_length=200)
    category_id: str | None = None
    symbol_id: str | None = None
    icon_asset_id: str | None = None
    audio_asset_id: str | None = None
    part_of_speech: PartOfSpeech | None = None
    grid_order: int | None = None

    @model_validator(mode="after")
    def _one_visual(self) -> CardUpdate:
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("a card has either a symbol or an uploaded icon, not both")
        return self


class ReorderRequest(BaseModel):
    child_id: str
    order: list[str] = Field(min_length=1)
