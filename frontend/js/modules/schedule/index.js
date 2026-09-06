// Schedule module entry (User Mode). The full day list is the landing view;
// from a row you drop into the focus view for that one task, and the monthly
// calendar is one tap away.

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

  // startIndex: undefined → focus starts on the current task; a number → on
  // that specific row the child tapped.
  function showFocus(startIndex) {
    renderFocus(host, { items, startIndex, onList: showList, onChange: () => {} });
  }
  function showList() {
    renderDayList(host, { items, onFocus: showFocus, onChange: () => {} });
  }
  async function showCalendar() {
    await renderCalendar(host, { childId, onExit: showList });
  }

  mount(screen);
  showList();
}
