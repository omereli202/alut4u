"""children + per-child module settings.

Reads are allowed in User Mode (the child's device needs the roster and the
enabled-module list). All writes require Caregiver Mode. Tenancy is enforced by
RLS — a child that isn't the caregiver's simply isn't visible, so those cases
surface as 404.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.api._helpers import ApiError, client_ip, parse_body, user_agent
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import audit as audit_repo
from app.repositories import board_templates
from app.repositories import children as repo
from app.repositories import consent as consent_repo
from app.schemas.children import ChildCreate, ChildOut, ChildUpdate, ModulesOut, ModulesUpdate

bp = Blueprint("children", __name__, url_prefix="/api/children")


def _child_out(row: dict) -> dict:
    return ChildOut.model_validate({**row, "created_at": str(row["created_at"])}).model_dump(
        mode="json"
    )


def _require_child(child_id: str) -> dict:
    row = repo.get_child(g.db, child_id)
    if row is None:
        raise ApiError(404, "not_found")
    return row


@bp.get("")
@require_session
def list_children():
    return jsonify(children=[_child_out(r) for r in repo.list_children(g.db)])


@bp.post("")
@require_caregiver_mode
def create_child():
    data = parse_body(ChildCreate)
    row = repo.create_child(
        g.db,
        caregiver_id=g.caregiver_id,
        name=data.name,
        birth_date=data.birth_date.isoformat() if data.birth_date else None,
        avatar_seed=data.avatar_seed,
        consent_basis=data.consent_basis,
    )
    if data.consent_basis == "professional_with_parental_consent":
        consent_repo.record(
            caregiver_id=g.caregiver_id,
            child_id=row["id"],
            kind="professional_attestation",
            terms_version="n/a",
            ip=client_ip(),
            user_agent=user_agent(),
        )
    if data.board_template_id:
        board_templates.apply_to_child(g.db, row["id"], data.board_template_id)
    audit_repo.log(
        caregiver_id=g.caregiver_id, action="child.create", target_type="child", target_id=row["id"]
    )
    return jsonify(_child_out(row)), 201


@bp.get("/board-templates")
@require_session
def list_board_templates():
    return jsonify(templates=board_templates.list_templates())


@bp.get("/<child_id>")
@require_session
def get_child(child_id: str):
    return jsonify(_child_out(_require_child(child_id)))


@bp.patch("/<child_id>")
@require_caregiver_mode
def update_child(child_id: str):
    _require_child(child_id)
    data = parse_body(ChildUpdate)
    patch = data.model_dump(exclude_none=True)
    if "birth_date" in patch:
        patch["birth_date"] = data.birth_date.isoformat() if data.birth_date else None
    row = repo.update_child(g.db, child_id, patch)
    return jsonify(_child_out(row))


@bp.delete("/<child_id>")
@require_caregiver_mode
def deactivate_child(child_id: str):
    _require_child(child_id)
    repo.deactivate_child(g.db, child_id)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="child.deactivate",
        target_type="child",
        target_id=child_id,
    )
    return "", 204


@bp.get("/<child_id>/modules")
@require_session
def get_modules(child_id: str):
    _require_child(child_id)
    row = repo.get_modules(g.db, child_id)
    if row is None:
        raise ApiError(404, "not_found")
    return jsonify(ModulesOut.model_validate(row).model_dump())


@bp.put("/<child_id>/modules")
@require_caregiver_mode
def update_modules(child_id: str):
    _require_child(child_id)
    data = parse_body(ModulesUpdate)
    patch = data.model_dump(exclude_none=True)
    if not patch:
        raise ApiError(422, "no_fields")
    row = repo.update_modules(g.db, child_id, patch)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="child.modules_update",
        target_type="child",
        target_id=child_id,
        detail=patch,
    )
    return jsonify(ModulesOut.model_validate(row).model_dump())
