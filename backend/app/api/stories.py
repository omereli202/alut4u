"""AI social stories.

The caregiver chats with an agent (``/chat``) which interviews them, then
``/compose`` turns the conversation into a structured story, generates an
illustration per page, and saves it. The child reads finished stories in User
Mode. Composing counts against the caregiver's monthly AI quota.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.extensions import limiter
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import stories as repo
from app.schemas.stories import ChatRequest, ComposeRequest
from app.services.ai import get_story_ai
from app.services.ai.base import AIError
from app.services.quotas import QuotaExceeded, check, record
from app.services.tts import cache as tts_cache

bp = Blueprint("stories", __name__, url_prefix="/api/stories")

_MAX_PAGES = 8


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _messages(models) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in models]


@bp.post("/chat")
@require_caregiver_mode
@limiter.limit("40 per hour")
def chat():
    data = parse_body(ChatRequest)
    _own_child_or_404(data.child_id)
    try:
        turn = get_story_ai().interview(_messages(data.messages))
    except AIError as e:
        raise ApiError(502, "ai_unavailable", str(e)) from e
    if turn.llm_tokens:
        record(g.caregiver_id, llm_tokens=turn.llm_tokens)
    return jsonify(reply=turn.reply, ready=turn.ready)


@bp.post("/compose")
@require_caregiver_mode
@limiter.limit("15 per hour; 40 per day")
def compose():
    data = parse_body(ComposeRequest)
    _own_child_or_404(data.child_id)

    try:
        check(g.caregiver_id, images=5, llm_tokens=3000)
    except QuotaExceeded as e:
        raise ApiError(429, "quota_exceeded", e.resource) from e

    ai = get_story_ai()
    try:
        story = ai.compose(_messages(data.messages))
    except AIError as e:
        raise ApiError(502, "ai_unavailable", str(e)) from e

    pages = []
    images = 0
    for page in story.pages[:_MAX_PAGES]:
        image_id = None
        try:
            img, mime = ai.illustrate(page.image_prompt, story.protagonist)
            image_id = repo.store_page_image(data.child_id, img, mime)
            images += 1
        except AIError:
            pass  # a page without art is still a page
        pages.append(
            {
                "text": page.text,
                "image_asset_id": image_id,
                "tts_asset_id": tts_cache.ensure_tts_asset(page.text),
            }
        )

    row = repo.create_story(
        g.db,
        data.child_id,
        {
            "title": story.title,
            "protagonist": story.protagonist,
            "situation": story.situation,
            "goal": story.goal,
            "pages": pages,
            "created_by": g.caregiver_id,
        },
    )
    record(g.caregiver_id, images=images, llm_tokens=3000)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="story.compose",
        target_type="social_story",
        target_id=row["id"],
    )
    return jsonify(_story_out(row)), 201


@bp.get("")
@require_session
def list_stories():
    from flask import request

    child_id = request.args.get("child_id")
    if not child_id:
        raise ApiError(422, "missing_param", "child_id")
    _own_child_or_404(child_id)
    return jsonify(
        stories=[
            {**s, "created_at": str(s["created_at"])} for s in repo.list_stories(g.db, child_id)
        ]
    )


@bp.get("/<story_id>")
@require_session
def get_story(story_id: str):
    row = repo.get_story(g.db, story_id)
    if row is None:
        raise ApiError(404, "not_found")
    return jsonify(_story_out(row))


@bp.delete("/<story_id>")
@require_caregiver_mode
def delete_story(story_id: str):
    if repo.get_story(g.db, story_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_story(g.db, story_id)
    return "", 204


def _story_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "protagonist": row.get("protagonist"),
        "pages": [
            {
                "text": p["text"],
                "image_url": f"/api/media/{p['image_asset_id']}"
                if p.get("image_asset_id")
                else None,
                "audio_url": f"/api/media/{p['tts_asset_id']}" if p.get("tts_asset_id") else None,
            }
            for p in row["pages"]
        ],
        "created_at": str(row["created_at"]),
    }
