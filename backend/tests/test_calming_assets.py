"""Consistency for the bundled calming-sound loops.

Pure filesystem + text parsing — no Supabase, runs in every CI job. Same
failure mode as test_symbol_consistency.py: derived representations of one
source of truth drifting apart. Here that's the generator's ORDER / SYNTH /
RECORDINGS, index.json, the on-disk .wav files, and the frontend's own TRACKS
list in sounds.js.

The RMS check is the regression test for the "waves is inaudible" bug — that
file's DSP left it ~30x quieter than rain, and player-side volume can't undo
it. If a future generator change reintroduces a near-silent track, this fails.
"""

from __future__ import annotations

import ast
import json
import math
import re
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CALMING_DIR = ROOT / "frontend" / "assets" / "calming"
INDEX_JSON = CALMING_DIR / "index.json"
LICENSE_MD = CALMING_DIR / "LICENSE.md"
BUILD_SCRIPT = ROOT / "scripts" / "build_calming.py"
SOUNDS_JS = ROOT / "frontend" / "js" / "modules" / "calming" / "sounds.js"

sys.path.insert(0, str(ROOT / "scripts"))
import build_calming as bc  # noqa: E402


def _index() -> dict:
    return json.loads(INDEX_JSON.read_text(encoding="utf-8"))


def _sounds_js_tracks() -> list[tuple[str, str]]:
    """[(slug, Hebrew label), ...] in order, parsed from sounds.js's TRACKS."""
    src = SOUNDS_JS.read_text(encoding="utf-8")
    block = re.search(r"const TRACKS = \[(.*?)\];", src, re.S).group(1)
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(r'slug:\s*"([^"]+)",\s*label:\s*"([^"]+)"', block)
    ]


def _wav_stats(path: Path) -> tuple[float, float]:
    """(duration_seconds, rms_normalised_to_full_scale)."""
    with wave.open(str(path)) as w:
        n = w.getnframes()
        rate = w.getframerate()
        raw = w.readframes(n)
    samples = struct.unpack(f"<{n}h", raw)
    rms = math.sqrt(sum(s * s for s in samples) / n) / 32767
    return n / rate, rms


def test_generator_order_covers_both_kinds():
    assert set(bc.ORDER) == set(bc.SYNTH) | set(bc.RECORDINGS)
    assert not (set(bc.SYNTH) & set(bc.RECORDINGS)), "a slug is both synth and recording"


def test_index_json_matches_generator():
    index = _index()
    assert list(index) == bc.ORDER, "index.json order must match build_calming.ORDER"
    for slug in bc.ORDER:
        assert index[slug]["label_he"] == bc.LABELS[slug]
        assert index[slug]["file"] == f"{slug}.wav"


def test_index_json_matches_on_disk_wavs():
    index = _index()
    on_disk = {p.stem for p in CALMING_DIR.glob("*.wav")}
    assert set(index) == on_disk
    for entry in index.values():
        assert (CALMING_DIR / entry["file"]).exists()


def test_sounds_js_tracks_match_generator():
    js_tracks = _sounds_js_tracks()
    assert [s for s, _ in js_tracks] == bc.ORDER, "sounds.js TRACKS order vs build_calming.ORDER"
    for slug, label in js_tracks:
        assert label == bc.LABELS[slug], f"{slug}: label differs from build_calming.LABELS"


def test_synth_loops_are_the_right_length_and_audible():
    for slug in bc.SYNTH:
        dur, rms = _wav_stats(CALMING_DIR / f"{slug}.wav")
        assert abs(dur - bc.SECONDS) < 0.1, f"{slug}: {dur:.1f}s, expected {bc.SECONDS}s"
        # Loudness floor — catches a track that regressed to near-silence (the
        # waves bug was ~0.005).
        assert rms > 0.05, f"{slug}: RMS {rms:.4f} is too quiet"


def test_recording_loops_are_looped_and_loudness_matched():
    for slug, (_label, _src, secs) in bc.RECORDINGS.items():
        dur, rms = _wav_stats(CALMING_DIR / f"{slug}.wav")
        # _loop() shrinks below `secs` when the source is short, never grows it.
        assert 4.0 < dur <= secs + 0.3, f"{slug}: {dur:.1f}s outside (4, {secs}]"
        # _normalize_rec targets bc.RMS_BED — all four should land right on it.
        assert abs(rms - bc.RMS_BED) < 0.03, f"{slug}: RMS {rms:.3f} not matched to {bc.RMS_BED}"


def test_recording_sources_are_vendored():
    for _label, src, _secs in bc.RECORDINGS.values():
        assert (bc.SRC / src).is_file(), f"missing vendored source: {src}"


def test_license_names_every_recording():
    text = LICENSE_MD.read_text(encoding="utf-8")
    for slug in bc.RECORDINGS:
        assert f"`{slug}.wav`" in text, f"LICENSE.md does not mention {slug}.wav"


def test_sounds_js_has_dated_asset_version():
    src = SOUNDS_JS.read_text(encoding="utf-8")
    assert re.search(r'const ASSET_V = "\d{8}"', src), "sounds.js is missing a dated ASSET_V"


def test_generator_has_no_syntax_errors():
    ast.parse(BUILD_SCRIPT.read_text(encoding="utf-8"))
