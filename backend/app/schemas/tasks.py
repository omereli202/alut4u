from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Recurrence = Literal["daily", "once"]


class TaskCreate(BaseModel):
    child_id: str
    title: str = Field(min_length=1, max_length=80)
    symbol_id: str | None = None
    recurrence: Recurrence = "daily"
    sort_order: int = 0


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    symbol_id: str | None = None
    recurrence: Recurrence | None = None
    sort_order: int | None = None


class ToggleRequest(BaseModel):
    task_id: str
    the_date: date
    completed: bool
    idempotency_key: str | None = None  # from the offline outbox; server is idempotent


class ReorderRequest(BaseModel):
    child_id: str
    order: list[str] = Field(min_length=1)


class SettingsUpdate(BaseModel):
    child_id: str
    reward_tokens: int = Field(ge=0, le=20)


class ClaimRequest(BaseModel):
    child_id: str
    the_date: date
