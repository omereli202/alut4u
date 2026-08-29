"""GDPR data-subject endpoints: export and hard delete.

Both require Caregiver Mode. Built in Phase 1 deliberately — while the schema is
small — rather than bolted on at launch.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, session
from pydantic import BaseModel

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import COOKIE_KEY, require_caregiver_mode
from app.auth.gotrue import GoTrue
from app.repositories import account as repo
from app.repositories import audit as audit_repo

bp = Blueprint("account", __name__, url_prefix="/api/account")


class DeleteRequest(BaseModel):
    confirm: str  # must equal "DELETE"


@bp.get("/export")
@require_caregiver_mode
def export_account():
    bundle = repo.export_bundle(g.caregiver_id)
    audit_repo.log(caregiver_id=g.caregiver_id, action="account.export")
    resp = jsonify(bundle)
    resp.headers["Content-Disposition"] = 'attachment; filename="alut4u-account-export.json"'
    # Media assets (icons, audio) are added to this bundle in Phase 2.
    return resp


@bp.delete("")
@require_caregiver_mode
def delete_account():
    data = parse_body(DeleteRequest)
    if data.confirm != "DELETE":
        raise ApiError(422, "confirm_required", 'send {"confirm": "DELETE"}')

    caregiver_id = g.caregiver_id
    audit_repo.log(caregiver_id=caregiver_id, action="account.delete_requested")

    # Remove the auth user first (revokes all tokens), then cascade the data.
    GoTrue(current_app.config["SETTINGS"]).admin_delete_user(caregiver_id)
    repo.delete_everything(caregiver_id)
    audit_repo.log(caregiver_id=None, action="account.deleted", target_id=caregiver_id)

    session.pop(COOKIE_KEY, None)
    return "", 204
