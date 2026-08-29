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

    # Azure Speech
    azure_speech_key: str = ""
    azure_speech_region: str = "westeurope"
    azure_speech_voice: str = "he-IL-HilaNeural"

    # OpenAI (phase 6)
    openai_api_key: str = ""

    # Quotas — per caregiver per calendar month; 0 disables the check
    quota_tts_chars_per_month: int = 200_000
    quota_image_count_per_month: int = 100
    quota_llm_tokens_per_month: int = 500_000

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
