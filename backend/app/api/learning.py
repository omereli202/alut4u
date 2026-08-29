"""Graded reading & writing practice.

Reading: the child reads a graded text aloud (read-aloud support is client-side);
the **caregiver** marks pass/fail — there is no speech recognition. A pass awards
tokens.

Writing: the child copies/spells a target; the server checks it with a lenient
Hebrew comparison and awards a token on success — fully self-serve.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import children as children_repo
from app.repositories import learning as repo
from app.repositories import tokens as tokens_repo
from app.schemas.learning import ReadingVerdictRequest, WritingAttemptRequest
from app.services.hebrew import matches
from app.services.tts import cache as tts_cache

bp = Blueprint("learning", __name__, url_prefix="/api/learning")

READING_TOKENS_BY_LEVEL = {1: 2, 2: 3, 3: 4}
WRITING_TOKEN = 1


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _level():
    raw = request.args.get("level")
    return int(raw) if raw and raw.isdigit() else None


@bp.get("/reading")
@require_session
def list_reading():
    _ = g.caregiver_id
    texts = []
    for t in repo.list_reading(_level()):
        audio_id = tts_cache.ensure_tts_asset(t["body"])
        texts.append({**t, "audio_url": f"/api/media/{audio_id}" if audio_id else None})
    return jsonify(texts=texts)


@bp.get("/writing")
@require_session
def list_writing():
    _ = g.caregiver_id
    return jsonify(prompts=repo.list_writing(_level()))


@bp.post("/reading/<text_id>/verdict")
@require_caregiver_mode
def reading_verdict(text_id: str):
    data = parse_body(ReadingVerdictRequest)
    _own_child_or_404(data.child_id)
    text = repo.get_reading(text_id)
    if text is None:
        raise ApiError(404, "text_not_found")

    tokens = READING_TOKENS_BY_LEVEL.get(text["level"], 2) if data.verdict == "pass" else 0
    attempt = repo.record_attempt(
        g.db,
        data.child_id,
        kind="reading",
        ref_id=text_id,
        level=text["level"],
        verdict=data.verdict,
        tokens_awarded=tokens,
    )
    if tokens:
        tokens_repo.add_transaction(
            g.db,
            data.child_id,
            delta=tokens,
            kind="exercise",
            reason=f"קריאה: {text['title']}",
            created_by=g.caregiver_id,
        )
    return jsonify(
        attempt=attempt,
        tokens_awarded=tokens,
        balance=tokens_repo.balance(g.db, data.child_id),
    ), 201


@bp.post("/writing/attempt")
@require_session
def writing_attempt():
    data = parse_body(WritingAttemptRequest)
    _own_child_or_404(data.child_id)
    prompt = repo.get_writing(data.prompt_id)
    if prompt is None:
        raise ApiError(404, "prompt_not_found")

    correct = matches(data.submitted, prompt["target"])
    tokens = WRITING_TOKEN if correct else 0
    repo.record_attempt(
        g.db,
        data.child_id,
        kind="writing",
        ref_id=data.prompt_id,
        level=prompt["level"],
        verdict="pass" if correct else "fail",
        tokens_awarded=tokens,
    )
    if tokens:
        tokens_repo.add_transaction(
            g.db,
            data.child_id,
            delta=tokens,
            kind="exercise",
            reason="כתיבה",
            created_by=None,
        )
    return jsonify(
        correct=correct,
        target=prompt["target"] if not correct else None,
        tokens_awarded=tokens,
        balance=tokens_repo.balance(g.db, data.child_id),
    )


@bp.get("/progress")
@require_session
def progress():
    child_id = request.args.get("child_id")
    if not child_id:
        raise ApiError(422, "missing_param", "child_id")
    _own_child_or_404(child_id)
    return jsonify(
        attempts=[{**a, "created_at": str(a["created_at"])} for a in repo.progress(g.db, child_id)]
    )
