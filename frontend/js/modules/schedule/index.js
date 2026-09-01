// Schedule module entry (User Mode). Focus view by default; toggles to the full
// day list and the monthly calendar.

import { el, icon, mount, toast } from "../../ui.js";
import { renderCalendar } from "./calendar.js";
import { renderDayList } from "./day-list.js";
import { loadDay, todayISO } from "./data.js";
import { renderFocus } from "./focus.js";

export async function renderSchedule({ childId, childName, onExit }) {
  const dateISO = todayISO();
  let items = [];
  try {
    items = await loadDay(childId, dateISO);
  } catch {
    toast("לא ניתן לטעון את הלוח", "error");
  }

  const host = el("div", { class: "schedule-host" });
  const screen = el(
    "section",
    { class: "schedule", "data-mode": "user" },
    el(
      "div",
      { class: "aac-topbar" },
      el("button", { class: "lock-btn", "aria-label": "יציאה", onclick: onExit }, icon("close")),
      el("h1", { class: "aac-title" }, childName || "הלוח שלי"),
      el("button", { class: "btn-link", onclick: showCalendar }, icon("calendar_month"), " חודש"),
    ),
    host,
  );

  function showFocus() {
    renderFocus(host, { items, onList: showList, onChange: () => {} });
  }
  function showList() {
    renderDayList(host, { items, onFocus: showFocus, onChange: () => {} });
  }
  async function showCalendar() {
    await renderCalendar(host, { childId, onExit: showFocus });
  }

  mount(screen);
  showFocus();
}
