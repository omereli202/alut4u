# Symbol library — Mulberry Symbols pipeline

The bundled AAC pictogram set is [Mulberry Symbols](https://mulberrysymbols.org/)
(CC BY-SA 4.0, © Steve Lee), swapped in for the original placeholder emoji
SVGs. This is a large, multi-session job — ~3,436 source symbols, only 36 of
which had a Hebrew label to begin with — so it's staged through a manifest
and a review pass rather than done in one shot.

## The three artifacts

1. **`scripts/data/mulberry_manifest.json`** (committed) — the single source
   of truth. Keyed by Mulberry's stable `symbol-id`. Each entry: which source
   file it maps to (`src`, null if kept as this project's own placeholder),
   the app's `id` (slug — **locked forever** for the original 36, see below),
   `label_he`/`keywords_he`, and a review `status`
   (`pending`/`approved`/`edited`/`rejected`).
2. **A published review Artifact** — a page where a human approves, edits,
   or rejects each candidate label before it ships. Built by
   `scripts/build_review_artifact.py`, which reads the manifest and writes a
   self-contained HTML file to publish. The page self-publishes its own
   edits (`artifact.publish()`) — read the current state back with the
   Artifact tool's `action: "read"`, then merge it into the manifest with
   `mulberry_manifest.merge_review()`.
3. **`frontend/assets/symbols/<id>.svg` + a migration** — the actual shipped
   result, written by `scripts/build_symbols.py` from whatever the manifest
   currently has at `approved`/`edited`.

## Why the original 36 ids can never change

`symbol_id` is a real FK (`on delete set null`) from five tables
(`aac_cards`, `schedule_items`, `calendar_events`, `behavior_rules`,
`rewards`) — renaming one silently blanks a live child's card. It's also
referenced with **no** FK protection as bare strings inside
`0005_reference_data.sql`'s `board_templates.cards` jsonb and
`frontend/js/modules/calming/memory.js`'s `POOL` array.
`backend/tests/test_symbol_consistency.py` asserts all of this stays
resolvable on every run.

Nine of the 36 have no direct Mulberry equivalent (Mulberry is noun-heavy;
core AAC words like "yes"/"no"/"stop" are thin). Where a Mulberry file is
close enough it's used as an approximate substitute (flagged
`scrutiny: "substitute"` in the manifest for extra review); where nothing
was good enough the id just keeps its original placeholder SVG untouched
(`src: null`) — currently `stop`, `thanks`, `dont-want`.

## Running an ingest batch

```bash
# 1. Bootstrap (one-time; already done) — reads the source archive + the
#    original 36 ids' hand-authored labels, classifies every Mulberry
#    concept as locked / rejected (explicit content, Country Flags/Maps) /
#    pending.
python3 -c "import sys; sys.path.insert(0,'scripts'); import mulberry_manifest as mm; mm.save_manifest(mm.bootstrap())"

# 2. Author labels for a batch of pending rows (by hand — this is Hebrew
#    translation work, not automatable), then build a review page for them:
python scripts/build_review_artifact.py --batch pending --status pending --limit 300 --out /tmp/review.html
# Publish /tmp/review.html via the Artifact tool (capabilities: {"artifact": {}}).

# 3. Once reviewed, read the artifact back and merge decisions:
#    (see mulberry_manifest.merge_review — refuses to downgrade an
#    already-approved row without force=True)

# 4. Ingest whatever is now approved/edited:
python scripts/build_symbols.py               # dry run report
python scripts/build_symbols.py --apply        # writes SVGs + a new migration
```

`build_symbols.py --apply` is safe to re-run — already-shipped ids are
no-ops (same source, same output). Each run's migration is additive
(`0012_..._batch2.sql`, `0013_..._batch3.sql`, …); never edit an applied one.

## After every `--apply`

1. Bump `SYMBOLS_VERSION` in `frontend/js/ui.js`. **This is not optional.**
   Railway's CDN edge-caches `/assets/*` per node on top of Caddy's 7-day
   `Cache-Control`, independently of the service worker — replacing a
   symbol's file *contents* while its *path* stays the same is exactly the
   bug that bit the icon sprite (`ba37785`) and unversioned CSS/JS
   (`e62c623`). A new `?v=` is a new URL at every cache layer.
2. Bump `SHELL_CACHE` in `frontend/sw.js` (since `ui.js` changed).
3. `supabase db push` (or let CI apply the new migration).
4. Run `pytest backend/tests/test_symbol_consistency.py`.

## Normalization notes

The source archive mixes two authoring generations — do not run a generic
SVG minifier over it:

- ~90% of files have `width`/`height`/`overflow` attributes and a redundant
  full-canvas bounding-box `<path fill="none" d="M0 0h…H0z"/>` — all
  stripped by `normalize_svg()`.
- ~10% instead have `id="Layer_1"` and an embedded `<style>` block using
  generic `.st0`…`.st13` class names — the `<style>` block and every
  `class=` reference to it are preserved byte-for-byte; stripping it blanks
  the symbol.
- `viewBox` is **not uniform** (10+ distinct values) and is always preserved
  as authored — the `<img>` render sites size via CSS, so the exact
  intrinsic ratio doesn't matter, but rewriting it to one canonical value
  would distort hundreds of files.
- 6 explicit-content symbols (`rated=1` in the source CSV) and the Country
  Flags/Country Maps categories (442 rows, ~9.2MB, zero relevance to a
  Hebrew children's AAC board) are pre-rejected in the manifest with a note,
  so a future bootstrap re-run can't silently reintroduce them.

## Attribution

`frontend/assets/symbols/LICENSE` (regenerated by `build_symbols.py`) and a
credits line in the caregiver dashboard's account section — CC BY-SA 4.0
requires this, it's not optional polish.
