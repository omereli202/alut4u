// Searchable symbol grid, used inside the card editor.

import { api } from "../../api.js";
import { el } from "../../ui.js";

export function createSymbolPicker(onPick) {
  const results = el("div", { class: "symbol-results" });
  let timer = null;

  async function run(q) {
    const { symbols } = await api.get(`/symbols?q=${encodeURIComponent(q)}`).catch(() => ({
      symbols: [],
    }));
    results.replaceChildren(
      ...symbols.map((s) =>
        el(
          "button",
          {
            type: "button",
            class: "symbol-option",
            title: s.label_he,
            onclick: () => onPick(s),
          },
          el("img", { src: `/assets/symbols/${s.file_path}`, alt: s.label_he }),
        ),
      ),
    );
  }

  const search = el("input", {
    type: "search",
    class: "symbol-search",
    placeholder: "חיפוש סמל…",
    oninput: (e) => {
      clearTimeout(timer);
      const q = e.target.value;
      timer = setTimeout(() => run(q), 200);
    },
  });

  run("");
  return el("div", { class: "symbol-picker" }, search, results);
}
