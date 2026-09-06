"""Reading & typing practice ("קריאה והקלדה").

Level-based: the child picks a level, works through tasks, and each completed
task disappears (no repeats). Tokens are **not** awarded per task — every 3
completed tasks in the same (kind, level) is a milestone worth a fixed number
of tokens, released only when the caregiver enters their PIN.

Reading has no automatic check (no speech recognition — privacy decision); the
child self-marks a text read. Typing is checked server-side by a lenient Hebrew
comparison. The caregiver's judgement happens at the milestone, where they are
present to enter the PIN.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import learning as repo
from app.repositories import tokens as tokens_repo
from app.schemas.learning import (
    LearningClaimRequest,
    ReadingCreate,
    ReadingDoneRequest,
    WritingAttemptRequest,
    WritingCreate,
)
from app.services.hebrew import matches
from app.services.tts import cache as tts_cache

bp = Blueprint("learning", __name__, url_prefix="/api/learning")

MILESTONE_SIZE = 3  # tasks per milestone
MILESTONE_TOKENS = 3  # tokens per milestone

_LEVEL_HE = {1: "רמה 1", 2: "רמה 2", 3: "רמה 3"}
_KIND_HE = {"reading": "קריאה", "writing": "הקלדה"}


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


def _level_arg() -> int:
    raw = request.args.get("level", "1")
    if not raw.isdigit() or not (1 <= int(raw) <= 3):
        raise ApiError(422, "bad_level")
    return int(raw)


def _progress(child_id: str, kind: str, level: int) -> dict:
    completed = repo.completion_count(g.db, child_id, kind, level)
    claimed = repo.get_claimed(g.db, child_id, kind, level)
    return {
        "completed": completed,
        "toward_next": completed % MILESTONE_SIZE,
        "unclaimed": completed // MILESTONE_SIZE - claimed,
    }


# --- lists ----------------------------------------------------------


@bp.get("/reading")
@require_session
def list_reading():
    child_id, level = _arg("child_id"), _level_arg()
    _own_child_or_404(child_id)
    done = repo.completed_task_ids(g.db, child_id, "reading", level)
    tasks = []
    for t in repo.list_reading(g.db, child_id, level):
        if t["id"] in done:
            continue
        audio_id = t.get("tts_asset_id") or tts_cache.ensure_tts_asset(t["body"])
        tasks.append(
            {
                "id": t["id"],
                "level": t["level"],
                "title": t["title"],
                "body": t["body"],
                "audio_url": f"/api/media/{audio_id}" if audio_id else None,
            }
        )
    return jsonify(tasks=tasks, progress=_progress(child_id, "reading", level))


@bp.get("/writing")
@require_session
def list_writing():
    child_id, level = _arg("child_id"), _level_arg()
    _own_child_or_404(child_id)
    done = repo.completed_task_ids(g.db, child_id, "writing", level)
    tasks = [
        {"id": p["id"], "level": p["level"], "hint": p["hint"]}
        for p in repo.list_writing(g.db, child_id, level)
        if p["id"] not in done
    ]
    return jsonify(tasks=tasks, progress=_progress(child_id, "writing", level))


# --- completing a task --------------------------------------------


def _visible_task(getter, task_id: str, child_id: str) -> dict:
    task = getter(g.db, task_id)
    if task is None or task.get("child_id") not in (None, child_id):
        raise ApiError(404, "task_not_found")
    return task


@bp.post("/reading/<text_id>/done")
@require_session
def reading_done(text_id: str):
    data = parse_body(ReadingDoneRequest)
    _own_child_or_404(data.child_id)
    text = _visible_task(repo.get_reading, text_id, data.child_id)
    repo.record_attempt(
        g.db, data.child_id, kind="reading", ref_id=text_id, level=text["level"], verdict="pass"
    )
    repo.record_completion(g.db, data.child_id, text_id, "reading", text["level"])
    return jsonify(progress=_progress(data.child_id, "reading", text["level"])), 201


@bp.post("/writing/attempt")
@require_session
def writing_attempt():
    data = parse_body(WritingAttemptRequest)
    _own_child_or_404(data.child_id)
    prompt = _visible_task(repo.get_writing, data.prompt_id, data.child_id)

    correct = matches(data.submitted, prompt["target"])
    repo.record_attempt(
        g.db,
        data.child_id,
        kind="writing",
        ref_id=data.prompt_id,
        level=prompt["level"],
        verdict="pass" if correct else "fail",
    )
    if correct:
        repo.record_completion(g.db, data.child_id, data.prompt_id, "writing", prompt["level"])
    return jsonify(
        correct=correct,
        target=None if correct else prompt["target"],
        progress=_progress(data.child_id, "writing", prompt["level"]),
    )


# --- milestone claim (caregiver PIN) ------------------------------


@bp.post("/claim")
@require_caregiver_mode
def claim():
    data = parse_body(LearningClaimRequest)
    _own_child_or_404(data.child_id)
    completed = repo.completion_count(g.db, data.child_id, data.kind, data.level)
    claimed = repo.get_claimed(g.db, data.child_id, data.kind, data.level)
    unclaimed = completed // MILESTONE_SIZE - claimed
    if unclaimed <= 0:
        raise ApiError(409, "nothing_to_claim")

    tokens = MILESTONE_TOKENS * unclaimed
    tokens_repo.add_transaction(
        g.db,
        data.child_id,
        delta=tokens,
        kind="exercise",
        reason=f"{_KIND_HE[data.kind]} — {_LEVEL_HE[data.level]}",
        created_by=g.caregiver_id,
    )
    repo.set_claimed(g.db, data.child_id, data.kind, data.level, completed // MILESTONE_SIZE)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="learning.claim",
        target_type="child",
        target_id=data.child_id,
        detail={"kind": data.kind, "level": data.level, "tokens": tokens},
    )
    return jsonify(
        tokens_awarded=tokens,
        balance=tokens_repo.balance(g.db, data.child_id),
        progress=_progress(data.child_id, data.kind, data.level),
    ), 201


# --- caregiver content editor ------------------------------------


@bp.get("/tasks")
@require_caregiver_mode
def list_tasks():
    child_id, level = _arg("child_id"), _level_arg()
    kind = _arg("kind")
    if kind not in ("reading", "writing"):
        raise ApiError(422, "bad_kind")
    _own_child_or_404(child_id)
    tasks = [
        {**t, "owned": t.get("child_id") == child_id}
        for t in repo.list_tasks(g.db, kind, child_id, level)
    ]
    return jsonify(tasks=tasks)


@bp.post("/reading")
@require_caregiver_mode
def create_reading():
    data = parse_body(ReadingCreate)
    _own_child_or_404(data.child_id)
    row = repo.create_reading(
        g.db,
        data.child_id,
        g.caregiver_id,
        {
            "level": data.level,
            "title": data.title,
            "body": data.body,
            "tts_asset_id": tts_cache.ensure_tts_asset(data.body),
        },
    )
    return jsonify(row), 201


@bp.post("/writing")
@require_caregiver_mode
def create_writing():
    data = parse_body(WritingCreate)
    _own_child_or_404(data.child_id)
    row = repo.create_writing(
        g.db,
        data.child_id,
        g.caregiver_id,
        {"level": data.level, "hint": data.hint, "target": data.target},
    )
    return jsonify(row), 201


@bp.delete("/reading/<text_id>")
@require_caregiver_mode
def delete_reading(text_id: str):
    repo.delete_task(g.db, "reading", text_id)
    return "", 204


@bp.delete("/writing/<prompt_id>")
@require_caregiver_mode
def delete_writing(prompt_id: str):
    repo.delete_task(g.db, "writing", prompt_id)
    return "", 204


# --- caregiver progress view -------------------------------------


@bp.get("/progress")
@require_session
def progress():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(levels=repo.progress_all(g.db, child_id))
