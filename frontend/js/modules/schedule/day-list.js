// The full day as a list. Each row has two separate targets: the checkbox
// marks the task done/undone, tapping the task itself opens the focus view on
// it. The first not-done task is marked "עכשיו" and scrolled into view.

import { el, emptyState, icon } from "../../ui.js";
import { audioUrl, toggleItem, visualNode } from "./data.js";

export function renderDayList(host, { items, onFocus, onExit, onChange }) {
  let reading = false;
  let scrolled = false;

  const currentIndex = () => items.findIndex((i) => !i.is_completed);

  async function readAll() {
    if (reading) return;
    reading = true;
    render();
    for (const item of items) {
      const url = audioUrl(item.tts_asset_id);
      if (!url) continue;
      await new Promise((resolve) => {
        const a = new Audio(url);
        a.onended = a.onerror = resolve;
        a.play().catch(resolve);
      });
      if (!reading) break;
    }
    reading = false;
    render();
  }

  function row(item, index, isCurrent) {
    let cls = "sched-row";
    if (item.is_completed) cls += " done";
    if (isCurrent) cls += " current";
    return el(
      "div",
      { class: cls },
      el("input", {
        type: "checkbox",
        checked: item.is_completed,
        "aria-label": `סימון "${item.title}" כבוצע`,
        onchange: (e) => {
          toggleItem(item, e.target.checked);
          onChange?.();
          render();
        },
      }),
      el(
        "button",
        {
          class: "sched-row-main",
          onclick: () => onFocus?.(index),
        },
        visualNode(item, "sched-row-visual"),
        el("span", { class: "sched-row-title" }, item.title),
        isCurrent && el("span", { class: "sched-row-now" }, "עכשיו"),
        item.start_time && el("span", { class: "sched-row-time" }, item.start_time.slice(0, 5)),
      ),
    );
  }

  function render() {
    const cur = currentIndex();
    host.replaceChildren(
      el(
        "div",
        { class: "day-list" },
        el(
          "div",
          { class: "day-list-head" },
          el(
            "button",
            { class: "sb-btn speak", onclick: reading ? () => (reading = false) : readAll },
            reading ? icon("stop_circle") : icon("play_arrow"),
            reading ? " עצור" : " הקראת כל היום",
          ),
          onFocus && cur !== -1 && el("button", { class: "btn-link", onclick: () => onFocus() }, "מה עכשיו"),
          onExit && el("button", { class: "btn-link", onclick: onExit }, "יציאה"),
        ),
        items.length
          ? el("div", { class: "sched-rows" }, ...items.map((it, i) => row(it, i, i === cur)))
          : emptyState({ iconName: "calendar_month", title: "אין משימות להיום." }),
      ),
    );

    if (!scrolled && cur > 0) {
      scrolled = true;
      host.querySelector(".sched-row.current")?.scrollIntoView({ block: "center" });
    }
  }

  render();
}
