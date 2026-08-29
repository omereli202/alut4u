// A calm memory / matching game built from the bundled symbol set. No timer,
// no score pressure — just turn cards until all pairs are found.

import { el } from "../../ui.js";

const POOL = [
  "happy", "ball", "book", "music", "home", "sleep",
  "eat", "drink", "love", "play", "hello", "hot",
];

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function renderMemory(host) {
  let pairs = 6;

  function newGame() {
    const chosen = shuffle([...POOL]).slice(0, pairs);
    const deck = shuffle(
      chosen.flatMap((s, i) => [
        { id: `${i}a`, sym: s },
        { id: `${i}b`, sym: s },
      ]),
    );
    let flipped = [];
    let matched = new Set();
    let busy = false;

    function render() {
      host.replaceChildren(
        el(
          "div",
          { class: "memory-game" },
          el(
            "div",
            { class: "memory-head" },
            el("span", { class: "muted" }, `${matched.size / 2} / ${pairs}`),
            el("button", { class: "btn-link", onclick: newGame }, "משחק חדש"),
            el(
              "button",
              {
                class: "btn-link",
                onclick: () => {
                  pairs = pairs === 6 ? 8 : 6;
                  newGame();
                },
              },
              `זוגות: ${pairs}`,
            ),
          ),
          matched.size === deck.length
            ? el("p", { class: "memory-win" }, "🎉 מצאת הכל!")
            : el(
                "div",
                { class: "memory-grid", style: `--cols:${pairs === 6 ? 4 : 4}` },
                ...deck.map((card) => {
                  const shown = flipped.includes(card.id) || matched.has(card.sym);
                  return el(
                    "button",
                    {
                      class: shown ? "memory-card shown" : "memory-card",
                      disabled: shown || busy,
                      "aria-label": shown ? card.sym : "קלף",
                      onclick: () => flip(card),
                    },
                    shown
                      ? el("img", { src: `/assets/symbols/${card.sym}.svg`, alt: "" })
                      : el("span", { class: "memory-back" }, "?"),
                  );
                }),
              ),
        ),
      );
    }

    function flip(card) {
      if (busy || flipped.includes(card.id) || matched.has(card.sym)) return;
      flipped.push(card.id);
      render();
      if (flipped.length === 2) {
        busy = true;
        const [a, b] = flipped.map((id) => deck.find((c) => c.id === id));
        setTimeout(() => {
          if (a.sym === b.sym) matched.add(a.sym);
          flipped = [];
          busy = false;
          render();
        }, a.sym === b.sym ? 350 : 900);
      }
    }

    render();
  }

  newGame();
}
