from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class _Visual(BaseModel):
    symbol_id: str | None = None
    icon_asset_id: str | None = None

    @model_validator(mode="after")
    def _one_visual(self):
        if self.symbol_id and self.icon_asset_id:
            raise ValueError("either a symbol or an uploaded icon, not both")
        return self


class RuleCreate(_Visual):
    child_id: str
    title: str = Field(min_length=1, max_length=60)
    body: str | None = Field(default=None, max_length=300)
    sort_order: int = 0


class RuleUpdate(_Visual):
    title: str | None = Field(default=None, min_length=1, max_length=60)
    body: str | None = Field(default=None, max_length=300)
    audio_asset_id: str | None = None
    sort_order: int | None = None


class AwardRequest(BaseModel):
    child_id: str
    amount: int = Field(ge=-100, le=100)  # negative = remove tokens
    reason: str | None = Field(default=None, max_length=120)


class RewardCreate(_Visual):
    child_id: str
    title: str = Field(min_length=1, max_length=60)
    cost: int = Field(ge=1, le=1000)
    sort_order: int = 0


class RewardUpdate(_Visual):
    title: str | None = Field(default=None, min_length=1, max_length=60)
    cost: int | None = Field(default=None, ge=1, le=1000)
    is_active: bool | None = None
    sort_order: int | None = None


class RedeemRequest(BaseModel):
    child_id: str
    reward_id: str
    idempotency_key: str | None = None


class ReorderRequest(BaseModel):
    child_id: str
    order: list[str] = Field(min_length=1)
