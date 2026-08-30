"""Flask application factory.

In production the backend serves **only** the REST API under ``/api`` — a
separate Caddy service serves the static PWA and reverse-proxies ``/api/*`` here
over Railway's private network.

For local development one process can serve both: set ``SERVE_FRONTEND=1``
(``scripts/dev.sh`` does) and Flask falls back to the static files in
``frontend/`` for non-API routes.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from app.api._helpers import ApiError
from app.config import Settings, get_settings
from app.extensions import limiter
from app.observability import configure_logging, init_sentry
from app.observability import register as register_observability

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    settings.require_production_secrets()

    configure_logging(settings)
    init_sentry(settings)

    app = Flask(__name__, static_folder=None)
    app.config["SETTINGS"] = settings
    app.config["SECRET_KEY"] = settings.flask_secret_key
    app.config["SESSION_COOKIE_NAME"] = settings.session_cookie_name
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = settings.is_production
    # Kiosk: the session should outlast the tablet being idle for weeks.
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)

    limiter.init_app(app)
    register_observability(app, settings)
    _register_blueprints(app)
    if settings.serve_frontend and FRONTEND_DIR.is_dir():
        _register_frontend(app)
    _register_error_handlers(app)

    return app


def _register_blueprints(app: Flask) -> None:
    from app.api.aac import bp as aac_bp
    from app.api.account import bp as account_bp
    from app.api.auth import bp as auth_bp
    from app.api.children import bp as children_bp
    from app.api.health import bp as health_bp
    from app.api.learning import bp as learning_bp
    from app.api.media import bp as media_bp
    from app.api.schedule import bp as schedule_bp
    from app.api.stories import bp as stories_bp
    from app.api.symbols import bp as symbols_bp
    from app.api.tokens import bp as tokens_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(children_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(symbols_bp)
    app.register_blueprint(aac_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(tokens_bp)
    app.register_blueprint(stories_bp)
    app.register_blueprint(learning_bp)


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
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        body, status = e.response()
        return jsonify(body), status

    @app.errorhandler(404)
    def _404(_e):
        return jsonify(error="not_found"), 404

    @app.errorhandler(429)
    def _429(_e):
        return jsonify(error="rate_limited"), 429

    @app.errorhandler(500)
    def _500(_e):
        app.logger.exception("unhandled error")
        return jsonify(error="internal_error"), 500


# `flask --app app run` and `gunicorn "app:create_app()"` both discover the
# factory above; no module-level app instance needed.
