from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase

# The stub interviewer asks five things, in this order.
_ANSWERS = [
    "דני",
    "מעבר לגן בבוקר",
    "להיפרד מאמא ברוגע",
    "רגיש לרעש חזק",
    "אין",
]


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _interview(client, child_id):
    """Walk the stub agent's interview; return the message history."""
    msgs = []
    for ans in _ANSWERS:
        msgs.append({"role": "user", "content": ans})
        r = client.post("/api/stories/chat", json={"child_id": child_id, "messages": msgs})
        assert r.status_code == 200
        msgs.append({"role": "assistant", "content": r.get_json()["reply"]})
    return msgs


def test_chat_kickoff_with_no_messages_opens_the_interview(client, caregiver_mode):
    child_id = _child(client)
    r = client.post("/api/stories/chat", json={"child_id": child_id, "messages": []})
    assert r.status_code == 200
    body = r.get_json()
    assert body["reply"] and body["ready"] is False
    assert all(v is None for v in body["slots"].values())


def test_interview_collects_five_slots(client, caregiver_mode):
    child_id = _child(client)
    msgs = []
    for i, ans in enumerate(_ANSWERS):
        msgs.append({"role": "user", "content": ans})
        body = client.post(
            "/api/stories/chat", json={"child_id": child_id, "messages": msgs}
        ).get_json()
        # not ready until the last slot is filled
        assert body["ready"] is (i == len(_ANSWERS) - 1)
        msgs.append({"role": "assistant", "content": body["reply"]})
    assert body["slots"]["protagonist"] == "דני"
    assert body["slots"]["sensory"]


def test_compose_returns_reviewed_text_without_art(client, caregiver_mode):
    child_id = _child(client)
    msgs = _interview(client, child_id)

    r = client.post("/api/stories/compose", json={"child_id": child_id, "messages": msgs})
    assert r.status_code == 201
    body = r.get_json()
    assert "דני" in body["title"]
    assert len(body["pages"]) == 5
    assert all(p["text"] for p in body["pages"])
    # text-first: no illustrations yet
    assert all(p["image_url"] is None for p in body["pages"])
    assert body["art"]["pending_pages"] == [0, 1, 2, 3, 4]
    assert body["review_notes"]
    assert body["situation"] and body["goal"]


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
    # the new illustrate route is cross-tenant safe too
    assert other.post(f"/api/stories/{sid}/illustrate", json={"page_index": 0}).status_code == 404
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
