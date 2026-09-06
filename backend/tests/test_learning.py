from __future__ import annotations

from app.services.hebrew import matches
from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _reading_ids(client, child_id, level=1):
    r = client.get(f"/api/learning/reading?child_id={child_id}&level={level}").get_json()
    return [t["id"] for t in r["tasks"]], r["progress"]


def test_hebrew_normalization():
    assert matches("שלומ", "שלום")  # missing final form
    assert matches(" בית. ", "בית")  # trim + punctuation
    assert matches("אמא", "אִמָּא")  # niqqud on target
    assert not matches("שלום", "בית")


def test_reading_done_completes_and_does_not_repeat(client, caregiver_mode):
    child_id = _child(client)
    ids, prog = _reading_ids(client, child_id, 1)
    assert prog == {"completed": 0, "toward_next": 0, "unclaimed": 0}
    assert len(ids) >= 3

    r = client.post(f"/api/learning/reading/{ids[0]}/done", json={"child_id": child_id})
    assert r.status_code == 201
    assert r.get_json()["progress"]["completed"] == 1

    # second "done" on the same task is idempotent
    client.post(f"/api/learning/reading/{ids[0]}/done", json={"child_id": child_id})
    ids2, prog2 = _reading_ids(client, child_id, 1)
    assert prog2["completed"] == 1
    assert ids[0] not in ids2  # completed task is gone from the list


def test_writing_attempt_completes_only_when_correct(client, caregiver_mode):
    child_id = _child(client)
    client.delete("/api/auth/pin/elevation")  # User Mode

    wrong = client.post(
        "/api/learning/writing/attempt",
        json={"child_id": child_id, "prompt_id": "w1-shalom", "submitted": "בית"},
    ).get_json()
    assert wrong["correct"] is False and wrong["target"] == "שלום"
    assert wrong["progress"]["completed"] == 0

    ok = client.post(
        "/api/learning/writing/attempt",
        json={"child_id": child_id, "prompt_id": "w1-shalom", "submitted": "שלומ"},
    ).get_json()
    assert ok["correct"] is True and ok["target"] is None
    assert ok["progress"]["completed"] == 1

    tasks = client.get(f"/api/learning/writing?child_id={child_id}&level=1").get_json()["tasks"]
    assert "w1-shalom" not in [t["id"] for t in tasks]


def test_milestone_claim(client, caregiver_mode):
    child_id = _child(client)
    ids, _ = _reading_ids(client, child_id, 1)

    for tid in ids[:2]:
        client.post(f"/api/learning/reading/{tid}/done", json={"child_id": child_id})
    _, prog = _reading_ids(client, child_id, 1)
    assert prog == {"completed": 2, "toward_next": 2, "unclaimed": 0}

    client.post(f"/api/learning/reading/{ids[2]}/done", json={"child_id": child_id})
    _, prog = _reading_ids(client, child_id, 1)
    assert prog["unclaimed"] == 1

    claimed = client.post(
        "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 1}
    )
    assert claimed.status_code == 201
    body = claimed.get_json()
    assert body["tokens_awarded"] == 3 and body["balance"] == 3
    assert body["progress"] == {"completed": 3, "toward_next": 0, "unclaimed": 0}

    # nothing left to claim
    again = client.post(
        "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 1}
    )
    assert again.status_code == 409 and again.get_json()["error"] == "nothing_to_claim"

    # three more completions -> another milestone
    for tid in ids[3:6]:
        client.post(f"/api/learning/reading/{tid}/done", json={"child_id": child_id})
    body = client.post(
        "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 1}
    ).get_json()
    assert body["tokens_awarded"] == 3 and body["balance"] == 6


def test_claim_separates_kind_and_level(client, caregiver_mode):
    child_id = _child(client)
    ids, _ = _reading_ids(client, child_id, 1)
    for tid in ids[:3]:
        client.post(f"/api/learning/reading/{tid}/done", json={"child_id": child_id})

    # level 2 has nothing
    assert (
        client.post(
            "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 2}
        ).status_code
        == 409
    )
    # writing has nothing
    assert (
        client.post(
            "/api/learning/claim", json={"child_id": child_id, "kind": "writing", "level": 1}
        ).status_code
        == 409
    )
    # reading level 1 pays
    assert (
        client.post(
            "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 1}
        ).status_code
        == 201
    )


def test_claim_needs_caregiver_mode(client, caregiver_mode):
    child_id = _child(client)
    ids, _ = _reading_ids(client, child_id, 1)
    for tid in ids[:3]:
        client.post(f"/api/learning/reading/{tid}/done", json={"child_id": child_id})
    client.delete("/api/auth/pin/elevation")
    assert (
        client.post(
            "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 1}
        ).status_code
        == 403
    )


def test_caregiver_editor_crud(client, caregiver_mode):
    child_id = _child(client)
    created = client.post(
        "/api/learning/reading",
        json={"child_id": child_id, "level": 2, "title": "שלי", "body": "טקסט קצר לתרגול."},
    )
    assert created.status_code == 201
    new_id = created.get_json()["id"]
    assert created.get_json()["tts_asset_id"]  # TTS pre-generated

    # appears for this child (level 2), tagged owned
    tasks = client.get(f"/api/learning/tasks?child_id={child_id}&kind=reading&level=2").get_json()[
        "tasks"
    ]
    mine = next(t for t in tasks if t["id"] == new_id)
    assert mine["owned"] is True
    assert any(t["owned"] is False for t in tasks)  # bundled rows present too

    # also in the child-facing list
    ids, _ = _reading_ids(client, child_id, 2)
    assert new_id in ids

    assert client.delete(f"/api/learning/reading/{new_id}").status_code == 204
    ids, _ = _reading_ids(client, child_id, 2)
    assert new_id not in ids


def test_learning_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)

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
        other.post("/api/learning/reading/r1-sun/done", json={"child_id": child_id}).status_code
        == 404
    )
    assert (
        other.post(
            "/api/learning/reading",
            json={"child_id": child_id, "level": 1, "title": "x", "body": "y"},
        ).status_code
        == 404
    )
    assert (
        other.post(
            "/api/learning/claim", json={"child_id": child_id, "kind": "reading", "level": 1}
        ).status_code
        == 404
    )
    assert other.get(f"/api/learning/progress?child_id={child_id}").status_code == 404
