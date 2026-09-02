// AAC board (User Mode): category tabs + a grid of cards. Tapping a card
// appends it to the sentence bar and speaks it.

import { api } from "../../api.js";
import { el, emptyState, icon, mount, navBar, visual } from "../../ui.js";
import { createSentenceBar } from "./sentence-bar.js";
import { prefetch } from "./speech.js";

// Matches --space-3 in tokens.css — the grid's actual gap. Read as a constant
// rather than measured, since the fit calculation below needs it before the
// grid has been laid out with a candidate column count.
const GRID_GAP = 12;

// The card's picture/photo sits in a colour-tinted medallion (docs/design/
// stitch-export §T1.1) rather than filling the card edge-to-edge. The tint is
// the card's own category colour when the caregiver set one, else a neutral
// secondary wash — same --cat custom property the category tab already uses,
// so a card always matches its tab.
function cardVisual(card, cats) {
  const cat = cats.find((c) => c.id === card.category_id);
  return el(
    "span",
    { class: "card-medallion", style: cat?.color ? `--cat:${cat.color}` : null },
    visual(card, "card-visual"),
  );
}

// Categories have no image of their own (schemas/aac.py: name + color only),
// so this always falls through to visual()'s two-letter text fallback — same
// helper the cards use. visual() reads `.label`/`.title`, not a category's
// `.name`, hence the wrapper.
function categoryVisual(cat) {
  return el(
    "span",
    { class: "card-medallion", style: cat.color ? `--cat:${cat.color}` : null },
    visual({ label: cat.name }, "card-visual"),
  );
}

// Pick the column/row split that lets all `n` cards fit in `box` (px) at
// once — no scrolling, ever, on a locked kiosk tablet a child can't scroll
// back from. Tries every column count, keeps whichever makes the resulting
// cell largest (closest to square), since rows always = ceil(n/cols) so
// everything fits regardless of which split wins.
function fitGrid(box, n) {
  if (!n) return { cols: 1, rows: 1, cell: box.height };
  let best = null;
  for (let cols = 1; cols <= n; cols++) {
    const rows = Math.ceil(n / cols);
    const cellW = (box.width - GRID_GAP * (cols - 1)) / cols;
    const cellH = (box.height - GRID_GAP * (rows - 1)) / rows;
    const cell = Math.min(cellW, cellH);
    if (!best || cell > best.cell) best = { cols, rows, cell };
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

  if (!preview) prefetch(board.cards);

  const cats = board.categories;
  let activeCat = cats[0]?.id ?? null;

  const sentence = createSentenceBar();
  let grid = null;
  let ro = null;

  function cardsForActive() {
    if (activeCat === "__all__" || !cats.length) return board.cards;
    return board.cards.filter((c) => c.category_id === activeCat);
  }

  // Below --touch-min (60px) even at the best-fitting split, a real screen is
  // too small/crowded for the card count — fall back to scrolling rather than
  // shipping sub-60px touch targets (docs/accessibility.md's floor).
  function fitToGrid() {
    if (!grid) return;
    const n = cardsForActive().length;
    const { width, height } = grid.getBoundingClientRect();
    if (!width || !height) return;
    const { cols, rows, cell } = fitGrid({ width, height }, n);
    grid.style.setProperty("--cols", cols);
    grid.style.setProperty("--rows", rows);
    grid.classList.toggle("aac-grid-scroll", cell < 60);
  }

  function paint() {
    grid = el(
      "div",
      { class: "aac-grid", role: "list" },
      ...cardsForActive().map((card) =>
        el(
          "button",
          {
            class: "aac-card",
            role: "listitem",
            // Preview is read-only — no sentence-bar writes, no TTS.
            onclick: preview ? undefined : () => sentence.add(card),
          },
          cardVisual(card, cats),
          el("span", { class: "card-label" }, card.label),
        ),
      ),
    );

    const tabs =
      cats.length > 1
        ? el(
            "div",
            { class: "cat-cards", role: "tablist" },
            ...cats.map((c) =>
              el(
                "button",
                {
                  class: c.id === activeCat ? "cat-card active" : "cat-card",
                  role: "tab",
                  "aria-selected": c.id === activeCat,
                  style: c.color ? `--cat:${c.color}` : null,
                  onclick: () => {
                    activeCat = c.id;
                    paint();
                  },
                },
                categoryVisual(c),
                el("span", {}, c.name),
              ),
            ),
          )
        : null;

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
      tabs,
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
