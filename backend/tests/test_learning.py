from __future__ import annotations

from app.services.hebrew import matches
from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def test_hebrew_normalization():
    assert matches("שלומ", "שלום")  # missing final form
    assert matches(" בית. ", "בית")  # trim + punctuation
    assert matches("אמא", "אִמָּא")  # niqqud on target
    assert not matches("שלום", "בית")


def test_reading_verdict_awards_tokens(client, caregiver_mode):
    child_id = _child(client)
    texts = client.get("/api/learning/reading").get_json()["texts"]
    lvl2 = next(t for t in texts if t["level"] == 2)

    r = client.post(
        f"/api/learning/reading/{lvl2['id']}/verdict",
        json={"child_id": child_id, "verdict": "pass"},
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body["tokens_awarded"] == 3  # level 2
    assert body["balance"] == 3

    # a fail records but awards nothing
    fail = client.post(
        f"/api/learning/reading/{lvl2['id']}/verdict",
        json={"child_id": child_id, "verdict": "fail"},
    ).get_json()
    assert fail["tokens_awarded"] == 0
    assert fail["balance"] == 3


def test_reading_verdict_needs_caregiver_mode(client, caregiver_mode):
    child_id = _child(client)
    tid = client.get("/api/learning/reading").get_json()["texts"][0]["id"]
    client.delete("/api/auth/pin/elevation")
    assert (
        client.post(
            f"/api/learning/reading/{tid}/verdict", json={"child_id": child_id, "verdict": "pass"}
        ).status_code
        == 403
    )


def test_writing_attempt_is_self_serve_and_lenient(client, caregiver_mode):
    child_id = _child(client)
    prompts = client.get("/api/learning/writing").get_json()["prompts"]
    p = next(x for x in prompts if x["id"] == "w1-shalom")
    client.delete("/api/auth/pin/elevation")  # User Mode

    wrong = client.post(
        "/api/learning/writing/attempt",
        json={"child_id": child_id, "prompt_id": p["id"], "submitted": "בית"},
    ).get_json()
    assert wrong["correct"] is False
    assert wrong["target"] == "שלום"
    assert wrong["tokens_awarded"] == 0

    # missing final mem still passes
    ok = client.post(
        "/api/learning/writing/attempt",
        json={"child_id": child_id, "prompt_id": p["id"], "submitted": "שלומ"},
    ).get_json()
    assert ok["correct"] is True
    assert ok["tokens_awarded"] == 1
    assert ok["balance"] == 1


def test_progress_lists_attempts(client, caregiver_mode):
    child_id = _child(client)
    tid = client.get("/api/learning/reading").get_json()["texts"][0]["id"]
    client.post(
        f"/api/learning/reading/{tid}/verdict", json={"child_id": child_id, "verdict": "pass"}
    )
    attempts = client.get(f"/api/learning/progress?child_id={child_id}").get_json()["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["kind"] == "reading"


def test_learning_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)
    tid = client.get("/api/learning/reading").get_json()["texts"][0]["id"]

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"ln-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1938"})
    other.post("/api/auth/pin", json={"pin": "1938"})
    assert (
        other.post(
            f"/api/learning/reading/{tid}/verdict", json={"child_id": child_id, "verdict": "pass"}
        ).status_code
        == 404
    )
    assert other.get(f"/api/learning/progress?child_id={child_id}").status_code == 404
