// AAC board (User Mode): category tabs + a grid of cards. Tapping a card
// appends it to the sentence bar and speaks it.

import { api } from "../../api.js";
import { el, emptyState, icon, mount, visual } from "../../ui.js";
import { createSentenceBar } from "./sentence-bar.js";
import { prefetch } from "./speech.js";

const GRID_KEY = "alut4u.aac.grid"; // remembered columns (2–5)

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

export async function renderAacBoard({ childId, childName, onExit }) {
  let board;
  try {
    board = await api.get(`/aac/board?child_id=${encodeURIComponent(childId)}`);
  } catch {
    return mount(emptyState({ title: "לא ניתן לטעון את הלוח.", onBack: onExit }));
  }

  prefetch(board.cards);

  const cats = board.categories;
  let activeCat = cats[0]?.id ?? null;
  let columns = clampCols(Number(safeGet(GRID_KEY)) || 3);

  const sentence = createSentenceBar();

  function cardsForActive() {
    if (activeCat === "__all__" || !cats.length) return board.cards;
    return board.cards.filter((c) => c.category_id === activeCat);
  }

  function view() {
    const grid = el(
      "div",
      { class: "aac-grid", style: `--cols:${columns}`, role: "list" },
      ...cardsForActive().map((card) =>
        el(
          "button",
          {
            class: "aac-card",
            role: "listitem",
            onclick: () => sentence.add(card),
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
            { class: "cat-tabs", role: "tablist" },
            ...cats.map((c) =>
              el(
                "button",
                {
                  class: c.id === activeCat ? "cat-tab active" : "cat-tab",
                  role: "tab",
                  "aria-selected": c.id === activeCat,
                  style: c.color ? `--cat:${c.color}` : null,
                  onclick: () => {
                    activeCat = c.id;
                    mount(view());
                  },
                },
                c.name,
              ),
            ),
          )
        : null;

    return el(
      "section",
      { class: "aac-board", "data-mode": "user" },
      el(
        "div",
        { class: "aac-topbar" },
        el("button", { class: "lock-btn", "aria-label": "יציאה", onclick: onExit }, icon("close")),
        el("h1", { class: "aac-title" }, childName || "לוח תקשורת"),
        gridControl(),
      ),
      sentence.host,
      tabs,
      grid,
    );
  }

  function gridControl() {
    return el(
      "div",
      { class: "grid-control", "aria-label": "גודל הרשת" },
      el(
        "button",
        {
          class: "sb-btn",
          "aria-label": "פחות עמודות",
          onclick: () => setCols(columns - 1),
        },
        "−",
      ),
      el("span", { class: "grid-count" }, `${columns}`),
      el(
        "button",
        { class: "sb-btn", "aria-label": "יותר עמודות", onclick: () => setCols(columns + 1) },
        "+",
      ),
    );
  }

  function setCols(n) {
    columns = clampCols(n);
    safeSet(GRID_KEY, columns);
    mount(view());
  }

  mount(view());
}

function clampCols(n) {
  return Math.max(2, Math.min(5, n || 3));
}
function safeGet(k) {
  try {
    return localStorage.getItem(k);
  } catch {
    return null;
  }
}
function safeSet(k, v) {
  try {
    localStorage.setItem(k, String(v));
  } catch {
    /* ignore */
  }
}
