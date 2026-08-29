#!/usr/bin/env python3
"""Generate the bundled calming-sound loops.

PLACEHOLDER: short procedurally-generated ambient loops (no copyright question,
tiny files). Replace with licensed recordings later — same filenames.

Output: frontend/assets/calming/<slug>.wav  +  index.json
"""

from __future__ import annotations

import json
import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "assets" / "calming"
RATE = 22050
SECONDS = 16  # loops seamlessly-ish

TRACKS = {
    "rain": "גשם",
    "waves": "גלים",
    "wind": "רוח",
    "hum": "זמזום רגוע",
}


def _lowpass(samples: list[float], alpha: float) -> list[float]:
    out, prev = [], 0.0
    for s in samples:
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


def _track(slug: str) -> list[float]:
    n = RATE * SECONDS
    rng = random.Random(slug)
    noise = [rng.uniform(-1, 1) for _ in range(n)]

    if slug == "rain":
        sig = _lowpass(noise, 0.5)
        sig = [s * 0.35 for s in sig]
    elif slug == "waves":
        brown = _lowpass(_lowpass(noise, 0.02), 0.02)
        sig = [
            b * (0.25 + 0.25 * math.sin(2 * math.pi * (i / RATE) / 8))
            for i, b in enumerate(brown)
        ]
    elif slug == "wind":
        base = _lowpass(noise, 0.05)
        sig = [
            b * (0.2 + 0.3 * abs(math.sin(2 * math.pi * (i / RATE) / 11)))
            for i, b in enumerate(base)
        ]
    else:  # hum — soft drone with slow beat
        sig = [
            0.18 * math.sin(2 * math.pi * 110 * (i / RATE))
            + 0.10 * math.sin(2 * math.pi * 110.5 * (i / RATE))
            for i in range(n)
        ]

    # gentle fade in/out so the loop point is soft
    fade = RATE // 2
    for i in range(fade):
        k = i / fade
        sig[i] *= k
        sig[-1 - i] *= k
    return sig


def _write(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(
            b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for slug, label in TRACKS.items():
        _write(OUT / f"{slug}.wav", _track(slug))
        index[slug] = {"file": f"{slug}.wav", "label_he": label}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"wrote {len(TRACKS)} calming loops → {OUT}")


if __name__ == "__main__":
    main()
