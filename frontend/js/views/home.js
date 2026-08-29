// User Mode home — what the child sees. Pick a child, then the enabled modules
// show as large tiles. Modules themselves are Phase 2+; for now they're
// placeholders. A small corner control opens the PIN pad for Caregiver Mode.

import { api } from "../api.js";
import { el, mount, toast } from "../ui.js";
import { renderAacBoard } from "../modules/aac/board.js";
import { renderSchedule } from "../modules/schedule/index.js";
import { renderRules } from "../modules/rules/index.js";

const MODULE_LABELS = {
  aac_enabled: "תקשורת",
  schedule_enabled: "לוח זמנים",
  rules_enabled: "כללים ואסימונים",
  calming_enabled: "פינת רוגע",
  social_stories_enabled: "סיפורים חברתיים",
  reading_writing_enabled: "קריאה וכתיבה",
};

const ACTIVE_CHILD_KEY = "alut4u.activeChild";

export async function renderHome({ onEnterCaregiver }) {
  let children = [];
  try {
    children = (await api.get("/children")).children;
  } catch {
    toast("לא ניתן לטעון נתונים", "error");
  }

  let activeId = null;
  try {
    activeId = localStorage.getItem(ACTIVE_CHILD_KEY);
  } catch {
    /* private mode */
  }
  if (!children.some((c) => c.id === activeId)) activeId = children[0]?.id ?? null;

  async function view() {
    const child = children.find((c) => c.id === activeId);
    const lockBtn = el(
      "button",
      { class: "lock-btn", "aria-label": "מצב מטפל", onclick: onEnterCaregiver },
      "🔒",
    );

    if (!children.length) {
      return el(
        "section",
        { class: "home", "data-mode": "user" },
        lockBtn,
        el("h1", {}, "ברוכים הבאים"),
        el("p", { class: "muted" }, "מטפל צריך להוסיף פרופיל ילד/ה במצב מטפל."),
      );
    }

    let modules = {};
    try {
      modules = await api.get(`/children/${activeId}/modules`);
    } catch {
      /* leave empty */
    }
    const enabled = Object.keys(MODULE_LABELS).filter((k) => modules[k]);

    return el(
      "section",
      { class: "home", "data-mode": "user" },
      lockBtn,
      children.length > 1 && childSwitcher(),
      el("h1", {}, `שלום, ${child?.name ?? ""}`),
      el(
        "div",
        { class: "tile-grid" },
        ...enabled.map((k) =>
          el("button", { class: "tile", onclick: () => openModule(k, child) }, MODULE_LABELS[k]),
        ),
      ),
      !enabled.length && el("p", { class: "muted" }, "אין מודולים פעילים כרגע."),
    );
  }

  function openModule(key, child) {
    const back = async () => mount(await view());
    if (key === "aac_enabled") {
      return renderAacBoard({ childId: child.id, childName: child.name, onExit: back });
    }
    if (key === "schedule_enabled") {
      return renderSchedule({ childId: child.id, childName: child.name, onExit: back });
    }
    if (key === "rules_enabled") {
      return renderRules({ childId: child.id, childName: child.name, onExit: back });
    }
    toast("המודול יתווסף בשלב הבא");
  }

  function childSwitcher() {
    return el(
      "div",
      { class: "child-switch" },
      ...children.map((c) =>
        el(
          "button",
          {
            class: c.id === activeId ? "chip active" : "chip",
            onclick: async () => {
              activeId = c.id;
              try {
                localStorage.setItem(ACTIVE_CHILD_KEY, c.id);
              } catch {
                /* ignore */
              }
              mount(await view());
            },
          },
          c.name,
        ),
      ),
    );
  }

  mount(await view());
}
