#!/usr/bin/env python3
"""Build the bundled calming-sound loops.

Two kinds of track, one output shape (mono 22.05 kHz 16-bit WAV, ~seamless):

  SYNTH       procedurally generated ambient beds — no copyright question.
  RECORDINGS  real CC0 field recordings from chosic.com, vendored under
              scripts/data/calming_sources/. Decoded with `afconvert` (macOS
              built-in — this half of the script is macOS-only), trimmed, and
              crossfade-looped so they tile without an audible seam.

Output: frontend/assets/calming/<slug>.wav  +  index.json  (order = ORDER).

Run by hand (`./.conda/bin/python scripts/build_calming.py`); the .wav files
are committed. CI only runs backend/tests/test_calming_assets.py against them.
If scripts/data/calming_sources/ is missing, the SYNTH tracks still rebuild and
the committed recording .wav are left in place.

Licence of the recordings: frontend/assets/calming/LICENSE.md
"""

from __future__ import annotations

import json
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "assets" / "calming"
SRC = ROOT / "scripts" / "data" / "calming_sources"
RATE = 22050
SECONDS = 16  # synth loop length; every LFO period must divide it

# slug -> Hebrew label
SYNTH = {
    "rain": "גשם",
    "waves": "גלים",
    "wind": "רוח",
    "hum": "זמזום רגוע",
    "tone432": "תדר מרגיע",
}

# slug -> (Hebrew label, source file under SRC, loop length in seconds)
RECORDINGS = {
    "fire": ("מדורה", "Fire-Crackle-and-Flames-1(chosic.com).mp3", 18),
    "forest": ("יער בגשם", "Rain-Sound-and-Rainforest(chosic.com).mp3", 40),
    "brook": ("פכפוך נחל", "stream-1(chosic.com).mp3", 12),
    "birds": (
        "ציפורים",
        "burghrecords__birds-singing-forest-scotland(chosic.com).mp3",
        30,
    ),
}

# Display / grid order across both kinds.
ORDER = ["rain", "waves", "wind", "hum", "fire", "forest", "brook", "birds", "tone432"]

LABELS = {**SYNTH, **{s: v[0] for s, v in RECORDINGS.items()}}

# RMS targets — noise beds sit a touch louder than the tonal tracks, which
# read as loud as noise at a lower RMS.
RMS_BED = 0.18
RMS_TONE = 0.12


def _lowpass(samples: list[float], alpha: float) -> list[float]:
    out, prev = [], 0.0
    for s in samples:
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def _normalize(
    samples: list[float], target_rms: float, peak_cap: float = 0.95
) -> list[float]:
    cur = _rms(samples)
    if cur == 0:
        return samples
    gain = target_rms / cur
    peak = max((abs(s) for s in samples), default=0.0) * gain
    if peak > peak_cap:
        gain *= peak_cap / peak
    return [s * gain for s in samples]


def _normalize_rec(samples: list[float], target_rms: float) -> list[float]:
    """Loudness-match a recording without letting rare transients hold it down.

    Raw field recordings have a huge crest factor (a stray click 20x above the
    bed), so plain peak-capped _normalize leaves the bed far too quiet. Bring
    the RMS up, soft-knee the peaks with tanh, then re-match the RMS.
    """
    cur = _rms(samples)
    if cur == 0:
        return samples
    g = target_rms / cur
    softened = [0.95 * math.tanh(s * g / 0.8) for s in samples]
    return _normalize(softened, target_rms)


# --------------------------------------------------------------- synth tracks


def _track(slug: str) -> list[float]:
    import random

    n = RATE * SECONDS
    rng = random.Random(slug)
    noise = [rng.uniform(-1, 1) for _ in range(n)]

    if slug == "rain":
        sig = _normalize(_lowpass(noise, 0.5), RMS_BED)
    elif slug == "waves":
        brown = _lowpass(_lowpass(noise, 0.02), 0.02)
        sig = [
            b * (0.5 + 0.5 * math.sin(2 * math.pi * (i / RATE) / 8))
            for i, b in enumerate(brown)
        ]
        sig = _normalize(sig, RMS_BED)
    elif slug == "wind":
        base = _lowpass(noise, 0.05)
        sig = [
            b * (0.35 + 0.65 * abs(math.sin(2 * math.pi * (i / RATE) / 8)))
            for i, b in enumerate(base)
        ]
        sig = _normalize(sig, RMS_BED)
    elif slug == "hum":  # soft drone with slow beat
        # 110 Hz + a slight detune for the beat, plus a 220 Hz octave so tablet
        # and phone speakers (which barely reproduce ~110 Hz) still carry it.
        # Matched to the beds' RMS, not RMS_TONE — it read much quieter in situ.
        sig = [
            0.16 * math.sin(2 * math.pi * 110 * (i / RATE))
            + 0.09 * math.sin(2 * math.pi * 110.5 * (i / RATE))
            + 0.09 * math.sin(2 * math.pi * 220 * (i / RATE))
            for i in range(n)
        ]
        sig = _normalize(sig, RMS_BED)
    else:  # tone432 — 432 Hz + sub, slow amplitude LFO so it breathes
        sig = [
            (
                0.6 * math.sin(2 * math.pi * 432 * (i / RATE))
                + 0.4 * math.sin(2 * math.pi * 216 * (i / RATE))
            )
            * (0.6 + 0.4 * math.sin(2 * math.pi * 0.125 * (i / RATE)))
            for i in range(n)
        ]
        sig = _normalize(sig, RMS_TONE)

    # gentle fade in/out so the loop point is soft
    fade = RATE // 2
    for i in range(fade):
        k = i / fade
        sig[i] *= k
        sig[-1 - i] *= k
    return sig


# ----------------------------------------------------------- recorded tracks


def _decode_mono(src: Path) -> list[float]:
    """MP3 -> mono 22.05 kHz float samples in [-1, 1], via macOS afconvert."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            [
                "afconvert",
                str(src),
                "-f",
                "WAVE",
                "-d",
                f"LEI16@{RATE}",
                "-c",
                "1",
                str(tmp_path),
            ],
            check=True,
            capture_output=True,
        )
        with wave.open(str(tmp_path)) as w:
            raw = w.readframes(w.getnframes())
        ints = struct.unpack(f"<{len(raw) // 2}h", raw)
        return [s / 32768.0 for s in ints]
    finally:
        tmp_path.unlink(missing_ok=True)


def _loop(samples: list[float], secs: float) -> list[float]:
    """Trim edges, take `secs`, crossfade the tail over the head → seamless."""
    head = int(1.0 * RATE)  # drop fade-ins / room noise at the start
    tail = int(0.5 * RATE)  # drop stops / fade-outs at the end
    body = (
        samples[head : len(samples) - tail]
        if len(samples) > head + tail
        else samples[:]
    )

    want = int(secs * RATE)
    xf = min(int(2.0 * RATE), want // 3)  # crossfade length
    if len(body) < want + xf:
        # source too short for the requested loop — shrink to fit
        want = max(len(body) - xf, xf * 2)

    seg = body[: want + xf]
    out = seg[:want]
    for i in range(xf):
        # equal-power crossfade: end of the segment fades into its start
        a = math.cos(0.5 * math.pi * i / xf)  # tail out
        b = math.sin(0.5 * math.pi * i / xf)  # head in
        out[i] = seg[want + i] * a + seg[i] * b
    return out


def _ingest(src_name: str, secs: float) -> list[float]:
    sig = _loop(_decode_mono(SRC / src_name), secs)
    return _normalize_rec(sig, RMS_BED)


# ------------------------------------------------------------------- output


def _write(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(
            b"".join(
                struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
                for s in samples
            )
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    for slug in SYNTH:
        _write(OUT / f"{slug}.wav", _track(slug))
    print(f"synthesised {len(SYNTH)} loops")

    if SRC.is_dir():
        for slug, (_label, src_name, secs) in RECORDINGS.items():
            _write(OUT / f"{slug}.wav", _ingest(src_name, secs))
        print(f"ingested {len(RECORDINGS)} recordings from {SRC}")
    else:
        print(f"! {SRC} missing — kept the committed recording .wav as-is")

    index = {slug: {"file": f"{slug}.wav", "label_he": LABELS[slug]} for slug in ORDER}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"wrote index.json ({len(ORDER)} tracks) → {OUT}")


if __name__ == "__main__":
    main()
