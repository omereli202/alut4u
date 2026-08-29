from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ConsentBasis = Literal["parent", "guardian", "professional_with_parental_consent"]

MODULE_KEYS = (
    "aac_enabled",
    "schedule_enabled",
    "rules_enabled",
    "calming_enabled",
    "social_stories_enabled",
    "reading_writing_enabled",
)


class ChildCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    avatar_seed: str | None = Field(default=None, max_length=64)
    consent_basis: ConsentBasis
    # Required True when a professional creates a record about someone else's child.
    parental_consent_attested: bool = False
    # Optional starter board applied right after creation.
    board_template_id: str | None = None

    @model_validator(mode="after")
    def _professional_needs_attestation(self) -> ChildCreate:
        if (
            self.consent_basis == "professional_with_parental_consent"
            and not self.parental_consent_attested
        ):
            raise ValueError("parental_consent_attested is required for a professional record")
        return self


class ChildUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    birth_date: date | None = None
    avatar_seed: str | None = Field(default=None, max_length=64)


class ChildOut(BaseModel):
    id: str
    name: str
    birth_date: date | None = None
    avatar_seed: str | None = None
    consent_basis: ConsentBasis
    is_active: bool
    created_at: str


class ModulesUpdate(BaseModel):
    aac_enabled: bool | None = None
    schedule_enabled: bool | None = None
    rules_enabled: bool | None = None
    calming_enabled: bool | None = None
    social_stories_enabled: bool | None = None
    reading_writing_enabled: bool | None = None


class ModulesOut(BaseModel):
    child_id: str
    aac_enabled: bool
    schedule_enabled: bool
    rules_enabled: bool
    calming_enabled: bool
    social_stories_enabled: bool
    reading_writing_enabled: bool
