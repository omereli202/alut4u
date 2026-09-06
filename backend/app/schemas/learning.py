from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["reading", "writing"]


class ReadingDoneRequest(BaseModel):
    child_id: str


class WritingAttemptRequest(BaseModel):
    child_id: str
    prompt_id: str
    submitted: str = Field(min_length=1, max_length=300)


class LearningClaimRequest(BaseModel):
    child_id: str
    kind: Kind
    level: int = Field(ge=1, le=3)


class ReadingCreate(BaseModel):
    child_id: str
    level: int = Field(ge=1, le=3)
    title: str = Field(min_length=1, max_length=60)
    body: str = Field(min_length=1, max_length=600)


class WritingCreate(BaseModel):
    child_id: str
    level: int = Field(ge=1, le=3)
    hint: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=300)
