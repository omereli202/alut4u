// The sentence builder strip. Holds an ordered list of cards; renders chips and
// the speak / clear / backspace controls.

import { el, icon } from "../../ui.js";
import { speak, speakSequence } from "./speech.js";

export function createSentenceBar() {
  let cards = [];
  const host = el("div", { class: "sentence-bar", "aria-live": "polite" });

  function render() {
    host.replaceChildren(
      el(
        "div",
        { class: "sentence-chips" },
        ...cards.map((c, i) =>
          el(
            "button",
            {
              class: "chip sentence-chip",
              "aria-label": `הסר ${c.label}`,
              onclick: () => {
                cards.splice(i, 1);
                render();
              },
            },
            c.label,
          ),
        ),
      ),
      el(
        "div",
        { class: "sentence-actions" },
        el(
          "button",
          {
            class: "sb-btn speak",
            disabled: cards.length === 0,
            onclick: () => speakSequence(cards),
          },
          icon("play_arrow"),
          " הקראה",
        ),
        el(
          "button",
          {
            class: "sb-btn",
            disabled: cards.length === 0,
            "aria-label": "מחק אחרון",
            onclick: () => {
              cards.pop();
              render();
            },
          },
          icon("backspace", { flip: true }),
        ),
        el(
          "button",
          {
            class: "sb-btn",
            disabled: cards.length === 0,
            onclick: () => {
              cards = [];
              render();
            },
          },
          "נקה",
        ),
      ),
    );
  }

  render();

  return {
    host,
    add(card) {
      cards.push(card);
      render();
      speak(card);
    },
  };
}
