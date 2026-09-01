// Visual monthly calendar of events.

import { api } from "../../api.js";
import { el, icon } from "../../ui.js";

const MONTHS = [
  "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
  "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
];
const WEEKDAYS = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"];

export async function renderCalendar(host, { childId, onExit }) {
  const now = new Date();
  let year = now.getFullYear();
  let month = now.getMonth(); // 0-based

  async function load() {
    const first = `${year}-${String(month + 1).padStart(2, "0")}-01`;
    const last = `${year}-${String(month + 1).padStart(2, "0")}-${String(daysIn(year, month)).padStart(2, "0")}`;
    const { events } = await api
      .get(`/schedule/calendar?child_id=${encodeURIComponent(childId)}&from=${first}&to=${last}`)
      .catch(() => ({ events: [] }));
    render(events);
  }

  function render(events) {
    const byDay = {};
    for (const e of events) (byDay[Number(e.event_date.slice(8, 10))] ||= []).push(e);

    const firstWeekday = new Date(year, month, 1).getDay();
    const total = daysIn(year, month);
    const cells = [];
    for (let i = 0; i < firstWeekday; i++) cells.push(el("div", { class: "cal-cell empty" }));
    for (let d = 1; d <= total; d++) {
      const evs = byDay[d] || [];
      cells.push(
        el(
          "div",
          { class: "cal-cell" + (isToday(d) ? " today" : "") },
          el("span", { class: "cal-day" }, String(d)),
          ...evs.map((e) => el("span", { class: "cal-event", title: e.note || "" }, e.title)),
        ),
      );
    }

    host.replaceChildren(
      el(
        "div",
        { class: "calendar" },
        el(
          "div",
          { class: "cal-head" },
          el("button", { class: "sb-btn", "aria-label": "חודש קודם", onclick: () => step(-1) }, icon("chevron_right")),
          el("h1", {}, `${MONTHS[month]} ${year}`),
          el("button", { class: "sb-btn", "aria-label": "חודש הבא", onclick: () => step(1) }, icon("chevron_left")),
          onExit && el("button", { class: "btn-link", onclick: onExit }, "יציאה"),
        ),
        el("div", { class: "cal-grid" }, ...WEEKDAYS.map((w) => el("div", { class: "cal-wd" }, w)), ...cells),
      ),
    );
  }

  function step(delta) {
    month += delta;
    if (month < 0) {
      month = 11;
      year--;
    } else if (month > 11) {
      month = 0;
      year++;
    }
    load();
  }

  function isToday(d) {
    return year === now.getFullYear() && month === now.getMonth() && d === now.getDate();
  }

  await load();
}

function daysIn(y, m) {
  return new Date(y, m + 1, 0).getDate();
}
