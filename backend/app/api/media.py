"""Media pipeline.

``POST /api/media`` — caregiver uploads an icon or audio clip. Validated,
normalised (images re-encoded, EXIF dropped), stored in a private bucket.

``GET /api/media/<id>`` — the **stable** URL the client and service worker use.
Supabase signed URLs rotate and would break the offline cache, so the bytes are
streamed through here with a long immutable cache header and an ETag.
"""

from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request

from app.api._helpers import ApiError
from app.auth.decorators import require_caregiver_mode, require_session
from app.extensions import limiter
from app.repositories import audit as audit_repo
from app.repositories import caregivers as caregivers_repo
from app.repositories import children as children_repo
from app.repositories import media as media_repo
from app.services import storage
from app.services.media_processing import (
    IMAGE_MIMES,
    MediaError,
    process_audio,
    process_image,
)

bp = Blueprint("media", __name__, url_prefix="/api/media")

_KINDS = {"card_icon", "card_audio", "schedule_icon", "rule_audio"}
_AUDIO_KINDS = {"card_audio", "rule_audio"}


@bp.post("")
@require_caregiver_mode
@limiter.limit("120 per hour")
def upload():
    kind = request.form.get("kind", "")
    child_id = request.form.get("child_id", "")
    if kind not in _KINDS:
        raise ApiError(422, "bad_kind")
    file = request.files.get("file")
    if file is None:
        raise ApiError(422, "no_file")

    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")

    if kind in _AUDIO_KINDS:
        state = caregivers_repo.get(g.db, g.caregiver_id) or {}
        if not state.get("voice_consent_at"):
            raise ApiError(403, "voice_consent_required")

    raw = file.read()
    declared = file.mimetype or ""
    try:
        if kind in _AUDIO_KINDS:
            processed = process_audio(raw, declared)
        elif declared in IMAGE_MIMES or not declared:
            processed = process_image(raw)
        else:
            raise MediaError(f"unsupported type {declared}")
    except MediaError as e:
        raise ApiError(422, "invalid_media", str(e)) from e

    digest = media_repo.sha256(processed.data)
    object_path = f"{child_id}/{digest}.{processed.ext}"
    storage.upload(storage.MEDIA_BUCKET, object_path, processed.data, processed.mime)

    row = media_repo.create(
        child_id=child_id,
        kind=kind,
        storage_path=f"{storage.MEDIA_BUCKET}/{object_path}",
        mime=processed.mime,
        bytes_len=len(processed.data),
        digest=digest,
    )
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="media.upload",
        target_type="media_asset",
        target_id=row["id"],
        detail={"kind": kind, "child_id": child_id},
    )
    return jsonify(
        id=row["id"], url=f"/api/media/{row['id']}", mime=processed.mime, bytes=len(processed.data)
    ), 201


@bp.get("/<asset_id>")
@require_session
def fetch(asset_id: str):
    row = media_repo.get_for_caller(g.db, asset_id) or media_repo.get_shared_tts(asset_id)
    if row is None:
        raise ApiError(404, "not_found")

    etag = f'"{row["sha256"]}"'
    if request.headers.get("If-None-Match") == etag:
        return Response(status=304, headers={"ETag": etag})

    bucket, _, object_path = row["storage_path"].partition("/")
    data = storage.download(bucket, object_path)

    return Response(
        data,
        mimetype=row["mime"],
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Length": str(len(data)),
        },
    )
