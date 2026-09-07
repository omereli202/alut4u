from __future__ import annotations

import uuid

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client, name="ילד") -> str:
    return client.post("/api/children", json={"name": name, "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _note_body(child_id, **over):
    body = {
        "child_id": child_id,
        "note_id": str(uuid.uuid4()),
        "title": "הטיול שלי",
        "blocks": [{"t": "h1", "s": "היום בגן"}, {"t": "p", "s": "שיחקתי בחצר."}],
        "rev": 1,
    }
    body.update(over)
    return body


def test_note_upsert_is_idempotent(client, caregiver_mode):
    cid = _child(client)
    body = _note_body(cid)

    assert client.post("/api/typing/notes", json=body).status_code == 200
    assert client.post("/api/typing/notes", json=body).status_code == 200

    notes = client.get(f"/api/typing/notes?child_id={cid}").get_json()["notes"]
    assert len(notes) == 1
    assert notes[0]["title"] == "הטיול שלי"


def test_upsert_rev_is_monotonic(client, caregiver_mode):
    cid = _child(client)
    nid = str(uuid.uuid4())

    client.post("/api/typing/notes", json=_note_body(cid, note_id=nid, rev=2, title="חדש"))
    # a replayed older save must not clobber; server still answers 200 so the
    # outbox drains the entry instead of jamming
    r = client.post("/api/typing/notes", json=_note_body(cid, note_id=nid, rev=1, title="ישן"))
    assert r.status_code == 200

    got = client.get(f"/api/typing/notes/{nid}").get_json()
    assert got["title"] == "חדש"
    assert got["rev"] == 2


def test_child_can_save_without_pin(client, caregiver_mode):
    cid = _child(client)
    client.delete("/api/auth/pin/elevation")  # drop to User Mode
    assert client.post("/api/typing/notes", json=_note_body(cid)).status_code == 200


def test_child_can_delete_own_note(client, caregiver_mode):
    cid = _child(client)
    body = _note_body(cid)
    client.post("/api/typing/notes", json=body)
    client.delete("/api/auth/pin/elevation")  # User Mode

    assert client.delete(f"/api/typing/notes/{body['note_id']}").status_code == 204
    assert client.get(f"/api/typing/notes/{body['note_id']}").status_code == 404


def test_settings_roundtrip_in_user_mode(client, caregiver_mode):
    cid = _child(client)
    client.delete("/api/auth/pin/elevation")

    got = client.get(f"/api/typing/settings?child_id={cid}").get_json()
    assert got == {"font_family": "rubik", "font_scale": "md"}

    put = client.put(
        "/api/typing/settings", json={"child_id": cid, "font_family": "heebo", "font_scale": "lg"}
    )
    assert put.status_code == 200
    assert client.get(f"/api/typing/settings?child_id={cid}").get_json() == {
        "font_family": "heebo",
        "font_scale": "lg",
    }


def test_blocks_validation_422(client, caregiver_mode):
    cid = _child(client)
    bad = [
        _note_body(cid, blocks=[{"t": "h9", "s": "x"}]),
        _note_body(cid, blocks="not-an-array"),
        _note_body(cid, blocks=[{"t": "p", "s": "x"}] * 201),
        _note_body(cid, blocks=[{"t": "p", "s": "x" * 2001}]),
        _note_body(cid, title="x" * 121),
        _note_body(cid, blocks=[{"t": "p", "s": "x" * 2000}] * 11),  # > 20_000 total
    ]
    for body in bad:
        assert client.post("/api/typing/notes", json=body).status_code == 422


def test_speak_caches_and_refuses_long_notes(client, caregiver_mode):
    cid = _child(client)
    body = _note_body(cid)
    client.post("/api/typing/notes", json=body)
    nid = body["note_id"]

    first = client.post(f"/api/typing/notes/{nid}/speak", json={"child_id": cid})
    assert first.status_code == 200
    url = first.get_json()["audio_url"]
    assert url and url.startswith("/api/media/")

    # unchanged text -> same asset, no re-synthesis
    again = client.post(f"/api/typing/notes/{nid}/speak", json={"child_id": cid})
    assert again.get_json()["audio_url"] == url

    long_body = _note_body(cid, blocks=[{"t": "p", "s": "א" * 1600}])
    client.post("/api/typing/notes", json=long_body)
    r = client.post(f"/api/typing/notes/{long_body['note_id']}/speak", json={"child_id": cid})
    assert r.status_code == 422


def test_note_from_another_child_is_404(client, caregiver_mode):
    a = _child(client, "ילד-א")
    b = _child(client, "ילד-ב")
    body = _note_body(a)
    client.post("/api/typing/notes", json=body)

    # same caregiver, but the note belongs to child A — refuse under child B
    r = client.post("/api/typing/notes", json=_note_body(b, note_id=body["note_id"]))
    assert r.status_code == 404


def test_list_excludes_blocks(client, caregiver_mode):
    cid = _child(client)
    client.post("/api/typing/notes", json=_note_body(cid))
    notes = client.get(f"/api/typing/notes?child_id={cid}").get_json()["notes"]
    assert "blocks" not in notes[0]
    assert notes[0]["preview"].startswith("היום בגן")
