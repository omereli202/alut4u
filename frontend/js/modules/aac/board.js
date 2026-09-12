// AAC board (User Mode): a drill-down grid. Each level shows its
// sub-categories (as framed picture tiles) and its own word-cards together;
// tapping a category tile descends into it, a breadcrumb walks back up.
// Tapping a word card appends it to the sentence bar and speaks it.

import { api } from "../../api.js";
import { el, emptyState, icon, mount, navBar, visual } from "../../ui.js";
import { createSentenceBar } from "./sentence-bar.js";
import { prefetch, prefetchSymbols } from "./speech.js";

// Matches --space-3 in tokens.css — the grid's actual gap. Read as a constant
// rather than measured, since the fit calculation below needs it before the
// grid has been laid out with a candidate column count.
const GRID_GAP = 12;

// Cap on a single tile. Past this a card stops being easier to hit and just
// becomes a large tinted panel around a small centred symbol, with the word
// label looking lost inside it. 240px is 4x the 60px --touch-min floor —
// comfortable on a tablet, still bounded.
const MAX_CELL = 240;
// A tile never gets more than this much wider than tall (or taller than
// wide), so a 2-card landscape board doesn't produce two letterbox strips.
const MAX_ASPECT = 1.4;

// Maps a card's part_of_speech to its Fitzgerald-key colour token (see
// tokens.css). Falls back to the card's category colour, then to none (the
// CSS default border colour) — this is what lets root-level core words
// (which have no category at all) still get coloured.
const POS_COLOR_VAR = {
  pronoun: "--pos-pronoun",
  verb: "--pos-verb",
  adjective: "--pos-adjective",
  noun: "--pos-noun",
  social: "--pos-social",
  question: "--pos-question",
  negation: "--pos-negation",
  little: "--pos-little",
  adverb: "--pos-adverb",
};

function tileColor(card, cats) {
  const posVar = POS_COLOR_VAR[card.part_of_speech];
  if (posVar) return `var(${posVar})`;
  return cats.find((c) => c.id === card.category_id)?.color || null;
}

// A word card: the picture fills the card's image area edge-to-edge
// (docs/design.md §T1.1 — "a picture symbol filling the top two-thirds, a word
// label below"), with a border in the card's category colour. A text-only card
// (no symbol/photo) is just its word, large.
function wordTile(card, cats, onTap) {
  const hasPicture = card.symbol_id || card.icon_asset_id;
  const color = tileColor(card, cats);
  return el(
    "button",
    {
      class: hasPicture ? "aac-card" : "aac-card aac-card-text",
      role: "listitem",
      style: color ? `--cat:${color}` : null,
      onclick: onTap ? () => onTap(card) : undefined,
    },
    ...(hasPicture
      ? [
          el("span", { class: "card-image", style: color ? `--cat:${color}` : null }, visual(card, "card-visual")),
          el("span", { class: "card-label" }, card.label),
        ]
      : [el("span", { class: "card-label" }, card.label)]),
  );
}

// A sub-category tile: same picture + label shape as a word card, but a
// doubled frame in the category's own colour so it reads as a container to
// open, not a word to speak. Works in preview too — lets the caregiver walk
// the hierarchy.
function catTile(cat, onOpen) {
  const color = cat.color || null;
  const item = { symbol_id: cat.symbol_id, icon_asset_id: cat.icon_asset_id, name: cat.name };
  return el(
    "button",
    {
      class: "aac-card aac-cat-card",
      role: "listitem",
      style: color ? `--cat:${color}` : null,
      onclick: () => onOpen(cat.id),
    },
    el("span", { class: "card-image", style: color ? `--cat:${color}` : null }, visual(item, "card-visual")),
    el("span", { class: "card-label" }, cat.name),
  );
}

// Pick the column/row split that lets all `n` tiles fit in `box` (px) at
// once — no scrolling, ever, on a locked kiosk tablet a child can't scroll
// back from. Tries every column count, keeps whichever makes the resulting
// cell largest (closest to square), since rows always = ceil(n/cols) so
// everything fits regardless of which split wins.
function fitGrid(box, n) {
  if (!n) return { cols: 1, rows: 1, cell: box.height, cellW: box.height, cellH: box.height };
  let best = null;
  for (let cols = 1; cols <= n; cols++) {
    const rows = Math.ceil(n / cols);
    const cellW = (box.width - GRID_GAP * (cols - 1)) / cols;
    const cellH = (box.height - GRID_GAP * (rows - 1)) / rows;
    const cell = Math.min(cellW, cellH);
    if (!best || cell > best.cell) best = { cols, rows, cell, cellW, cellH };
  }
  return best;
}

// `host`: render into this element instead of the global #main (used by the
// caregiver-editor preview overlay so it can sit inside a modal rather than
// replacing the whole screen). `preview`: read-only — no TTS, no sentence-bar
// writes, and a plain "סגירה" control instead of the child-facing back+home.
export async function renderAacBoard({
  childId,
  childName,
  onExit,
  onHome,
  preview = false,
  host,
} = {}) {
  let board;
  try {
    board = await api.get(`/aac/board?child_id=${encodeURIComponent(childId)}`);
  } catch {
    const empty = emptyState({ title: "לא ניתן לטעון את הלוח.", onBack: onExit });
    return host ? host.replaceChildren(empty) : mount(empty);
  }

  if (!preview) {
    prefetch(board.cards);
    prefetchSymbols(board.cards);
  }

  const cats = board.categories.slice().sort((a, b) => a.sort_order - b.sort_order);
  const catById = new Map(cats.map((c) => [c.id, c]));
  // The current position in the hierarchy: category ids from root to here.
  // Empty = top level. A stale id (category deleted between loads) is dropped.
  let path = [];

  const sentence = createSentenceBar();
  let grid = null;
  let ro = null;

  function here() {
    return path.at(-1) ?? null;
  }

  function childCategories() {
    return cats.filter((c) => (c.parent_id ?? null) === here());
  }
  function directCards() {
    return board.cards
      .filter((c) => (c.category_id ?? null) === here())
      .sort((a, b) => a.grid_order - b.grid_order);
  }

  // Below --touch-min (60px) even at the best-fitting split, a real screen is
  // too small/crowded for the tile count — fall back to scrolling rather than
  // shipping sub-60px touch targets (docs/accessibility.md's floor).
  function fitToGrid() {
    if (!grid) return;
    const n = childCategories().length + directCards().length;
    const { width, height } = grid.getBoundingClientRect();
    if (!width || !height) return;
    const { cols, rows, cell, cellW, cellH } = fitGrid({ width, height }, n);
    // Clamp the winning split to a comfortable, roughly-square tile instead
    // of letting a sparse board (1-2 cards) stretch cells to fill the whole
    // screen — see MAX_CELL/MAX_ASPECT above.
    let w = Math.min(cellW, MAX_CELL);
    let h = Math.min(cellH, MAX_CELL);
    w = Math.min(w, h * MAX_ASPECT);
    h = Math.min(h, w * MAX_ASPECT);
    grid.style.setProperty("--cols", cols);
    grid.style.setProperty("--rows", rows);
    grid.style.setProperty("--cell-w", `${Math.floor(w)}px`);
    grid.style.setProperty("--cell-h", `${Math.floor(h)}px`);
    grid.classList.toggle("aac-grid-scroll", cell < 60);
  }

  function openCat(id) {
    path.push(id);
    paint();
  }
  function goTo(depth) {
    path = path.slice(0, depth);
    paint();
  }

  // Breadcrumb: only inside a category. A back button (pop one level) then the
  // trail — child name ‹ אוכל ‹ ארוחת בוקר — each crumb but the last a button
  // that jumps back to that level.
  function breadcrumb() {
    if (!path.length) return null;
    const steps = [
      el("button", { class: "crumb", onclick: () => goTo(0) }, childName || "הלוח"),
      ...path.map((id, i) => {
        const name = catById.get(id)?.name ?? "…";
        const last = i === path.length - 1;
        return last
          ? el("span", { class: "crumb crumb-current", "aria-current": "page" }, name)
          : el("button", { class: "crumb", onclick: () => goTo(i + 1) }, name);
      }),
    ];
    // Separator points into the trail (left, in RTL) — chevron_left is the
    // repo's pre-mirrored "next" glyph, so no bidi mirroring surprise the way a
    // literal ‹ has (see base.css). Interleaved, not a CSS ::after.
    const crumbs = steps.flatMap((step, i) =>
      i === 0
        ? [step]
        : [el("span", { class: "crumb-sep", "aria-hidden": "true" }, icon("chevron_left", { size: 20 })), step],
    );
    return el(
      "div",
      { class: "aac-breadcrumb" },
      el(
        "button",
        { class: "nav-btn crumb-back", "aria-label": "חזרה", onclick: () => goTo(path.length - 1) },
        icon("arrow_back", { flip: true }),
      ),
      el("nav", { class: "crumb-trail", "aria-label": "מיקום" }, ...crumbs),
    );
  }

  function paint() {
    // Drop any path segment whose category no longer exists.
    path = path.filter((id) => catById.has(id));

    const onTap = preview ? null : (card) => sentence.add(card);
    // Folder tiles before word cards — the topic folders are the board's
    // top-level navigation, so they anchor the start of the grid (top-right
    // in this RTL layout) with the word cards following after.
    grid = el(
      "div",
      { class: "aac-grid", role: "list" },
      ...childCategories().map((c) => catTile(c, openCat)),
      ...directCards().map((card) => wordTile(card, cats, onTap)),
    );

    const screen = el(
      "section",
      { class: preview ? "aac-board aac-board-preview" : "aac-board", "data-mode": "user" },
      preview
        ? el(
            "div",
            { class: "nav-bar" },
            el("button", { class: "nav-btn", onclick: onExit }, icon("close"), el("span", {}, "סגירה")),
            el("h1", { class: "nav-title" }, "תצוגה מקדימה"),
          )
        : navBar({ onBack: onExit, onHome: onHome ?? onExit, title: childName || "בוא נדבר" }),
      sentence.host,
      breadcrumb(),
      grid,
    );

    if (host) host.replaceChildren(screen);
    else mount(screen);

    ro?.disconnect();
    ro = new ResizeObserver(fitToGrid);
    ro.observe(grid);
    // The observer's own first callback fires after layout, but run once
    // synchronously too so the very first paint isn't a moment of overflow.
    requestAnimationFrame(fitToGrid);

    return screen;
  }

  return paint();
}
