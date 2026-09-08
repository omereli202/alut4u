"""בוא נצייר (Let's paint) — request models.

A painting is vector JSON: a list of brush/eraser strokes plus a list of
region fills, over either a blank page or a bundled Mulberry symbol rendered
as line art. Coordinates are page-normalised (0..1), never viewBox units.

Colours are validated against a hex pattern here, not just trusted from the
client — the frontend maps a region key straight to ``style.fill``, which is a
CSS-value sink (same lesson as typing_settings' font keys). Every cap is
enforced at save; the client also enforces them at capture so a four-minute
unbroken stroke can't blow the budget.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MAX_STROKES = 400
MAX_STROKE_NUMBERS = 2000  # 1000 x,y points
MAX_TOTAL_POINTS = 60_000  # ~700 KB of JSON; count + per-stroke caps alone allow ~4.8 MB
MAX_FILLS = 300
MAX_PAGES = 60

_COLOUR = r"^#[0-9a-f]{6}$"
_REGION = r"^r[0-9a-z]{1,14}$"
_SYMBOL = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class Stroke(BaseModel):
    c: str = Field(default="#000000", pattern=_COLOUR)
    w: float = Field(ge=0.002, le=0.2)
    e: Literal[0, 1] = 0
    p: list[float] = Field(min_length=4, max_length=MAX_STROKE_NUMBERS)

    @model_validator(mode="after")
    def _pairs_in_range(self) -> Stroke:
        if len(self.p) % 2:
            raise ValueError("p must hold x,y pairs")
        if any(not (-0.05 <= v <= 1.05) for v in self.p):
            raise ValueError("coordinates must be page-normalised (0..1)")
        return self


class Fill(BaseModel):
    r: str = Field(pattern=_REGION)
    c: str = Field(pattern=_COLOUR)


class Page(BaseModel):
    kind: Literal["blank", "symbol"] = "blank"
    symbol_id: str | None = Field(default=None, pattern=_SYMBOL, max_length=64)
    sig: str | None = Field(default=None, max_length=16)
    sv: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _symbol_needs_id(self) -> Page:
        if self.kind == "symbol" and not self.symbol_id:
            raise ValueError("a symbol page needs symbol_id")
        if self.kind == "blank":
            self.symbol_id = None
        return self


class PaintingUpsert(BaseModel):
    child_id: str
    painting_id: UUID  # CLIENT-generated — the offline outbox is POST-only
    title: str = Field(default="", max_length=80)
    page: Page = Field(default_factory=Page)
    strokes: list[Stroke] = Field(default_factory=list, max_length=MAX_STROKES)
    fills: list[Fill] = Field(default_factory=list, max_length=MAX_FILLS)
    rev: int = Field(ge=1)
    # Written by outbox.flush() on replay; accepted so validation passes, unused
    # (painting_id + rev is what makes a replay idempotent).
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def _total_points(self) -> PaintingUpsert:
        total = sum(len(s.p) for s in self.strokes) // 2
        if total > MAX_TOTAL_POINTS:
            raise ValueError(f"painting exceeds {MAX_TOTAL_POINTS} points")
        # A fill can't reference a colour outside the palette check either — but
        # de-duping to last-write-wins per region is the client's job; here we
        # only bound the count (done via max_length above).
        return self


class PagesUpdate(BaseModel):
    child_id: str
    symbol_ids: list[str] = Field(default_factory=list, max_length=MAX_PAGES)

    @model_validator(mode="after")
    def _shape(self) -> PagesUpdate:
        import re

        for s in self.symbol_ids:
            if not re.match(_SYMBOL, s):
                raise ValueError(f"bad symbol id: {s!r}")
        if len(set(self.symbol_ids)) != len(self.symbol_ids):
            raise ValueError("duplicate symbol id")
        return self
