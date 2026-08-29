from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def test_create_list_update_deactivate(client, caregiver_mode):
    created = client.post(
        "/api/children", json={"name": "יונתן", "consent_basis": "parent"}
    ).get_json()
    cid = created["id"]

    listed = client.get("/api/children").get_json()["children"]
    assert [c["id"] for c in listed] == [cid]

    updated = client.patch(f"/api/children/{cid}", json={"name": "יוני"}).get_json()
    assert updated["name"] == "יוני"

    assert client.delete(f"/api/children/{cid}").status_code == 204
    assert client.get("/api/children").get_json()["children"] == []  # inactive hidden
    assert client.get(f"/api/children/{cid}").status_code == 200  # still fetchable by id


def test_writes_require_caregiver_mode(client, signed_up):
    # signed_up but not elevated
    r = client.post("/api/children", json={"name": "x", "consent_basis": "parent"})
    assert r.status_code == 403


def test_reads_allowed_in_user_mode(client, caregiver_mode):
    cid = client.post("/api/children", json={"name": "x", "consent_basis": "parent"}).get_json()[
        "id"
    ]
    client.delete("/api/auth/pin/elevation")  # drop to user mode
    assert client.get("/api/children").status_code == 200
    assert client.get(f"/api/children/{cid}/modules").status_code == 200


def test_professional_consent_requires_attestation(client, caregiver_mode):
    bad = client.post(
        "/api/children",
        json={"name": "x", "consent_basis": "professional_with_parental_consent"},
    )
    assert bad.status_code == 422

    ok = client.post(
        "/api/children",
        json={
            "name": "x",
            "consent_basis": "professional_with_parental_consent",
            "parental_consent_attested": True,
        },
    )
    assert ok.status_code == 201


def test_module_toggle_roundtrip(client, caregiver_mode):
    cid = client.post("/api/children", json={"name": "x", "consent_basis": "parent"}).get_json()[
        "id"
    ]

    mods = client.get(f"/api/children/{cid}/modules").get_json()
    assert mods["aac_enabled"] is True

    after = client.put(
        f"/api/children/{cid}/modules", json={"aac_enabled": False, "calming_enabled": False}
    ).get_json()
    assert after["aac_enabled"] is False
    assert after["calming_enabled"] is False
    assert after["schedule_enabled"] is True


def test_empty_module_patch_is_422(client, caregiver_mode):
    cid = client.post("/api/children", json={"name": "x", "consent_basis": "parent"}).get_json()[
        "id"
    ]
    assert client.put(f"/api/children/{cid}/modules", json={}).status_code == 422
