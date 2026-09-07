"""Typing board ("לוח הקלדה") — free-composition notes ("פתקים").

For a child who already communicates by typing. No target, no scoring, no
tokens, no levels — the child writes, titles the note, and saves it to show a
parent or therapist later.

Nothing here is PIN-gated. A child mid-thought must never meet a keypad, so
saving is ``@require_session`` (same posture as ``POST /schedule/toggle``);
deleting is child-or-caregiver by product decision, guarded client-side by a
confirm dialog; the typeface/size pickers live on the child's own board.

Saves are an **upsert on a client-supplied id** so the offline outbox (which is
POST-only and returns nothing) can replay them. A monotonic ``rev`` makes a
stale replay a no-op.
"""

from __future__ import annotations

import hashlib

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_session
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import typing as repo
from app.repositories.typing import NoteIdConflict
from app.schemas.typing import MAX_SPEAK_CHARS, NoteUpsert, SpeakRequest, TypingSettingsUpdate
from app.services.tts import cache as tts_cache

bp = Blueprint("typing", __name__, url_prefix="/api/typing")

_PREVIEW_CHARS = 80


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


def _plain_text(blocks: list[dict]) -> str:
    return "\n".join(b.get("s", "") for b in blocks).strip()


def _preview(blocks: list[dict]) -> str:
    joined = " ".join(b.get("s", "") for b in blocks).strip()
    return joined[:_PREVIEW_CHARS]


def _note_list_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "preview": _preview(row.get("blocks") or []),
        "rev": row["rev"],
        "font_family": row["font_family"],
        "font_scale": row["font_scale"],
        "updated_at": str(row["updated_at"]),
    }


def _note_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "blocks": row.get("blocks") or [],
        "rev": row["rev"],
        "font_family": row["font_family"],
        "font_scale": row["font_scale"],
        "audio_url": f"/api/media/{row['tts_asset_id']}" if row.get("tts_asset_id") else None,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


# --- notes --------------------------------------------------------------


@bp.get("/notes")
@require_session
def list_notes():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(notes=[_note_list_row(r) for r in repo.list_notes(g.db, child_id)])


@bp.get("/notes/<note_id>")
@require_session
def get_note(note_id: str):
    row = repo.get_note(g.db, note_id)
    if row is None:
        raise ApiError(404, "note_not_found")
    return jsonify(_note_out(row))


@bp.post("/notes")
@require_session
def upsert_note():
    data = parse_body(NoteUpsert)
    _own_child_or_404(data.child_id)

    existing = repo.get_note(g.db, str(data.note_id))
    if existing is not None and existing["child_id"] != data.child_id:
        # A note the caller can see (their own child) but under a different
        # child — refuse rather than reparent it.
        raise ApiError(404, "note_not_found")

    values = {
        "note_id": str(data.note_id),
        "title": data.title,
        "blocks": [b.model_dump() for b in data.blocks],
        "rev": data.rev,
        "font_family": data.font_family,
        "font_scale": data.font_scale,
    }
    try:
        row = repo.upsert_note(g.db, data.child_id, g.caregiver_id, values)
    except NoteIdConflict as e:
        raise ApiError(409, "note_id_conflict") from e

    return jsonify(id=row["id"], rev=row["rev"], updated_at=str(row["updated_at"]))


@bp.delete("/notes/<note_id>")
@require_session
def delete_note(note_id: str):
    row = repo.get_note(g.db, note_id)
    if row is None:
        raise ApiError(404, "note_not_found")
    repo.delete_note(g.db, note_id)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="typing.note_delete",
        target_type="child",
        target_id=row["child_id"],
        detail={"note_id": note_id, "elevated": g.session.is_elevated()},
    )
    return "", 204


@bp.post("/notes/<note_id>/speak")
@require_session
def speak_note(note_id: str):
    data = parse_body(SpeakRequest)
    _own_child_or_404(data.child_id)
    row = repo.get_note(g.db, note_id)
    if row is None or row["child_id"] != data.child_id:
        raise ApiError(404, "note_not_found")

    text = _plain_text(row.get("blocks") or [])
    if not text:
        return jsonify(audio_url=None)
    if len(text) > MAX_SPEAK_CHARS:
        raise ApiError(422, "text_too_long_for_speech")

    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if row.get("tts_asset_id") and row.get("tts_text_hash") == text_hash:
        return jsonify(audio_url=f"/api/media/{row['tts_asset_id']}")

    asset_id = tts_cache.ensure_tts_asset(text)
    if asset_id is None:
        return jsonify(audio_url=None)
    repo.set_tts(g.db, note_id, asset_id, text_hash)
    return jsonify(audio_url=f"/api/media/{asset_id}")


# --- settings ---------------------------------------------------------


@bp.get("/settings")
@require_session
def get_settings():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    s = repo.get_settings(g.db, child_id)
    return jsonify(font_family=s["font_family"], font_scale=s["font_scale"])


@bp.put("/settings")
@require_session
def update_settings():
    data = parse_body(TypingSettingsUpdate)
    _own_child_or_404(data.child_id)
    patch = {k: v for k, v in data.model_dump(exclude={"child_id"}).items() if v is not None}
    if not patch:
        raise ApiError(422, "nothing_to_update")
    row = repo.upsert_settings(g.db, data.child_id, patch)
    return jsonify(font_family=row["font_family"], font_scale=row["font_scale"])
