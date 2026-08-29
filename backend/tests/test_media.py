from __future__ import annotations

import io
import struct
import zlib

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _png(size: int = 32) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = (b"\x00" + b"\x64\x64\x64" * size) * size
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _child(client) -> str:
    return client.post("/api/children", json={"name": "c", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def test_upload_icon_reencodes_and_is_fetchable(client, caregiver_mode):
    child_id = _child(client)
    up = client.post(
        "/api/media",
        data={"kind": "card_icon", "child_id": child_id, "file": (io.BytesIO(_png()), "x.png")},
        content_type="multipart/form-data",
    )
    assert up.status_code == 201
    asset = up.get_json()
    assert asset["url"] == f"/api/media/{asset['id']}"

    got = client.get(asset["url"])
    assert got.status_code == 200
    assert got.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    etag = got.headers["ETag"]
    assert client.get(asset["url"], headers={"If-None-Match": etag}).status_code == 304


def test_upload_rejects_non_image(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/media",
        data={
            "kind": "card_icon",
            "child_id": child_id,
            "file": (io.BytesIO(b"not an image"), "x.png"),
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 422


def test_audio_upload_needs_voice_consent(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/media",
        data={
            "kind": "card_audio",
            "child_id": child_id,
            "file": (io.BytesIO(b"ID3\x03\x00\x00\x00\x00\x00\x00"), "a.mp3"),
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 403
    assert r.get_json()["error"] == "voice_consent_required"

    assert client.post("/api/auth/voice-consent", json={"accept": True}).status_code == 204
    r2 = client.post(
        "/api/media",
        data={
            "kind": "card_audio",
            "child_id": child_id,
            "file": (io.BytesIO(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 200), "a.mp3"),
        },
        content_type="multipart/form-data",
    )
    assert r2.status_code == 201


def test_media_is_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)
    asset = client.post(
        "/api/media",
        data={"kind": "card_icon", "child_id": child_id, "file": (io.BytesIO(_png()), "x.png")},
        content_type="multipart/form-data",
    ).get_json()

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"m-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    assert other.get(asset["url"]).status_code == 404
