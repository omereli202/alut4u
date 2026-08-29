// AAC board (User Mode): category tabs + a grid of cards. Tapping a card
// appends it to the sentence bar and speaks it.

import { api } from "../../api.js";
import { el, mount } from "../../ui.js";
import { createSentenceBar } from "./sentence-bar.js";
import { prefetch } from "./speech.js";

const GRID_KEY = "alut4u.aac.grid"; // remembered columns (2–5)

function cardVisual(card) {
  if (card.symbol_id) {
    return el("img", {
      class: "card-visual",
      src: `/assets/symbols/${card.symbol_id}.svg`,
      alt: "",
    });
  }
  if (card.icon_asset_id) {
    return el("img", { class: "card-visual", src: `/api/media/${card.icon_asset_id}`, alt: "" });
  }
  return el("div", { class: "card-visual card-visual-text" }, card.label.slice(0, 2));
}

export async function renderAacBoard({ childId, childName, onExit }) {
  let board;
  try {
    board = await api.get(`/aac/board?child_id=${encodeURIComponent(childId)}`);
  } catch {
    return mount(
      el("p", { class: "err" }, "לא ניתן לטעון את הלוח."),
      el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
    );
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
          cardVisual(card),
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
        el("button", { class: "lock-btn", "aria-label": "יציאה", onclick: onExit }, "✕"),
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
