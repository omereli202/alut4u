from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase

# The name is prefilled from the child record — never asked. The interviewer
# then walks: situation, schedule, goal, sensory, triggers, and a closing
# "anything else?" question.
_CHILD_NAME = "יובל"
_ANSWERS = [
    "מעבר לגן בבוקר",
    "מחר בבוקר",
    "להיפרד מאמא ברוגע",
    "רגיש לרעש חזק",
    "אין",
    "לא",
]


def _child(client) -> str:
    return client.post(
        "/api/children", json={"name": _CHILD_NAME, "consent_basis": "parent"}
    ).get_json()["id"]


def _interview(client, child_id):
    """Walk the stub agent's interview; return the message history."""
    msgs = []
    for ans in _ANSWERS:
        msgs.append({"role": "user", "content": ans})
        r = client.post("/api/stories/chat", json={"child_id": child_id, "messages": msgs})
        assert r.status_code == 200
        msgs.append({"role": "assistant", "content": r.get_json()["reply"]})
    return msgs


def test_chat_kickoff_prefills_the_name_and_opens_on_the_situation(client, caregiver_mode):
    child_id = _child(client)
    r = client.post("/api/stories/chat", json={"child_id": child_id, "messages": []})
    assert r.status_code == 200
    body = r.get_json()
    assert body["reply"] and body["ready"] is False
    # the name is known upfront, never asked
    assert body["slots"]["protagonist"] == _CHILD_NAME
    assert body["slots"]["situation"] is None


def test_interview_collects_all_slots(client, caregiver_mode):
    child_id = _child(client)
    msgs = []
    for i, ans in enumerate(_ANSWERS):
        msgs.append({"role": "user", "content": ans})
        body = client.post(
            "/api/stories/chat", json={"child_id": child_id, "messages": msgs}
        ).get_json()
        # ready only after the closing "anything else?" answer
        assert body["ready"] is (i == len(_ANSWERS) - 1)
        msgs.append({"role": "assistant", "content": body["reply"]})
    assert body["slots"]["protagonist"] == _CHILD_NAME
    assert body["slots"]["schedule"] == "מחר בבוקר"
    assert body["slots"]["sensory"]


def test_compose_returns_reviewed_text_without_art(client, caregiver_mode):
    child_id = _child(client)
    msgs = _interview(client, child_id)

    r = client.post("/api/stories/compose", json={"child_id": child_id, "messages": msgs})
    assert r.status_code == 201
    body = r.get_json()
    assert _CHILD_NAME in body["title"]
    assert len(body["pages"]) == 5
    assert all(p["text"] for p in body["pages"])
    # text-first: no illustrations yet
    assert all(p["image_url"] is None for p in body["pages"])
    assert body["art"]["pending_pages"] == [0, 1, 2, 3, 4]
    assert body["review_notes"]
    assert body["situation"] and body["goal"]
    assert "schedule" not in body  # no longer surfaced as its own field
    # the timing is woven in somewhere, but not forced into the opening line
    joined = " ".join(p["text"] for p in body["pages"])
    assert "מחר בבוקר" in joined
    assert "מחר בבוקר" not in body["pages"][0]["text"]


def test_edit_story_text(client, caregiver_mode):
    child_id = _child(client)
    story = client.post(
        "/api/stories/compose",
        json={"child_id": child_id, "messages": _interview(client, child_id)},
    ).get_json()
    sid = story["id"]
    # illustrate page 0 so we can prove the image survives an edit
    client.post(f"/api/stories/{sid}/illustrate", json={"page_index": 0})

    before = client.get(f"/api/stories/{sid}").get_json()
    new_pages = [{"text": p["text"]} for p in before["pages"]]
    new_pages[1]["text"] = "טקסט חדש לגמרי לעמוד השני."
    r = client.patch(f"/api/stories/{sid}", json={"title": "כותרת חדשה", "pages": new_pages})
    assert r.status_code == 200

    after = client.get(f"/api/stories/{sid}").get_json()
    assert after["title"] == "כותרת חדשה"
    assert after["pages"][1]["text"] == "טקסט חדש לגמרי לעמוד השני."
    assert after["pages"][0]["text"] == before["pages"][0]["text"]  # untouched
    assert after["pages"][0]["image_url"] == before["pages"][0]["image_url"]  # image kept

    # wrong page count is rejected
    short = client.patch(f"/api/stories/{sid}", json={"pages": [{"text": "רק אחד"}]})
    assert short.status_code == 422


def test_illustrate_fills_pages_one_at_a_time(client, caregiver_mode):
    child_id = _child(client)
    story = client.post(
        "/api/stories/compose",
        json={"child_id": child_id, "messages": _interview(client, child_id)},
    ).get_json()

    for n, idx in enumerate(list(story["art"]["pending_pages"])):
        r = client.post(f"/api/stories/{story['id']}/illustrate", json={"page_index": idx})
        assert r.status_code == 200
        assert r.get_json()["image_url"].startswith("/api/media/")
        assert len(r.get_json()["art"]["pending_pages"]) == 4 - n

    got = client.get(f"/api/stories/{story['id']}").get_json()
    assert all(p["image_url"] for p in got["pages"])
    img = client.get(got["pages"][0]["image_url"])
    assert img.status_code == 200
    assert img.mimetype == "image/svg+xml"


def test_illustrate_is_idempotent(client, caregiver_mode, app):
    from app.repositories import usage as usage_repo

    cg = caregiver_mode["caregiver_id"]
    child_id = _child(client)
    story = client.post(
        "/api/stories/compose",
        json={"child_id": child_id, "messages": _interview(client, child_id)},
    ).get_json()

    # get_system() reads via the service role, so it needs current_settings() to
    # resolve — i.e. an app context (that's what the `app` fixture is for).
    with app.app_context():
        first = client.post(f"/api/stories/{story['id']}/illustrate", json={"page_index": 0})
        assert first.status_code == 200
        before = usage_repo.get_system(cg)["image_count"]

        again = client.post(f"/api/stories/{story['id']}/illustrate", json={"page_index": 0})
        assert again.status_code == 409
        assert usage_repo.get_system(cg)["image_count"] == before


def test_illustrate_without_index_picks_next_pending(client, caregiver_mode):
    child_id = _child(client)
    story = client.post(
        "/api/stories/compose",
        json={"child_id": child_id, "messages": _interview(client, child_id)},
    ).get_json()
    r = client.post(f"/api/stories/{story['id']}/illustrate", json={})
    assert r.status_code == 200
    assert r.get_json()["page_index"] == 0


def test_stories_need_caregiver_mode(client, signed_up):
    child_id = client.post("/api/children", json={"name": "x", "consent_basis": "parent"})
    assert child_id.status_code == 403  # can't even create the child


def test_reads_allowed_in_user_mode(client, caregiver_mode):
    child_id = _child(client)
    msgs = _interview(client, child_id)
    sid = client.post(
        "/api/stories/compose", json={"child_id": child_id, "messages": msgs}
    ).get_json()["id"]

    client.delete("/api/auth/pin/elevation")  # → User Mode
    assert client.get(f"/api/stories?child_id={child_id}").status_code == 200
    assert client.get(f"/api/stories/{sid}").status_code == 200
    # but chatting / composing / illustrating does not
    assert (
        client.post("/api/stories/chat", json={"child_id": child_id, "messages": msgs}).status_code
        == 403
    )
    assert client.post(f"/api/stories/{sid}/illustrate", json={"page_index": 0}).status_code == 403


def test_stories_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)
    msgs = _interview(client, child_id)
    sid = client.post(
        "/api/stories/compose", json={"child_id": child_id, "messages": msgs}
    ).get_json()["id"]

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"st-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1593"})
    other.post("/api/auth/pin", json={"pin": "1593"})
    assert other.get(f"/api/stories?child_id={child_id}").status_code == 404
    assert other.get(f"/api/stories/{sid}").status_code == 404
    # the new illustrate + edit routes are cross-tenant safe too
    assert other.post(f"/api/stories/{sid}/illustrate", json={"page_index": 0}).status_code == 404
    assert other.patch(f"/api/stories/{sid}", json={"pages": [{"text": "x"}]}).status_code == 404
    # and A's story still has no art
    assert client.get(f"/api/stories/{sid}").get_json()["pages"][0]["image_url"] is None


def test_delete_story(client, caregiver_mode):
    child_id = _child(client)
    msgs = _interview(client, child_id)
    sid = client.post(
        "/api/stories/compose", json={"child_id": child_id, "messages": msgs}
    ).get_json()["id"]
    assert client.delete(f"/api/stories/{sid}").status_code == 204
    assert client.get(f"/api/stories/{sid}").status_code == 404


# --- content-safety guardrail ------------------------------------------
#
# StubStoryAI has no model to run the real content policy (that lives in
# gemini_story.py's prompts) — it recognises a literal "[[refuse]]" marker in
# any message so these tests can exercise the refusal path end to end without
# a Gemini key. See stub_story.py.

_REFUSE_MARKER_MESSAGES = [
    {"role": "user", "content": "מעבר לגן בבוקר"},
    {"role": "assistant", "content": "מתי?"},
    {"role": "user", "content": "[[refuse]] מחר בבוקר"},
]


def test_compose_content_refusal_returns_422_and_saves_nothing(client, caregiver_mode, monkeypatch):
    from app.api import stories as stories_api

    logged = []
    monkeypatch.setattr(stories_api.audit_repo, "log", lambda **kw: logged.append(kw))

    child_id = _child(client)
    r = client.post(
        "/api/stories/compose",
        json={"child_id": child_id, "messages": _REFUSE_MARKER_MESSAGES},
    )
    assert r.status_code == 422
    body = r.get_json()
    assert body["error"] == "content_declined"
    assert "detail" not in body

    assert client.get(f"/api/stories?child_id={child_id}").get_json()["stories"] == []

    # audit_repo.log is a shared module — child creation logs its own entry
    # too, so isolate the one this refusal wrote.
    declined = [row for row in logged if row["action"] == "story.content_declined"]
    assert len(declined) == 1
    assert declined[0]["detail"] == {"stage": "compose", "reason": "stub_marker"}
    assert declined[0]["target_id"] == child_id


def test_chat_content_refusal_returns_422(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/stories/chat",
        json={"child_id": child_id, "messages": [{"role": "user", "content": "[[refuse]]"}]},
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "content_declined"


def test_illustrate_content_refusal_returns_422_and_leaves_the_page_bare(
    client, caregiver_mode, app, monkeypatch
):
    from app.repositories import usage as usage_repo
    from app.services.ai.base import ContentRefused
    from app.services.ai.stub_story import StubStoryAI

    def _raise(*a, **kw):
        raise ContentRefused("stub_marker", stage="illustrate")

    monkeypatch.setattr(StubStoryAI, "illustrate", _raise)

    cg = caregiver_mode["caregiver_id"]
    child_id = _child(client)
    story = client.post(
        "/api/stories/compose",
        json={"child_id": child_id, "messages": _interview(client, child_id)},
    ).get_json()

    with app.app_context():
        before = usage_repo.get_system(cg)["image_count"]
        r = client.post(f"/api/stories/{story['id']}/illustrate", json={"page_index": 0})
        assert r.status_code == 422
        assert r.get_json()["error"] == "content_declined"
        assert usage_repo.get_system(cg)["image_count"] == before

    got = client.get(f"/api/stories/{story['id']}").get_json()
    assert got["pages"][0]["image_url"] is None


def test_compose_refusal_still_counts_llm_tokens(client, caregiver_mode, app):
    from app.repositories import usage as usage_repo

    cg = caregiver_mode["caregiver_id"]
    child_id = _child(client)
    with app.app_context():
        before = usage_repo.get_system(cg)["llm_tokens"]
        r = client.post(
            "/api/stories/compose",
            json={"child_id": child_id, "messages": _REFUSE_MARKER_MESSAGES},
        )
        assert r.status_code == 422
        # the work happened (StubStoryAI reports 0 tokens, so the route falls
        # back to the pre-flight budget) even though nothing was saved
        assert usage_repo.get_system(cg)["llm_tokens"] > before
