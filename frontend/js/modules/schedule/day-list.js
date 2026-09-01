// The full day as a list, with a "read the whole day" button.

import { el, icon } from "../../ui.js";
import { audioUrl, toggleItem, visualNode } from "./data.js";

export function renderDayList(host, { items, onFocus, onExit, onChange }) {
  let reading = false;

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

  function row(item) {
    return el(
      "label",
      { class: item.is_completed ? "sched-row done" : "sched-row" },
      el("input", {
        type: "checkbox",
        checked: item.is_completed,
        onchange: (e) => {
          toggleItem(item, e.target.checked);
          onChange?.();
          render();
        },
      }),
      visualNode(item, "sched-row-visual"),
      el("span", { class: "sched-row-title" }, item.title),
      item.start_time && el("span", { class: "sched-row-time" }, item.start_time.slice(0, 5)),
    );
  }

  function render() {
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
          onFocus && el("button", { class: "btn-link", onclick: onFocus }, "מיקוד"),
          onExit && el("button", { class: "btn-link", onclick: onExit }, "יציאה"),
        ),
        items.length
          ? el("div", { class: "sched-rows" }, ...items.map(row))
          : el("p", { class: "muted" }, "אין משימות להיום."),
      ),
    );
  }

  render();
}
