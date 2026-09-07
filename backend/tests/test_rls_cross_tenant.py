"""The tenancy-isolation test. This protects minors' data and must stay green.

Caregiver A creates a child. Caregiver B must not be able to read, update, or
delete it through any endpoint, and must not be able to see the row even with a
direct RLS-scoped Supabase client.
"""

from __future__ import annotations

import uuid

import pytest

from app.auth import sessions as session_svc
from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _signup(client, email):
    r = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "test-password-123",
            "display_name": "cg",
            "accept_terms": True,
        },
    )
    assert r.status_code == 201
    return r.get_json()["caregiver_id"]


def _enter_caregiver_mode(client, pin="2580"):
    assert client.put("/api/auth/pin", json={"pin": pin}).status_code == 204
    assert client.post("/api/auth/pin", json={"pin": pin}).status_code == 200


@pytest.fixture
def two_caregivers(app):
    a, b = app.test_client(), app.test_client()
    email_a = f"a-{uuid.uuid4().hex[:10]}@example.com"
    email_b = f"b-{uuid.uuid4().hex[:10]}@example.com"
    _signup(a, email_a)
    _signup(b, email_b)
    _enter_caregiver_mode(a)
    _enter_caregiver_mode(b, pin="1357")

    child = a.post("/api/children", json={"name": "child-A", "consent_basis": "parent"}).get_json()
    return {"a": a, "b": b, "child_id": child["id"], "app": app}


def test_b_cannot_read_a_child_via_api(two_caregivers):
    b, cid = two_caregivers["b"], two_caregivers["child_id"]
    assert b.get(f"/api/children/{cid}").status_code == 404
    assert b.get(f"/api/children/{cid}/modules").status_code == 404


def test_b_cannot_mutate_a_child_via_api(two_caregivers):
    b, cid = two_caregivers["b"], two_caregivers["child_id"]
    assert b.patch(f"/api/children/{cid}", json={"name": "hijacked"}).status_code == 404
    assert b.put(f"/api/children/{cid}/modules", json={"aac_enabled": False}).status_code == 404
    assert b.delete(f"/api/children/{cid}").status_code == 404


def test_b_child_list_is_empty(two_caregivers):
    assert two_caregivers["b"].get("/api/children").get_json()["children"] == []


def test_rls_hides_the_row_from_a_direct_client(two_caregivers):
    """Even with a valid Supabase client carrying B's JWT, A's child is invisible."""
    app, b, cid = two_caregivers["app"], two_caregivers["b"], two_caregivers["child_id"]
    settings = app.config["SETTINGS"]

    with b.session_transaction() as sess:
        sid = sess["sid"]
    with app.app_context():
        resolved = session_svc.resolve(sid, settings)
        rows = resolved.db.table("children").select("*").eq("id", cid).execute().data
    assert rows == []


def test_a_still_owns_its_child(two_caregivers):
    a, cid = two_caregivers["a"], two_caregivers["child_id"]
    assert a.get(f"/api/children/{cid}").status_code == 200


def test_b_cannot_touch_a_rules_settings(two_caregivers):
    b, cid = two_caregivers["b"], two_caregivers["child_id"]
    assert b.get(f"/api/tokens/settings?child_id={cid}").status_code == 404
    assert (
        b.put("/api/tokens/settings", json={"child_id": cid, "daily_bonus": 5}).status_code == 404
    )
    assert (
        b.post("/api/tokens/rules/bonus", json={"child_id": cid, "on": "2026-09-06"}).status_code
        == 404
    )


def test_b_cannot_touch_a_learning(two_caregivers):
    b, cid = two_caregivers["b"], two_caregivers["child_id"]
    assert b.get(f"/api/learning/reading?child_id={cid}&level=1").status_code == 404
    assert (
        b.post(
            "/api/learning/reading",
            json={"child_id": cid, "level": 1, "title": "x", "body": "y"},
        ).status_code
        == 404
    )
    assert (
        b.post(
            "/api/learning/claim", json={"child_id": cid, "kind": "reading", "level": 1}
        ).status_code
        == 404
    )


def _a_note(a, cid):
    nid = str(uuid.uuid4())
    body = {
        "child_id": cid,
        "note_id": nid,
        "title": "שלי",
        "blocks": [{"t": "p", "s": "טקסט של קרייגיבר A"}],
        "rev": 1,
    }
    assert a.post("/api/typing/notes", json=body).status_code == 200
    return nid


def test_b_cannot_touch_a_typing_notes(two_caregivers):
    a, b, cid = two_caregivers["a"], two_caregivers["b"], two_caregivers["child_id"]
    nid = _a_note(a, cid)

    assert b.get(f"/api/typing/notes?child_id={cid}").status_code == 404
    assert b.get(f"/api/typing/notes/{nid}").status_code == 404
    assert (
        b.post(
            "/api/typing/notes",
            json={
                "child_id": cid,
                "note_id": str(uuid.uuid4()),
                "blocks": [{"t": "p", "s": "x"}],
                "rev": 1,
            },
        ).status_code
        == 404
    )
    assert b.delete(f"/api/typing/notes/{nid}").status_code == 404
    assert b.get(f"/api/typing/settings?child_id={cid}").status_code == 404
    assert (
        b.put("/api/typing/settings", json={"child_id": cid, "font_family": "heebo"}).status_code
        == 404
    )
    # A's note is untouched
    assert a.get(f"/api/typing/notes/{nid}").get_json()["blocks"][0]["s"] == "טקסט של קרייגיבר A"


def test_b_cannot_hijack_a_note_id_via_upsert(two_caregivers):
    """B posts A's note id with B's own child_id — must fail, not reparent."""
    a, b = two_caregivers["a"], two_caregivers["b"]
    a_cid = two_caregivers["child_id"]
    nid = _a_note(a, a_cid)

    b_cid = b.post("/api/children", json={"name": "child-B", "consent_basis": "parent"}).get_json()[
        "id"
    ]
    r = b.post(
        "/api/typing/notes",
        json={
            "child_id": b_cid,
            "note_id": nid,
            "title": "hijacked",
            "blocks": [{"t": "p", "s": "לא שלי"}],
            "rev": 99,
        },
    )
    assert r.status_code in (404, 409)
    assert a.get(f"/api/typing/notes/{nid}").get_json()["blocks"][0]["s"] == "טקסט של קרייגיבר A"


def test_rls_hides_a_note_from_a_direct_client(two_caregivers):
    app, a, b = two_caregivers["app"], two_caregivers["a"], two_caregivers["b"]
    nid = _a_note(a, two_caregivers["child_id"])
    settings = app.config["SETTINGS"]

    with b.session_transaction() as sess:
        sid = sess["sid"]
    with app.app_context():
        resolved = session_svc.resolve(sid, settings)
        rows = resolved.db.table("typing_notes").select("*").eq("id", nid).execute().data
    assert rows == []
