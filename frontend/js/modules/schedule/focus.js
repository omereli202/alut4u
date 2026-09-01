// "Where are we now" — one big task at a time with a large checkmark that
// advances to the next incomplete task after a calm confirmation.

import { el, icon } from "../../ui.js";
import { audioUrl, toggleItem, visualNode } from "./data.js";

export function renderFocus(host, { items, onList, onExit, onChange }) {
  const remaining = () => items.filter((i) => !i.is_completed);

  function speak(item) {
    const url = audioUrl(item.tts_asset_id);
    if (url) new Audio(url).play().catch(() => {});
  }

  function view() {
    const left = remaining();
    const done = items.length - left.length;

    if (!items.length) {
      return el(
        "div",
        { class: "focus-empty" },
        el("p", { class: "muted" }, "אין משימות להיום."),
        onExit && el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
      );
    }
    if (!left.length) {
      return el(
        "div",
        { class: "focus-done" },
        el("div", { class: "focus-celebrate" }, icon("celebration", { size: 80 })),
        el("h1", {}, "כל הכבוד! סיימנו להיום"),
        el("button", { class: "btn-link", onclick: () => onList?.() }, "צפייה בכל היום"),
      );
    }

    const current = left[0];
    return el(
      "div",
      { class: "focus-view" },
      el(
        "div",
        { class: "focus-progress", "aria-label": `${done} מתוך ${items.length} הושלמו` },
        ...items.map((i) => el("span", { class: i.is_completed ? "dot filled" : "dot" })),
      ),
      el(
        "button",
        { class: "focus-card", onclick: () => speak(current) },
        visualNode(el, current, "focus-visual"),
        el("h1", { class: "focus-title" }, current.title),
        current.start_time && el("p", { class: "focus-time" }, current.start_time.slice(0, 5)),
      ),
      el(
        "button",
        {
          class: "focus-check",
          "aria-label": `סימון "${current.title}" כבוצע`,
          onclick: () => complete(current),
        },
        icon("check", { size: 48 }),
      ),
      el(
        "div",
        { class: "focus-actions" },
        el("button", { class: "btn-link", onclick: () => onList?.() }, "כל היום"),
        onExit && el("button", { class: "btn-link", onclick: onExit }, "יציאה"),
      ),
    );
  }

  function complete(item) {
    toggleItem(item, true);
    onChange?.();
    const card = host.querySelector(".focus-check");
    card?.classList.add("checked");
    host.querySelector(".focus-card")?.classList.add("leaving");
    setTimeout(() => {
      render();
      const next = remaining()[0];
      if (next) speak(next);
    }, 650);
  }

  function render() {
    host.replaceChildren(view());
  }

  render();
}
