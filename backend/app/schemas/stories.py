from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    child_id: str
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class ComposeRequest(BaseModel):
    child_id: str
    messages: list[ChatMessage] = Field(min_length=3, max_length=40)
