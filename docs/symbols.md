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
4. **Regenerate the search vectors:** `python scripts/build_symbol_vectors.py --apply`
   (see § Symbol vectors below). Skipping it leaves the new symbols
   findable by exact word only and reddens `test_symbol_consistency.py`.
5. Run `pytest backend/tests/test_symbol_consistency.py` and
   `pytest backend/tests/test_painting_pages.py`.
6. If the batch re-exports a symbol used as a **colouring page** (see `CURATED`
   in `frontend/js/modules/painting/pages.js`), expect the geometry-derived
   region keys to change — an old painting's saved `fills` then no longer match
   its stored `sig` and are dropped on load (the brush strokes still replay).
   That is the intended graceful degradation, not a bug; the `SYMBOLS_VERSION`
   bump in step 1 is what makes it visible instead of silent.

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

## Symbol vectors (fuzzy + semantic search)

`GET /api/symbols?q=` (every caregiver symbol picker) ranks in
`backend/app/services/symbol_search.py`: nine tiers, exact-label first, then
Hebrew-morphology-tolerant lexical tiers (final-letter fold, clitic prefixes
`ה/ו/ב/ל/מ/ש`, plural, ktiv male/haser), then a **semantic backfill** of
fastText cosine neighbours — only used to fill an under-full page, so it never
displaces an exact hit and `total` never inflates.

### Prerequisites (local only)

The model is **not** a backend dependency. Once:

```bash
pip install fasttext-wheel numpy
# cc.he.300.bin.gz (~4.5GB) from https://fasttext.cc/docs/en/crawl-vectors.html
gunzip ~/Downloads/cc.he.300.bin.gz
```

### Regenerating

```bash
python scripts/build_symbol_vectors.py                 # dry run — coverage + diagnostics
python scripts/build_symbol_vectors.py --probe "אוטו,גור,שמח"
python scripts/build_symbol_vectors.py --apply
```

`--apply` writes six files to `backend/app/data/symbol_vectors/`:

| file | what | rewritten |
|---|---|---|
| `meta.json` | ids, dim, `mean[300]` + `pc[300]` (the post-processing params), diagnostics | every run |
| `symbols.f16.npy` | one 300-d vector per approved symbol (unit, post-processed) | every run |
| `words.f16.npy` / `words.txt` | the 20k most-frequent Hebrew words (unit, **not** post-processed) — used to embed the query at request time | only when the key list changes |
| `words_extra.f16.npy` / `words_extra.txt` | symbol tokens missing from the 20k core | every run |

The pooling + `post()` (mean subtraction + top-principal-component removal,
"all-but-the-top") in the script **must stay byte-identical** to
`symbol_search.embed` — build and runtime share one arithmetic. Changing it
invalidates every stored vector.

### Tuning the threshold

`--apply` prints a **suggested `SEMANTIC_MIN_COS`** (the p99.5 of the
random-pair cosine distribution). Paste it into `symbol_search.py` by hand —
a rebuild silently changing user-visible ranking is the drift class these
tests exist to prevent. `test_symbol_consistency.py::test_label_roundtrip_accuracy`
catches a build/runtime arithmetic mismatch (every label should re-retrieve
its own symbol).

Quality is honest-but-modest: single-word synonyms on concrete nouns work
(`אוטו`→`מכונית`); co-hyponyms and antonyms sit as close as synonyms, so the
band is a *picker* aid only — never auto-select a semantic hit. Multi-word
queries degrade; the tier order just makes the band contribute nothing.
