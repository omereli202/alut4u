// Schedule editor (Caregiver Mode): build a day's tasks + manage calendar events.

import { api } from "../../api.js";
import { destructiveDialog } from "../../dialog.js";
import { el, errText, icon, mount, symbolUrl, toast, withBusy } from "../../ui.js";
import { createSymbolPicker } from "../aac/symbol-picker.js";
import { todayISO } from "./data.js";

export async function renderScheduleEditor({ childId, childName, onExit }) {
  let dateISO = todayISO();
  let items = [];
  let events = [];
  let templates = null; // loaded once, reused across date changes

  async function load() {
    const monthFirst = dateISO.slice(0, 8) + "01";
    const monthLast = dateISO.slice(0, 8) + "28"; // rough window; fine for the list
    const [dayItems, cal, tpls] = await Promise.all([
      api.get(`/schedule/day?child_id=${childId}&date=${dateISO}`).then((r) => r.items),
      api
        .get(`/schedule/calendar?child_id=${childId}&from=${monthFirst}&to=${monthLast}`)
        .catch(() => ({ events: [] })),
      templates ? Promise.resolve({ templates }) : api.get("/schedule/templates").catch(() => ({ templates: [] })),
    ]);
    items = dayItems;
    events = cal.events;
    templates = tpls.templates;
    render();
  }

  function render() {
    mount(
      el(
        "section",
        { class: "schedule-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `סדר יום — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        el(
          "div",
          { class: "field" },
          el("label", { for: "sc-date" }, "תאריך"),
          el("input", {
            id: "sc-date",
            type: "date",
            value: dateISO,
            onchange: (e) => {
              dateISO = e.target.value;
              load();
            },
          }),
        ),
        el(
          "div",
          { class: "card" },
          el("h3", {}, "משימות היום"),
          el(
            "div",
            { class: "editor-card-list" },
            ...items.map(itemRow),
            !items.length && templatePicker(),
          ),
          itemForm(),
          el(
            "form",
            { class: "copy-day", onsubmit: copyDay },
            el("label", {}, "העתקה מתאריך: "),
            el("input", { type: "date", name: "from", required: true }),
            el("button", { type: "submit", class: "btn-link" }, "העתק"),
          ),
          items.length > 0 && saveTemplateForm(),
        ),
        savedTemplatesCard(),
        el(
          "div",
          { class: "card" },
          el("h3", {}, "אירועים בלוח החודשי"),
          el(
            "div",
            { class: "editor-card-list" },
            ...events.map(eventRow),
            !events.length && el("p", { class: "muted" }, "אין אירועים החודש."),
          ),
          eventForm(),
        ),
      ),
    );
  }

  // --- task rows + form ------------------------------------------------

  function itemRow(item) {
    const i = items.findIndex((x) => x.id === item.id);
    return el(
      "div",
      { class: "editor-card-row" },
      el("span", { class: "editor-card-label" }, `${item.start_time ? item.start_time.slice(0, 5) + " " : ""}${item.title}`),
      el(
        "div",
        { class: "editor-card-actions" },
        el(
          "button",
          { class: "sb-btn", "aria-label": "הזז מוקדם יותר", disabled: i === 0, onclick: () => move(i, -1) },
          icon("chevron_right"),
        ),
        el(
          "button",
          {
            class: "sb-btn",
            "aria-label": "הזז מאוחר יותר",
            disabled: i === items.length - 1,
            onclick: () => move(i, 1),
          },
          icon("chevron_left"),
        ),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              await api.del(`/schedule/items/${item.id}`);
              load();
            },
          },
          "מחק",
        ),
      ),
    );
  }

  async function move(i, delta) {
    const order = items.map((x) => x.id);
    [order[i], order[i + delta]] = [order[i + delta], order[i]];
    try {
      await api.put("/schedule/items/order", { child_id: childId, order });
      await load();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  function itemForm() {
    let symbolId = null;
    const preview = el("span", { class: "muted" }, "בחר סמל (רשות)");
    const picker = createSymbolPicker((s) => {
      symbolId = s.id;
      preview.replaceChildren(el("img", { class: "editor-thumb", src: symbolUrl(s.file_path), alt: s.label_he }));
    });
    return el(
      "form",
      { class: "sched-item-form", onsubmit: (e) => addItem(e, () => symbolId) },
      el("input", { name: "title", type: "text", required: true, maxlength: 80, placeholder: "שם המשימה" }),
      el("input", { name: "start_time", type: "time", "aria-label": "שעה" }),
      preview,
      picker,
      el("button", { type: "submit", class: "btn-primary" }, "הוסף משימה"),
      el("p", { class: "err", role: "alert" }),
    );
  }

  async function addItem(e, getSymbol) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/schedule/items", {
          child_id: childId,
          the_date: dateISO,
          title: f.get("title").trim(),
          start_time: f.get("start_time") || null,
          symbol_id: getSymbol(),
          sort_order: items.length,
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  // Shown only when the day is empty: seed it from a starter routine.
  function templatePicker() {
    if (!templates || !templates.length) {
      return el("p", { class: "muted" }, "אין משימות. הוסיפו למטה או העתיקו מיום אחר.");
    }
    return el(
      "form",
      { class: "template-picker", onsubmit: applyTemplate },
      el("p", { class: "muted" }, "אין משימות. אפשר להתחיל מסדר יום מוכן ולערוך אותו:"),
      el(
        "select",
        { name: "template_id", "aria-label": "סדר יום ברירת מחדל" },
        ...templates.map((t) => el("option", { value: t.id }, t.name_he)),
      ),
      el("button", { type: "submit", class: "btn-primary" }, "צור סדר יום"),
    );
  }

  async function applyTemplate(e) {
    e.preventDefault();
    const templateId = new FormData(e.target).get("template_id");
    if (!templateId) return;
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        const { created } = await api.post("/schedule/apply-template", {
          child_id: childId,
          template_id: templateId,
          the_date: dateISO,
        });
        toast(`נוצרו ${created} משימות`);
        load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  // Shown when the day has tasks: snapshot it as a reusable template.
  function saveTemplateForm() {
    return el(
      "form",
      { class: "save-template", onsubmit: saveTemplate },
      el("label", { for: "sc-tpl-name" }, "שמירת היום כסדר יום ברירת מחדל: "),
      el("input", {
        id: "sc-tpl-name",
        name: "name",
        type: "text",
        required: true,
        maxlength: 60,
        placeholder: "שם (למשל: יום רגיל)",
      }),
      el("button", { type: "submit", class: "btn-link" }, "שמור"),
    );
  }

  async function saveTemplate(e) {
    e.preventDefault();
    const name = new FormData(e.target).get("name").trim();
    if (!name) return;
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/schedule/save-template", {
          child_id: childId,
          the_date: dateISO,
          name_he: name,
        });
        toast("נשמר כסדר יום ברירת מחדל");
        templates = null; // invalidate the memo so the picker + list refresh
        load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  // The caregiver's own saved templates, with delete. Bundled ones aren't here.
  function savedTemplatesCard() {
    const owned = (templates || []).filter((t) => t.owned);
    if (!owned.length) return false;
    return el(
      "div",
      { class: "card" },
      el("h3", {}, "סדרי יום שמורים"),
      el(
        "div",
        { class: "editor-card-list" },
        ...owned.map((t) =>
          el(
            "div",
            { class: "editor-card-row" },
            el("span", { class: "editor-card-label" }, t.name_he),
            el(
              "button",
              { class: "btn-link danger", onclick: () => deleteTemplate(t) },
              "מחק",
            ),
          ),
        ),
      ),
    );
  }

  async function deleteTemplate(t) {
    const ok = await destructiveDialog({
      title: "למחוק סדר יום שמור?",
      body: `"${t.name_he}" יימחק. סדרי יום שכבר נוצרו ממנו לא יושפעו.`,
    });
    if (!ok) return;
    try {
      await api.del(`/schedule/templates/${t.id}`);
      templates = null;
      load();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  async function copyDay(e) {
    e.preventDefault();
    const from = new FormData(e.target).get("from");
    if (!from) return;
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        const { copied } = await api.post("/schedule/copy-day", {
          child_id: childId,
          from_date: from,
          to_date: dateISO,
        });
        toast(`הועתקו ${copied} משימות`);
        load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  // --- calendar events ----------------------------------------------

  function eventRow(ev) {
    return el(
      "div",
      { class: "editor-card-row" },
      el("span", { class: "editor-card-label" }, `${ev.event_date} — ${ev.title}`),
      el(
        "button",
        {
          class: "btn-link danger",
          onclick: async () => {
            await api.del(`/schedule/events/${ev.id}`);
            load();
          },
        },
        "מחק",
      ),
    );
  }

  function eventForm() {
    return el(
      "form",
      { class: "sched-item-form", onsubmit: addEvent },
      el("input", { name: "title", type: "text", required: true, maxlength: 80, placeholder: "כותרת האירוע" }),
      el("input", { name: "event_date", type: "date", required: true, "aria-label": "תאריך" }),
      el("input", { name: "note", type: "text", maxlength: 300, placeholder: "הערה (רשות)" }),
      el("button", { type: "submit", class: "btn-primary" }, "הוסף אירוע"),
      el("p", { class: "err", role: "alert" }),
    );
  }

  async function addEvent(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/schedule/events", {
          child_id: childId,
          title: f.get("title").trim(),
          event_date: f.get("event_date"),
          note: f.get("note").trim() || null,
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  await load();
}
