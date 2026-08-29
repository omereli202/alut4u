from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReadingVerdictRequest(BaseModel):
    child_id: str
    verdict: Literal["pass", "fail"]


class WritingAttemptRequest(BaseModel):
    child_id: str
    prompt_id: str
    submitted: str = Field(min_length=1, max_length=300)
