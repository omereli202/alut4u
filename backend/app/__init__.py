"""Flask application factory.

In production the backend serves **only** the REST API under ``/api`` — a
separate Caddy service serves the static PWA and reverse-proxies ``/api/*`` here
over Railway's private network.

For local development one process can serve both: set ``SERVE_FRONTEND=1``
(``scripts/dev.sh`` does) and Flask falls back to the static files in
``frontend/`` for non-API routes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from app.config import Settings, get_settings

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    settings.require_production_secrets()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = Flask(__name__, static_folder=None)
    app.config["SETTINGS"] = settings
    app.config["SECRET_KEY"] = settings.flask_secret_key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = settings.is_production

    _register_blueprints(app)
    if settings.serve_frontend and FRONTEND_DIR.is_dir():
        _register_frontend(app)
    _register_error_handlers(app)

    return app


def _register_blueprints(app: Flask) -> None:
    from app.api.health import bp as health_bp

    app.register_blueprint(health_bp)

    # Feature blueprints are added here as phases land:
    #   from app.api.account import bp as account_bp   (Phase 1)
    #   from app.api.children import bp as children_bp  (Phase 1)
    #   from app.api.modules import bp as modules_bp    (Phase 1)
    #   from app.api.media import bp as media_bp        (Phase 1)
    #   from app.api.aac import bp as aac_bp            (Phase 2)


def _register_frontend(app: Flask) -> None:
    """Local-dev convenience: serve the PWA from Flask. API routes match first;
    everything else falls through to the static app with an SPA-style fallback
    to index.html. In production Caddy does this instead."""

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def serve_frontend(path: str):
        if path.startswith("api/"):
            return jsonify(error="not_found"), 404
        target = FRONTEND_DIR / path
        if path and target.is_file():
            return send_from_directory(FRONTEND_DIR, path)
        return send_from_directory(FRONTEND_DIR, "index.html")


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def _404(_e):
        return jsonify(error="not_found"), 404

    @app.errorhandler(500)
    def _500(_e):
        app.logger.exception("unhandled error")
        return jsonify(error="internal_error"), 500


# `flask --app app run` and `gunicorn "app:create_app()"` both discover the
# factory above; no module-level app instance needed.
