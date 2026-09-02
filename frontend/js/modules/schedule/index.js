// Schedule module entry (User Mode). Focus view by default; toggles to the full
// day list and the monthly calendar.

import { el, icon, mount, navBar, toast } from "../../ui.js";
import { renderCalendar } from "./calendar.js";
import { renderDayList } from "./day-list.js";
import { loadDay, todayISO } from "./data.js";
import { renderFocus } from "./focus.js";

export async function renderSchedule({ childId, childName, onExit, onHome }) {
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
    navBar({
      onBack: onExit,
      onHome: onHome ?? onExit,
      title: childName || "סדר יום",
      extra: el("button", { class: "btn-link", onclick: showCalendar }, icon("calendar_month"), " חודש"),
    }),
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
