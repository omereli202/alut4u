from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class _Visual(BaseModel):
    symbol_id: str | None = None
    icon_asset_id: str | None = None

    @model_validator(mode="after")
    def _one_visual(self):
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("either a symbol or an uploaded icon, not both")
        return self


class ScheduleItemCreate(_Visual):
    child_id: str
    the_date: date
    title: str = Field(min_length=1, max_length=80)
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    sort_order: int = 0


class ScheduleItemUpdate(_Visual):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    sort_order: int | None = None


class ToggleRequest(BaseModel):
    item_id: str
    completed: bool
    idempotency_key: str | None = None  # from the offline outbox; server is idempotent


class ReorderRequest(BaseModel):
    child_id: str
    order: list[str] = Field(min_length=1)


class CopyDayRequest(BaseModel):
    child_id: str
    from_date: date
    to_date: date


class CalendarEventCreate(_Visual):
    child_id: str
    event_date: date
    title: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=300)


class CalendarEventUpdate(_Visual):
    event_date: date | None = None
    title: str | None = Field(default=None, min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=300)
