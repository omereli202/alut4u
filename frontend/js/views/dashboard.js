// Caregiver Mode dashboard. Children + per-child module toggles, add a child,
// account data controls, and exit back to User Mode.

import { api } from "../api.js";
import { el, errText, mount, toast } from "../ui.js";
import { renderAacEditor } from "../modules/aac/editor.js";
import { renderScheduleEditor } from "../modules/schedule/editor.js";
import { renderRulesEditor } from "../modules/rules/editor.js";
import { renderStoriesEditor } from "../modules/stories/editor.js";

const MODULES = [
  ["aac_enabled", "תקשורת (AAC)"],
  ["schedule_enabled", "לוח זמנים"],
  ["rules_enabled", "כללים ואסימונים"],
  ["calming_enabled", "פינת רוגע"],
  ["social_stories_enabled", "סיפורים חברתיים"],
  ["reading_writing_enabled", "קריאה וכתיבה"],
];

export async function renderDashboard({ onExit, onLogout }) {
  let templates = [];
  let pending = [];

  async function load() {
    const [{ children }, tpl, queue] = await Promise.all([
      api.get("/children"),
      api.get("/children/board-templates").catch(() => ({ templates: [] })),
      api.get("/tokens/queue").catch(() => ({ pending: [] })),
    ]);
    templates = tpl.templates;
    pending = queue.pending;
    mount(await view(children));
  }

  async function view(children) {
    return el(
      "section",
      { class: "dashboard", "data-mode": "caregiver" },
      el(
        "header",
        { class: "dash-head" },
        el(
          "h1",
          {},
          "מצב מטפל",
          pending.length
            ? el("span", { class: "queue-badge", title: "בקשות פרס ממתינות" }, ` ${pending.length} ⭐`)
            : null,
        ),
        el("button", { class: "btn-link", onclick: exit }, "יציאה ממצב מטפל"),
      ),
      el("h2", {}, "ילדים"),
      ...(children.length
        ? await Promise.all(children.map(childCard))
        : [el("p", { class: "muted" }, "עדיין לא נוספו ילדים.")]),
      addChildForm(),
      el("h2", {}, "החשבון שלי"),
      accountSection(),
    );
  }

  async function childCard(child) {
    let modules = {};
    try {
      modules = await api.get(`/children/${child.id}/modules`);
    } catch {
      /* ignore */
    }
    return el(
      "article",
      { class: "card child-card" },
      el("h3", {}, child.name),
      el(
        "div",
        { class: "toggle-list" },
        ...MODULES.map(([key, label]) =>
          el(
            "label",
            { class: "toggle" },
            el("input", {
              type: "checkbox",
              checked: !!modules[key],
              onchange: async (e) => {
                try {
                  await api.put(`/children/${child.id}/modules`, { [key]: e.target.checked });
                } catch (err) {
                  e.target.checked = !e.target.checked;
                  toast(errText(err), "error");
                }
              },
            }),
            " ",
            label,
          ),
        ),
      ),
      el(
        "div",
        { class: "child-card-actions" },
        modules.aac_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderAacEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך לוח תקשורת",
          ),
        modules.schedule_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderScheduleEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך לוח זמנים",
          ),
        modules.rules_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderRulesEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "כללים ואסימונים",
          ),
        modules.social_stories_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderStoriesEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "סיפורים חברתיים",
          ),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              if (!confirm(`להסתיר את הפרופיל של ${child.name}?`)) return;
              await api.del(`/children/${child.id}`);
              load();
            },
          },
          "הסתרת פרופיל",
        ),
      ),
    );
  }

  function addChildForm() {
    return el(
      "form",
      { class: "card", onsubmit: addChild },
      el("h3", {}, "הוספת ילד/ה"),
      el(
        "div",
        { class: "field" },
        el("label", { for: "nc-name" }, "שם"),
        el("input", { id: "nc-name", name: "name", type: "text", required: true, maxlength: 80 }),
      ),
      el(
        "div",
        { class: "field" },
        el("label", { for: "nc-basis" }, "בסיס להסכמה"),
        el(
          "select",
          { id: "nc-basis", name: "consent_basis" },
          el("option", { value: "parent" }, "הורה"),
          el("option", { value: "guardian" }, "אפוטרופוס"),
          el(
            "option",
            { value: "professional_with_parental_consent" },
            "איש מקצוע (בהסכמת הורה)",
          ),
        ),
      ),
      el(
        "label",
        { class: "checkbox", id: "nc-attest-wrap", hidden: true },
        el("input", { type: "checkbox", name: "parental_consent_attested" }),
        " אני מאשר/ת שקיבלתי את הסכמת ההורה/אפוטרופוס",
      ),
      el(
        "div",
        { class: "field" },
        el("label", { for: "nc-template" }, "לוח תקשורת התחלתי"),
        el(
          "select",
          { id: "nc-template", name: "board_template_id" },
          el("option", { value: "" }, "ללא — אתחיל מאפס"),
          ...templates.map((t) =>
            el("option", { value: t.id }, `${t.name_he} — ${t.description_he || ""}`),
          ),
        ),
      ),
      el("button", { type: "submit", class: "btn-primary" }, "הוספה"),
      el("p", { class: "err", id: "nc-err", role: "alert" }),
    );
  }

  function accountSection() {
    return el(
      "div",
      { class: "card" },
      el(
        "p",
        {},
        el("a", { href: "/api/account/export", class: "btn-link" }, "הורדת כל הנתונים שלי (JSON)"),
      ),
      el(
        "button",
        { class: "btn-link danger", onclick: deleteAccount },
        "מחיקת החשבון וכל הנתונים",
      ),
      el("hr"),
      el("button", { class: "btn-link", onclick: () => onLogout?.() }, "התנתקות מהמכשיר"),
    );
  }

  async function addChild(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const errEl = document.getElementById("nc-err");
    errEl.textContent = "";
    try {
      await api.post("/children", {
        name: f.get("name"),
        consent_basis: f.get("consent_basis"),
        parental_consent_attested: f.get("parental_consent_attested") === "on",
        board_template_id: f.get("board_template_id") || null,
      });
      load();
    } catch (err) {
      errEl.textContent = errText(err);
    }
  }

  async function deleteAccount() {
    const answer = prompt('פעולה בלתי הפיכה. הקלד/י DELETE כדי לאשר מחיקה מלאה:');
    if (answer !== "DELETE") return;
    await api.del("/account", { confirm: "DELETE" });
    location.reload();
  }

  async function exit() {
    await api.del("/auth/pin/elevation").catch(() => {});
    onExit();
  }

  // Show the professional-attestation checkbox only when relevant.
  document.addEventListener("change", (e) => {
    if (e.target?.id === "nc-basis") {
      const wrap = document.getElementById("nc-attest-wrap");
      if (wrap) wrap.hidden = e.target.value !== "professional_with_parental_consent";
    }
  });

  await load();
}
