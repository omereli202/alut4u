from __future__ import annotations

import pytest

from app import create_app
from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        flask_secret_key="test-secret",
        supabase_url="",
        supabase_anon_key="test-anon",
    )


@pytest.fixture
def app(settings: Settings):
    application = create_app(settings)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()
