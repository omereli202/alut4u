"""בוא נצייר (Let's paint) — a blank drawing page and colouring pages.

No target, no scoring, no tokens — the child paints, titles it, and saves it
to show a parent later (same posture as the typing board). Nothing here is
PIN-gated except editing the caregiver's curated colouring-page list.

Saves are an **upsert on a client-supplied id** so the offline outbox (POST
only, returns nothing) can replay them; a monotonic ``rev`` makes a stale
replay a no-op. The list route returns summaries only — a gallery must not
pull every stroke.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import painting as repo
from app.repositories.painting import PaintingIdConflict
from app.schemas.painting import PagesUpdate, PaintingUpsert

bp = Blueprint("painting", __name__, url_prefix="/api/painting")


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _arg(name: str) -> str:
    v = request.args.get(name)
    if not v:
        raise ApiError(422, "missing_param", name)
    return v


def _summary(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "page": row["page"],
        "rev": row["rev"],
        "updated_at": str(row["updated_at"]),
    }


def _full(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "page": row["page"],
        "strokes": row.get("strokes") or [],
        "fills": row.get("fills") or [],
        "rev": row["rev"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


# --- paintings ---------------------------------------------------------


@bp.get("/paintings")
@require_session
def list_paintings():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(paintings=[_summary(r) for r in repo.list_paintings(g.db, child_id)])


@bp.get("/paintings/<painting_id>")
@require_session
def get_painting(painting_id: str):
    row = repo.get_painting(g.db, painting_id)
    if row is None:
        raise ApiError(404, "painting_not_found")
    return jsonify(_full(row))


@bp.post("/paintings")
@require_session
def upsert_painting():
    data = parse_body(PaintingUpsert)
    _own_child_or_404(data.child_id)

    existing = repo.get_painting(g.db, str(data.painting_id))
    if existing is not None and existing["child_id"] != data.child_id:
        # A painting the caller can see (their own child) but under a different
        # child — refuse rather than reparent it.
        raise ApiError(404, "painting_not_found")

    values = {
        "painting_id": str(data.painting_id),
        "title": data.title,
        "page": data.page.model_dump(),
        "strokes": [s.model_dump() for s in data.strokes],
        "fills": [f.model_dump() for f in data.fills],
        "rev": data.rev,
    }
    try:
        row = repo.upsert_painting(g.db, data.child_id, g.caregiver_id, values)
    except PaintingIdConflict as e:
        raise ApiError(409, "painting_id_conflict") from e

    return jsonify(id=row["id"], rev=row["rev"], updated_at=str(row["updated_at"]))


@bp.delete("/paintings/<painting_id>")
@require_session
def delete_painting(painting_id: str):
    row = repo.get_painting(g.db, painting_id)
    if row is None:
        raise ApiError(404, "painting_not_found")
    repo.delete_painting(g.db, painting_id)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="painting.delete",
        target_type="child",
        target_id=row["child_id"],
        detail={"painting_id": painting_id, "elevated": g.session.is_elevated()},
    )
    return "", 204


# --- caregiver-curated colouring pages -------------------------------


@bp.get("/pages")
@require_session
def list_pages():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(symbol_ids=[r["symbol_id"] for r in repo.list_pages(g.db, child_id)])


@bp.put("/pages")
@require_caregiver_mode
def update_pages():
    data = parse_body(PagesUpdate)
    _own_child_or_404(data.child_id)
    saved = repo.set_pages(g.db, data.child_id, data.symbol_ids)
    return jsonify(symbol_ids=[r["symbol_id"] for r in saved])
