from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _interview(client, child_id):
    """Walk the stub agent's 3-question interview; return the message history."""
    msgs = []
    answers = ["דני", "מעבר לגן בבוקר", "להיפרד מאמא ברוגע"]
    for ans in answers:
        # send the answer, get the next question
        msgs.append({"role": "user", "content": ans})
        r = client.post("/api/stories/chat", json={"child_id": child_id, "messages": msgs})
        assert r.status_code == 200
        msgs.append({"role": "assistant", "content": r.get_json()["reply"]})
    return msgs


def test_interview_then_compose(client, caregiver_mode):
    child_id = _child(client)
    msgs = _interview(client, child_id)

    # after 3 answers the agent is ready
    last = client.post(
        "/api/stories/chat", json={"child_id": child_id, "messages": msgs}
    ).get_json()
    assert last["ready"] is True

    story = client.post("/api/stories/compose", json={"child_id": child_id, "messages": msgs})
    assert story.status_code == 201
    body = story.get_json()
    assert "דני" in body["title"]
    assert len(body["pages"]) == 5
    assert all(p["text"] for p in body["pages"])
    # stub illustrates every page
    assert all(p["image_url"] and p["image_url"].startswith("/api/media/") for p in body["pages"])

    # the child can read it, and the images resolve
    listed = client.get(f"/api/stories?child_id={child_id}").get_json()["stories"]
    assert [s["title"] for s in listed] == [body["title"]]
    got = client.get(f"/api/stories/{body['id']}").get_json()
    assert got["pages"][0]["image_url"]
    img = client.get(got["pages"][0]["image_url"])
    assert img.status_code == 200
    assert img.mimetype == "image/svg+xml"


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
    # but chatting / composing does not
    assert (
        client.post("/api/stories/chat", json={"child_id": child_id, "messages": msgs}).status_code
        == 403
    )


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


def test_delete_story(client, caregiver_mode):
    child_id = _child(client)
    msgs = _interview(client, child_id)
    sid = client.post(
        "/api/stories/compose", json={"child_id": child_id, "messages": msgs}
    ).get_json()["id"]
    assert client.delete(f"/api/stories/{sid}").status_code == 204
    assert client.get(f"/api/stories/{sid}").status_code == 404
