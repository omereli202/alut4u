// Caregiver Mode: add / remove reading texts and typing prompts for one child,
// per level. Bundled content is shown read-only; the caregiver's own tasks can
// be deleted.

import { api } from "../../api.js";
import { el, errText, mount, toast, withBusy } from "../../ui.js";

export async function renderLearningEditor({ childId, childName, onExit }) {
  let kind = "reading";
  let level = 1;
  let tasks = [];
  // The child's *actual* level (learning_settings) — separate from `level`
  // above, which is only "which level am I authoring/browsing content for".
  // Conflating the two would mean opening this editor to add a level-3 text
  // silently bumped the child up to level 3.
  let settings = { reading_level: 1, writing_level: 1 };

  async function load() {
    const id = encodeURIComponent(childId);
    try {
      tasks = (await api.get(`/learning/tasks?child_id=${id}&kind=${kind}&level=${level}`)).tasks;
    } catch (e) {
      tasks = [];
      toast(errText(e), "error");
    }
    render();
  }

  async function loadSettings() {
    try {
      settings = await api.get(`/learning/settings?child_id=${encodeURIComponent(childId)}`);
    } catch (e) {
      toast(errText(e), "error");
    }
  }

  async function setChildLevel(field, n) {
    if (settings[field] === n) return;
    const prev = settings[field];
    settings = { ...settings, [field]: n }; // optimistic
    render();
    try {
      settings = await api.put("/learning/settings", { child_id: childId, [field]: n });
    } catch (e) {
      settings = { ...settings, [field]: prev };
      toast(errText(e), "error");
    }
    render();
  }

  function childLevelPicker(label, field) {
    return el(
      "div",
      { class: "field" },
      el("label", {}, label),
      el(
        "div",
        { class: "cat-tabs" },
        ...[1, 2, 3].map((n) =>
          el(
            "button",
            {
              type: "button",
              class: n === settings[field] ? "cat-tab active" : "cat-tab",
              onclick: () => setChildLevel(field, n),
            },
            `רמה ${n}`,
          ),
        ),
      ),
    );
  }

  function tabBtn(k, label) {
    return el(
      "button",
      {
        class: kind === k ? "cat-tab active" : "cat-tab",
        onclick: () => {
          if (kind === k) return;
          kind = k;
          load();
        },
      },
      label,
    );
  }

  function levelBtn(n) {
    return el(
      "button",
      {
        class: n === level ? "cat-tab active" : "cat-tab",
        onclick: () => {
          if (n === level) return;
          level = n;
          load();
        },
      },
      `רמה ${n}`,
    );
  }

  function taskRow(t) {
    const label = kind === "reading" ? t.title : t.hint;
    return el(
      "div",
      { class: t.owned ? "editor-card-row" : "editor-card-row inactive" },
      el("span", { class: "editor-card-label" }, label),
      t.owned
        ? el(
            "button",
            {
              class: "btn-link danger",
              onclick: async () => {
                await api.del(`/learning/${kind}/${t.id}`);
                load();
              },
            },
            "מחק",
          )
        : el("span", { class: "muted" }, "מובנה"),
    );
  }

  function addForm() {
    if (kind === "reading") {
      return el(
        "form",
        { class: "sched-item-form", onsubmit: addReading },
        el("input", { name: "title", type: "text", required: true, maxlength: 60, placeholder: "כותרת" }),
        el("textarea", { name: "body", required: true, maxlength: 600, rows: 3, placeholder: "הטקסט לקריאה" }),
        el("button", { type: "submit", class: "btn-primary" }, "הוסף טקסט"),
        el("p", { class: "err", role: "alert" }),
      );
    }
    return el(
      "form",
      { class: "sched-item-form", onsubmit: addWriting },
      el("input", { name: "hint", type: "text", required: true, maxlength: 120, placeholder: "רמז (מה לכתוב)" }),
      el("input", { name: "target", type: "text", required: true, maxlength: 300, placeholder: "התשובה הנכונה" }),
      el("button", { type: "submit", class: "btn-primary" }, "הוסף תרגיל"),
      el("p", { class: "err", role: "alert" }),
    );
  }

  async function addReading(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/learning/reading", {
          child_id: childId,
          level,
          title: f.get("title").trim(),
          body: f.get("body").trim(),
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  async function addWriting(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/learning/writing", {
          child_id: childId,
          level,
          hint: f.get("hint").trim(),
          target: f.get("target").trim(),
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  function render() {
    mount(
      el(
        "section",
        { class: "learning-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `עריכת קריאה והקלדה — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        el(
          "div",
          { class: "card" },
          el("h3", {}, "הרמה של הילד/ה כרגע"),
          el(
            "p",
            { class: "muted" },
            "כאן קובעים באיזו רמה הילד/ה יקבל/תקבל את מטלות הקריאה וההקלדה — בנפרד לכל אחד מהם.",
          ),
          childLevelPicker("קריאה", "reading_level"),
          childLevelPicker("הקלדה", "writing_level"),
        ),
        el("h3", {}, "עריכת תוכן"),
        el("div", { class: "cat-tabs segmented" }, tabBtn("reading", "קריאה"), tabBtn("writing", "הקלדה")),
        el("div", { class: "cat-tabs" }, levelBtn(1), levelBtn(2), levelBtn(3)),
        el(
          "div",
          { class: "card" },
          el("h3", {}, `מטלות — ${kind === "reading" ? "קריאה" : "הקלדה"}, רמה ${level}`),
          tasks.length
            ? el("div", { class: "editor-card-list" }, ...tasks.map(taskRow))
            : el("p", { class: "muted" }, "אין עדיין מטלות ברמה הזו."),
          addForm(),
        ),
      ),
    );
  }

  await loadSettings();
  await load();
}
