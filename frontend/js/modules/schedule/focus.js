// "Where are we now" — one big task at a time. The large checkmark marks the
// task done and advances to the next incomplete one. Prev/next arrows let the
// child look back at what already happened and ahead at what's coming *without*
// changing anything — only the checkmark completes a task.

import { celebration, el, emptyState, icon } from "../../ui.js";
import { audioUrl, toggleItem, visualNode } from "./data.js";

export function renderFocus(host, { items, startIndex, onList, onExit, onChange }) {
  const remaining = () => items.filter((i) => !i.is_completed);
  const currentIndex = () => {
    const i = items.findIndex((x) => !x.is_completed);
    return i === -1 ? items.length - 1 : i;
  };

  let index = startIndex ?? currentIndex();
  let browsing = startIndex !== undefined; // the child picked what to look at

  function speak(item) {
    const url = audioUrl(item?.tts_asset_id);
    if (url) new Audio(url).play().catch(() => {});
  }

  function backToNow() {
    index = currentIndex();
    browsing = false;
    render();
  }

  function go(delta) {
    const next = index + delta;
    if (next < 0 || next >= items.length) return;
    index = next;
    browsing = true;
    render();
  }

  function view() {
    const left = remaining();
    const done = items.length - left.length;

    if (!items.length) {
      return el(
        "div",
        { class: "focus-empty" },
        emptyState({ title: "אין משימות להיום.", onBack: onExit }),
      );
    }
    if (!left.length && !browsing) {
      return el(
        "div",
        { class: "focus-done" },
        celebration({ title: "כל הכבוד! סיימנו להיום" }),
        el("button", { class: "btn-link", onclick: () => onList?.() }, "צפייה בכל היום"),
      );
    }

    const cur = currentIndex();
    const item = items[index];
    const rel = index < cur ? "past" : index > cur ? "future" : "now";
    const statusText = { past: "כבר עבר", future: "בהמשך", now: "עכשיו" }[rel];

    return el(
      "div",
      { class: "focus-view" },
      el(
        "div",
        { class: "focus-progress", "aria-label": `${done} מתוך ${items.length} הושלמו` },
        ...items.map((i, n) =>
          el("span", {
            class: (i.is_completed ? "dot filled" : "dot") + (n === index ? " viewing" : ""),
            "aria-current": n === index ? "true" : null,
          }),
        ),
      ),
      el(
        "div",
        { class: "focus-status" },
        el("span", { class: `focus-chip ${rel}` }, statusText),
        rel !== "now" &&
          el("button", { class: "btn-link", onclick: backToNow }, "חזרה לעכשיו"),
      ),
      el(
        "div",
        { class: "focus-stage" },
        el(
          "button",
          {
            class: "focus-nav prev",
            "aria-label": "המשימה הקודמת",
            disabled: index === 0,
            onclick: () => go(-1),
          },
          icon("chevron_right"),
        ),
        el(
          "button",
          { class: "focus-card", onclick: () => speak(item) },
          visualNode(item, "focus-visual"),
          el("h1", { class: "focus-title" }, item.title),
          item.start_time && el("p", { class: "focus-time" }, item.start_time.slice(0, 5)),
        ),
        el(
          "button",
          {
            class: "focus-nav next",
            "aria-label": "המשימה הבאה",
            disabled: index === items.length - 1,
            onclick: () => go(1),
          },
          icon("chevron_left"),
        ),
      ),
      item.is_completed
        ? el(
            "button",
            { class: "focus-check done", "aria-label": "כבר בוצע", disabled: true },
            icon("check", { size: 48 }),
          )
        : el(
            "button",
            {
              class: "focus-check",
              "aria-label": `סימון "${item.title}" כבוצע`,
              onclick: () => complete(item),
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
    host.querySelector(".focus-check")?.classList.add("checked");
    host.querySelector(".focus-card")?.classList.add("leaving");
    setTimeout(() => {
      index = currentIndex();
      browsing = false;
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
