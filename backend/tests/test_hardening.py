from __future__ import annotations

from app import create_app
from app.config import Settings
from tests.conftest import requires_supabase


def test_request_id_and_security_headers(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Request-Id")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_hsts_only_in_production():
    dev = create_app(Settings(app_env="test", serve_frontend=False))
    assert "Strict-Transport-Security" not in dev.test_client().get("/api/health").headers


_MSGS = [
    {"role": "user", "content": "a"},
    {"role": "assistant", "content": "?"},
    {"role": "user", "content": "b"},
    {"role": "assistant", "content": "?"},
    {"role": "user", "content": "c"},
    {"role": "assistant", "content": "?"},
    {"role": "user", "content": "d"},
    {"role": "assistant", "content": "?"},
    {"role": "user", "content": "e"},
]


@requires_supabase
def test_compose_rejects_over_llm_cap(client, caregiver_mode, app):
    app.config["SETTINGS"].quota_llm_tokens_per_month = 100  # < the compose budget
    child_id = client.post(
        "/api/children", json={"name": "x", "consent_basis": "parent"}
    ).get_json()["id"]
    r = client.post("/api/stories/compose", json={"child_id": child_id, "messages": _MSGS})
    assert r.status_code == 429
    assert r.get_json()["error"] == "quota_exceeded"


@requires_supabase
def test_illustrate_rejects_over_image_cap_but_keeps_the_text(client, caregiver_mode, app):
    app.config["SETTINGS"].quota_image_count_per_month = 1
    child_id = client.post(
        "/api/children", json={"name": "x", "consent_basis": "parent"}
    ).get_json()["id"]
    story = client.post(
        "/api/stories/compose", json={"child_id": child_id, "messages": _MSGS}
    ).get_json()

    first = client.post(f"/api/stories/{story['id']}/illustrate", json={"page_index": 0})
    assert first.status_code == 200
    over = client.post(f"/api/stories/{story['id']}/illustrate", json={"page_index": 1})
    assert over.status_code == 429
    assert over.get_json()["error"] == "quota_exceeded"

    # the story is still fully readable — text + audio survive
    got = client.get(f"/api/stories/{story['id']}").get_json()
    assert all(p["text"] for p in got["pages"])


@requires_supabase
def test_tts_quota_soft_skips_without_500(client, caregiver_mode, app):
    import uuid

    app.config["SETTINGS"].quota_tts_chars_per_month = 3  # tiny cap
    child_id = client.post(
        "/api/children", json={"name": "x", "consent_basis": "parent"}
    ).get_json()["id"]
    # a label that has never been synthesised → not a cache hit → quota applies
    card = client.post(
        "/api/aac/cards", json={"child_id": child_id, "label": f"מ {uuid.uuid4().hex[:8]}"}
    )
    assert card.status_code == 201
    assert card.get_json()["tts_asset_id"] is None  # over cap → silently no audio


@requires_supabase
def test_retention_dry_run_leaves_fresh_accounts_alone(client, signed_up):
    from app.services.retention import run

    with client.application.app_context():
        sweep = run(dry_run=True)
    assert sweep.dry_run is True
    assert signed_up["caregiver_id"] not in sweep.warned
    assert signed_up["caregiver_id"] not in sweep.purged
