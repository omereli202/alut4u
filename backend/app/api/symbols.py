"""Symbol library search — read-only, any signed-in caregiver."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth.decorators import require_session
from app.repositories import symbols as repo

bp = Blueprint("symbols", __name__, url_prefix="/api/symbols")


@bp.get("")
@require_session
def search():
    _ = g.caregiver_id  # require_session populated it
    q = request.args.get("q", "")
    hits, total = repo.search(q)
    return jsonify(symbols=hits, total=total)
