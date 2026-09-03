// Searchable symbol grid, used inside the card editor.

import { api } from "../../api.js";
import { el, symbolUrl } from "../../ui.js";

export function createSymbolPicker(onPick) {
  const results = el("div", { class: "symbol-results" });
  const count = el("p", { class: "symbol-count muted" });
  let timer = null;

  async function run(q) {
    const { symbols, total } = await api
      .get(`/symbols?q=${encodeURIComponent(q)}`)
      .catch(() => ({ symbols: [], total: 0 }));
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
          el("img", { src: symbolUrl(s.file_path), alt: s.label_he }),
        ),
      ),
    );
    if (!symbols.length) {
      count.textContent = q ? "לא נמצאו סמלים" : "";
    } else if (total > symbols.length) {
      count.textContent = `מציג ${symbols.length} מתוך ${total} — נסו חיפוש מדויק יותר`;
    } else {
      count.textContent = `${total} סמלים`;
    }
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
  return el("div", { class: "symbol-picker" }, search, count, results);
}
