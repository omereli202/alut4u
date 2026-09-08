// Caregiver Mode dashboard. Children + per-child module toggles, add a child,
// account data controls, and exit back to User Mode.

import { api } from "../api.js";
import { getActiveChildId, setActiveChildId } from "../active-child.js";
import { el, emptyState, errText, icon, mount, toast, withBusy } from "../ui.js";
import { destructiveDialog, typeToConfirmDialog } from "../dialog.js";
import { renderAacEditor } from "../modules/aac/editor.js";
import { renderScheduleEditor } from "../modules/schedule/editor.js";
import { renderRulesEditor } from "../modules/rules/editor.js";
import { renderStoriesEditor } from "../modules/stories/editor.js";
import { renderLearningEditor } from "../modules/learning/editor.js";
import { renderTypingViewer } from "../modules/typing/viewer.js";
import { renderTasksEditor } from "../modules/tasks/editor.js";
import { renderPaintingViewer } from "../modules/painting/viewer.js";
import { renderChildSetup } from "./child-setup.js";

const MODULES = [
  ["aac_enabled", "בוא נדבר (AAC)"],
  ["schedule_enabled", "סדר יום"],
  ["rules_enabled", "הכללים שלי"],
  ["calming_enabled", "פינת רוגע"],
  ["social_stories_enabled", "סיפורים חברתיים"],
  ["reading_writing_enabled", "קריאה והקלדה"],
  ["typing_board_enabled", "הפתקים שלי (לוח הקלדה)"],
  ["tasks_enabled", "המשימות שלי"],
  ["painting_enabled", "בוא נצייר"],
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
            ? el(
                "span",
                { class: "queue-badge", title: "בקשות פרס ממתינות" },
                String(pending.length),
                icon("star", { size: 16 }),
              )
            : null,
        ),
        el("button", { class: "btn-link", onclick: exit }, "יציאה ממצב מטפל"),
      ),
      children.length > 1 ? activeChildSwitcher(children) : null,
      el("h2", {}, "חברים"),
      ...(children.length
        ? await Promise.all(children.map(childCard))
        : [emptyState({ iconName: "manage_accounts", title: "עדיין לא נוספו חברים." })]),
      addChildForm(),
      el("h2", {}, "החשבון שלי"),
      accountSection(),
    );
  }

  // Which profile User Mode opens on. Choosing one also leaves Caregiver Mode
  // straight away — the caregiver hands the tablet back set to that child.
  function activeChildSwitcher(children) {
    const activeId = children.some((c) => c.id === getActiveChildId())
      ? getActiveChildId()
      : children[0]?.id;
    return el(
      "div",
      { class: "active-child" },
      el("p", { class: "muted" }, "הפרופיל שמוצג במצב משתמש:"),
      el(
        "div",
        { class: "child-switch" },
        ...children.map((c) =>
          el(
            "button",
            {
              class: c.id === activeId ? "chip active" : "chip",
              onclick: () => {
                setActiveChildId(c.id);
                exit();
              },
            },
            c.name,
          ),
        ),
      ),
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
      el(
        "div",
        { class: "child-card-head" },
        el("span", { class: "child-avatar", "aria-hidden": "true" }, child.name.slice(0, 1)),
        el("h3", {}, child.name),
      ),
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
        el(
          "button",
          {
            class: "btn-link",
            onclick: () =>
              renderChildSetup({ childId: child.id, childName: child.name, onDone: load }),
          },
          "הגדרת הפרופיל",
        ),
        modules.aac_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderAacEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך בוא נדבר",
          ),
        modules.schedule_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderScheduleEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך סדר יום",
          ),
        modules.rules_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderRulesEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך כללים",
          ),
        modules.social_stories_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderStoriesEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך סיפורים חברתיים",
          ),
        modules.reading_writing_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderLearningEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך קריאה והקלדה",
          ),
        modules.typing_board_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderTypingViewer({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך את הפתקים שלי",
          ),
        modules.tasks_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderTasksEditor({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך את המשימות שלי",
          ),
        modules.painting_enabled &&
          el(
            "button",
            {
              class: "btn-link",
              onclick: () =>
                renderPaintingViewer({ childId: child.id, childName: child.name, onExit: load }),
            },
            "ערוך את בוא נצייר",
          ),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              const ok = await destructiveDialog({
                title: "הסתרת פרופיל",
                body: `להסתיר את הפרופיל של ${child.name}?`,
                confirmLabel: "הסתרה",
              });
              if (!ok) return;
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
      el("h3", {}, "הוספת חבר/ה"),
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
      el("hr"),
      // CC BY-SA 4.0 requires attribution — see docs/symbols.md.
      el(
        "p",
        { class: "muted", style: "font-size: var(--text-sm)" },
        "סמלי התקשורת בלוח: ",
        el(
          "a",
          {
            href: "https://mulberrysymbols.org/",
            target: "_blank",
            rel: "noopener",
            style: "color: inherit; text-decoration: underline",
          },
          "Mulberry Symbols",
        ),
        " מאת Steve Lee, ברישיון ",
        el(
          "a",
          {
            href: "https://creativecommons.org/licenses/by-sa/4.0/",
            target: "_blank",
            rel: "noopener",
            style: "color: inherit; text-decoration: underline",
          },
          "CC BY-SA 4.0",
        ),
        ". אייקוני הממשק: Material Symbols מאת Google, ברישיון Apache-2.0.",
      ),
    );
  }

  async function addChild(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const errEl = document.getElementById("nc-err");
    errEl.textContent = "";
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        const created = await api.post("/children", {
          name: f.get("name"),
          consent_basis: f.get("consent_basis"),
          parental_consent_attested: f.get("parental_consent_attested") === "on",
          board_template_id: f.get("board_template_id") || null,
        });
        // Straight into the guided setup so the caregiver can prepare every
        // module's content before handing over the tablet.
        renderChildSetup({ childId: created.id, childName: created.name, onDone: load });
      } catch (err) {
        errEl.textContent = errText(err);
      }
    });
  }

  async function deleteAccount() {
    const ok = await typeToConfirmDialog({
      title: "מחיקת חשבון וכל הנתונים",
      body: "פעולה בלתי הפיכה. הקלד/י DELETE כדי לאשר מחיקה מלאה:",
      word: "DELETE",
    });
    if (!ok) return;
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
