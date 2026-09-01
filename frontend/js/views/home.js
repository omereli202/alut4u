// User Mode home — what the child sees. Pick a child, then the enabled modules
// show as large tiles. Modules themselves are Phase 2+; for now they're
// placeholders. A small corner control opens the PIN pad for Caregiver Mode.

import { api } from "../api.js";
import { el, emptyState, icon, mount, toast } from "../ui.js";
import { renderAacBoard } from "../modules/aac/board.js";
import { renderSchedule } from "../modules/schedule/index.js";
import { renderRules } from "../modules/rules/index.js";
import { renderCalming } from "../modules/calming/index.js";
import { renderStories } from "../modules/stories/index.js";
import { renderLearning } from "../modules/learning/index.js";

const MODULES = {
  aac_enabled: { label: "תקשורת", icon: "forum" },
  schedule_enabled: { label: "לוח זמנים", icon: "calendar_month" },
  rules_enabled: { label: "כללים ואסימונים", icon: "toll" },
  calming_enabled: { label: "פינת רוגע", icon: "spa" },
  social_stories_enabled: { label: "סיפורים חברתיים", icon: "auto_stories" },
  reading_writing_enabled: { label: "קריאה וכתיבה", icon: "menu_book" },
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
      icon("lock"),
    );

    if (!children.length) {
      return el(
        "section",
        { class: "home", "data-mode": "user" },
        lockBtn,
        emptyState({
          title: "ברוכים הבאים",
          body: "מטפל צריך להוסיף פרופיל ילד/ה במצב מטפל.",
        }),
      );
    }

    let modules = {};
    try {
      modules = await api.get(`/children/${activeId}/modules`);
    } catch {
      /* leave empty */
    }
    const enabled = Object.keys(MODULES).filter((k) => modules[k]);

    return el(
      "section",
      { class: "home", "data-mode": "user" },
      lockBtn,
      children.length > 1 && childSwitcher(),
      el("h1", {}, `שלום, ${child?.name ?? ""}`),
      enabled.length
        ? el(
            "div",
            { class: "tile-grid" },
            ...enabled.map((k) =>
              el(
                "button",
                { class: "tile", onclick: () => openModule(k, child) },
                icon(MODULES[k].icon, { size: 40 }),
                el("span", {}, MODULES[k].label),
              ),
            ),
          )
        : emptyState({ title: "אין מודולים פעילים כרגע." }),
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
    if (key === "calming_enabled") {
      return renderCalming({ childName: child.name, onExit: back });
    }
    if (key === "social_stories_enabled") {
      return renderStories({ childId: child.id, childName: child.name, onExit: back });
    }
    if (key === "reading_writing_enabled") {
      return renderLearning({ childId: child.id, childName: child.name, onExit: back });
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
