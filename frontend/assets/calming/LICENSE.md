# Calming-zone audio loops

Nine ambient loops for the calming module (`frontend/js/modules/calming/`), all
mono 22.05 kHz 16-bit WAV, built by `scripts/build_calming.py`.

## Synthesized — no third-party rights

`rain.wav` `waves.wav` `wind.wav` `hum.wav` `tone432.wav`

Procedurally generated (filtered noise / sine drones). Created for this project;
no copyright question. Regenerate: `./.conda/bin/python scripts/build_calming.py`.

## Field recordings — CC0 / public-domain-equivalent

`fire.wav` `forest.wav` `brook.wav` `birds.wav`

Downloaded from **chosic.com** (free sounds) by the project owner and declared
**CC0 / public-domain-equivalent** by the project owner on **2026-09-04**. The
originals are vendored under `scripts/data/calming_sources/`; the build script
decodes, trims and crossfade-loops them into the `.wav` above.

| slug | file in this folder | original download | embedded metadata (as found) |
|---|---|---|---|
| `fire` | `fire.wav` | `Fire-Crackle-and-Flames-1(chosic.com).mp3` | artist "Sound Effects", 2010 |
| `forest` | `forest.wav` | `Rain-Sound-and-Rainforest(chosic.com).mp3` | artist "Chosic" |
| `brook` | `brook.wav` | `stream-1(chosic.com).mp3` | (no tags) |
| `birds` | `birds.wav` | `burghrecords__birds-singing-forest-scotland(chosic.com).mp3` | **`TCOP BurghRecords`, album "Scottish Forest Sounds", 2019** |

> ⚠️ **`birds.wav` carries a `BurghRecords` copyright tag.** The CC0 status
> rests on the project owner's assertion, not on a licence file shipped with the
> download. **Verify the chosic.com licence for all four tracks — the birds one
> especially — before promoting to `main` / production.** See
> `docs/launch-checklist.md`.

If a track's licence turns out to require attribution or is not usable, replace
its source in `scripts/data/calming_sources/` (or fall back to a synthesized
track — see git history for `birds`/`bowls`/`drip`) and rerun the build.
