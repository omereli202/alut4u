from __future__ import annotations

from app import create_app
from app.config import Settings


def test_serve_frontend_disabled_leaves_non_api_routes_unregistered():
    app = create_app(Settings(app_env="test", serve_frontend=False))
    client = app.test_client()

    # API still works.
    assert client.get("/api/health").status_code == 200
    # The SPA fallback route is not registered → 404 (Caddy handles this in prod).
    assert client.get("/some/spa/route").status_code == 404
