"""בוא נצייר — painting module API.

Rev-gating, colour/shape validation, the caps, and the caregiver page list.
"""

from __future__ import annotations

import uuid

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _body(cid, **over):
    b = {
        "child_id": cid,
        "painting_id": str(uuid.uuid4()),
        "title": "",
        "page": {"kind": "blank"},
        "strokes": [{"c": "#123abc", "w": 0.02, "e": 0, "p": [0.1, 0.1, 0.2, 0.2]}],
        "fills": [],
        "rev": 1,
    }
    b.update(over)
    return b


def test_roundtrip_blank_and_symbol(client, caregiver_mode):
    cid = _child(client)

    pid = str(uuid.uuid4())
    r = client.post(
        "/api/painting/paintings",
        json=_body(
            cid,
            painting_id=pid,
            title="הבית שלי",
            page={"kind": "symbol", "symbol_id": "cat", "sig": "abc123", "sv": "20260914e"},
            fills=[{"r": "r7f2a91", "c": "#4a90e2"}],
        ),
    )
    assert r.status_code == 200, r.get_json()

    full = client.get(f"/api/painting/paintings/{pid}").get_json()
    assert full["title"] == "הבית שלי"
    assert full["page"]["symbol_id"] == "cat"
    assert full["fills"] == [{"r": "r7f2a91", "c": "#4a90e2"}]

    lst = client.get(f"/api/painting/paintings?child_id={cid}").get_json()["paintings"]
    assert len(lst) == 1
    assert "strokes" not in lst[0]  # summary only


def test_rev_gating_ignores_stale_replay(client, caregiver_mode):
    cid = _child(client)
    pid = str(uuid.uuid4())
    client.post("/api/painting/paintings", json=_body(cid, painting_id=pid, rev=3, title="חדש"))
    # a replayed older save
    client.post("/api/painting/paintings", json=_body(cid, painting_id=pid, rev=1, title="ישן"))
    assert client.get(f"/api/painting/paintings/{pid}").get_json()["title"] == "חדש"


def test_blank_page_drops_symbol_id(client, caregiver_mode):
    cid = _child(client)
    pid = str(uuid.uuid4())
    client.post(
        "/api/painting/paintings",
        json=_body(cid, painting_id=pid, page={"kind": "blank", "symbol_id": "cat"}),
    )
    assert client.get(f"/api/painting/paintings/{pid}").get_json()["page"].get("symbol_id") is None


def test_delete(client, caregiver_mode):
    cid = _child(client)
    pid = str(uuid.uuid4())
    client.post("/api/painting/paintings", json=_body(cid, painting_id=pid))
    assert client.delete(f"/api/painting/paintings/{pid}").status_code == 204
    assert client.get(f"/api/painting/paintings/{pid}").status_code == 404


def test_caregiver_pages_roundtrip(client, caregiver_mode):
    cid = _child(client)
    r = client.put("/api/painting/pages", json={"child_id": cid, "symbol_ids": ["cat", "dog"]})
    assert r.status_code == 200
    assert r.get_json()["symbol_ids"] == ["cat", "dog"]
    assert client.get(f"/api/painting/pages?child_id={cid}").get_json()["symbol_ids"] == [
        "cat",
        "dog",
    ]
    # replace
    client.put("/api/painting/pages", json={"child_id": cid, "symbol_ids": ["tree"]})
    assert client.get(f"/api/painting/pages?child_id={cid}").get_json()["symbol_ids"] == ["tree"]


def test_pages_edit_needs_caregiver_mode(client, signed_up):
    # signed_up but not elevated — the decorator refuses before the handler runs
    assert (
        client.put(
            "/api/painting/pages",
            json={"child_id": str(uuid.uuid4()), "symbol_ids": ["cat"]},
        ).status_code
        == 403
    )
