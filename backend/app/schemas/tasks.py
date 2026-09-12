from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Recurrence = Literal["daily", "once"]


class _Visual(BaseModel):
    symbol_id: str | None = None
    icon_asset_id: str | None = None

    @model_validator(mode="after")
    def _one_visual(self):
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("either a symbol or an uploaded icon, not both")
        return self


class TaskCreate(_Visual):
    child_id: str
    title: str = Field(min_length=1, max_length=80)
    recurrence: Recurrence = "daily"
    sort_order: int = 0


class TaskUpdate(_Visual):
    title: str | None = Field(default=None, min_length=1, max_length=80)
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
