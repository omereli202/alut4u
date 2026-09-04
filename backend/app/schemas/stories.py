from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    child_id: str
    # empty on the very first turn — the agent opens with its first question
    messages: list[ChatMessage] = Field(default_factory=list, max_length=40)


class ComposeRequest(BaseModel):
    child_id: str
    messages: list[ChatMessage] = Field(min_length=3, max_length=40)


class IllustrateRequest(BaseModel):
    # None -> the server illustrates the next page that still lacks art.
    page_index: int | None = Field(default=None, ge=0, le=14)


class StoryEditPage(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class StoryEditRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    pages: list[StoryEditPage] = Field(min_length=1, max_length=15)
