from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    accept_terms: bool

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("terms must be accepted to create an account")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=4)


class AcceptTermsRequest(BaseModel):
    accept: bool


class VoiceConsentRequest(BaseModel):
    accept: bool


class OnboardingState(BaseModel):
    needs_pin: bool
    needs_terms: bool
    voice_consent: bool
    display_name: str | None = None


class SessionInfo(BaseModel):
    caregiver_id: str
    mode: str  # "user" | "caregiver"
    elevated_until: str | None
    onboarding: OnboardingState
