"""Validate and normalise uploaded media before it is stored.

Images are re-encoded (drops EXIF/metadata, confirms it's a real image, caps
dimensions). Audio is validated by magic bytes + size only.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_AUDIO_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIM = 1024

IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
AUDIO_MIMES = {"audio/mpeg", "audio/wav", "audio/webm", "audio/ogg", "audio/mp4"}

_AUDIO_MAGIC = {
    b"ID3": "audio/mpeg",
    b"\xff\xfb": "audio/mpeg",
    b"\xff\xf3": "audio/mpeg",
    b"\xff\xf2": "audio/mpeg",
    b"RIFF": "audio/wav",
    b"OggS": "audio/ogg",
    b"\x1aE\xdf\xa3": "audio/webm",
}


@dataclass(frozen=True, slots=True)
class ProcessedMedia:
    data: bytes
    mime: str
    ext: str


class MediaError(ValueError):
    pass


def process_image(raw: bytes) -> ProcessedMedia:
    if len(raw) > MAX_IMAGE_BYTES:
        raise MediaError("image too large")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:  # Pillow raises many types
        raise MediaError("not a valid image") from e

    img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
    img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))

    out = io.BytesIO()
    if img.mode == "RGBA":
        img.save(out, format="PNG", optimize=True)
        return ProcessedMedia(out.getvalue(), "image/png", "png")
    img.save(out, format="JPEG", quality=85, optimize=True)
    return ProcessedMedia(out.getvalue(), "image/jpeg", "jpg")


def process_audio(raw: bytes, declared_mime: str) -> ProcessedMedia:
    if len(raw) > MAX_AUDIO_BYTES:
        raise MediaError("audio too large")
    if declared_mime not in AUDIO_MIMES:
        raise MediaError(f"unsupported audio type {declared_mime}")

    sniffed = next((m for magic, m in _AUDIO_MAGIC.items() if raw.startswith(magic)), None)
    # webm/mp4 magic is fiddly; trust the declared type when we can't sniff.
    mime = sniffed or declared_mime
    ext = {
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/ogg": "ogg",
        "audio/webm": "webm",
        "audio/mp4": "m4a",
    }[mime if mime in AUDIO_MIMES else declared_mime]
    return ProcessedMedia(raw, mime, ext)
