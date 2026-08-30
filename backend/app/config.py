"""Environment-driven configuration.

One ``Settings`` object, populated from environment variables (and a local
``.env`` during development). Fail fast: if a required value is missing in
production the app refuses to start rather than 500-ing later.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Env = Literal["development", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Env = "development"
    flask_secret_key: str = "dev-insecure-change-me"
    log_level: str = "INFO"
    public_base_url: str = "http://localhost:8000"

    # Local dev serves the PWA from Flask too; in production Caddy does, so the
    # backend image sets SERVE_FRONTEND=0.
    serve_frontend: bool = True

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Session refresh-token encryption (Fernet key)
    session_token_enc_key: str = ""

    # Session / Caregiver-Mode
    session_cookie_name: str = "alut4u_sid"
    caregiver_elevation_minutes: int = 15
    # Escalating PIN lockout: after N failures, lock for the matching duration.
    pin_lockout_after: int = 5
    pin_lockout_steps_seconds: tuple[int, ...] = (60, 300, 900)
    # Optional server-side pepper mixed into the PIN before hashing.
    pin_pepper: str = ""
    # Terms version presented at onboarding; bump when the text changes.
    terms_version: str = "2026-08-29"

    # Azure Speech
    azure_speech_key: str = ""
    azure_speech_region: str = "westeurope"
    azure_speech_voice: str = "he-IL-HilaNeural"

    # OpenAI (Phase 6). Confirm the current model ids for your account.
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o"
    openai_image_model: str = "dall-e-3"

    # Quotas — per caregiver per calendar month; 0 disables the check
    quota_tts_chars_per_month: int = 200_000
    quota_image_count_per_month: int = 100
    quota_llm_tokens_per_month: int = 500_000

    # Data retention — accounts idle this long are warned, then purged.
    retention_warn_days: int = 540
    retention_purge_days: int = 730

    # Observability — optional Sentry DSN; structured JSON logs when true.
    sentry_dsn: str = ""
    json_logs: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @field_validator("log_level")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    def require_production_secrets(self) -> None:
        """Raise if a production deployment is missing a critical secret."""
        if not self.is_production:
            return
        missing = [
            name
            for name in (
                "flask_secret_key",
                "supabase_url",
                "supabase_anon_key",
                "supabase_service_role_key",
                "supabase_jwt_secret",
                "session_token_enc_key",
            )
            if not getattr(self, name) or getattr(self, name) == "dev-insecure-change-me"
        ]
        if missing:
            raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def current_settings() -> Settings:
    """The Settings bound to the running app, if there is one (tests pass their
    own), else the process-wide singleton. Use this everywhere outside the app
    factory."""
    try:
        from flask import current_app, has_app_context

        if has_app_context() and "SETTINGS" in current_app.config:
            return current_app.config["SETTINGS"]
    except ImportError:
        pass
    return get_settings()
