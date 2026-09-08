// User Mode home — what the child sees. The active child profile is picked by
// the caregiver in Caregiver Mode; here the enabled modules for that profile
// show as large tiles. A small corner control opens the PIN pad for Caregiver
// Mode.

import { api } from "../api.js";
import { getActiveChildId } from "../active-child.js";
import { el, emptyState, icon, mount, toast } from "../ui.js";
import { renderAacBoard } from "../modules/aac/board.js";
import { renderSchedule } from "../modules/schedule/index.js";
import { renderRules } from "../modules/rules/index.js";
import { renderCalming } from "../modules/calming/index.js";
import { renderStories } from "../modules/stories/index.js";
import { renderLearning } from "../modules/learning/index.js";
import { renderTyping } from "../modules/typing/index.js";
import { renderMyTasks } from "../modules/tasks/index.js";
import { renderPainting } from "../modules/painting/index.js";

const MODULES = {
  aac_enabled: { label: "בוא נדבר", icon: "forum" },
  schedule_enabled: { label: "סדר יום", icon: "calendar_month" },
  rules_enabled: { label: "הכללים שלי", icon: "toll" },
  calming_enabled: { label: "פינת רוגע", icon: "spa" },
  social_stories_enabled: { label: "סיפורים חברתיים", icon: "auto_stories" },
  reading_writing_enabled: { label: "קריאה והקלדה", icon: "menu_book" },
  typing_board_enabled: { label: "הפתקים שלי", icon: "edit" },
  tasks_enabled: { label: "המשימות שלי", icon: "check_circle" },
  painting_enabled: { label: "בוא נצייר", icon: "brush" },
};

export async function renderHome({ onEnterCaregiver }) {
  let children = [];
  try {
    children = (await api.get("/children")).children;
  } catch {
    toast("לא ניתן לטעון נתונים", "error");
  }

  // The active profile is chosen by the caregiver in Caregiver Mode. User Mode
  // only reads it — no switcher here. Fall back to the first profile when the
  // stored id is missing or points at a hidden child.
  let activeId = getActiveChildId();
  if (!children.some((c) => c.id === activeId)) activeId = children[0]?.id ?? null;

  // Last-loaded module settings for the active child. Kept out here so
  // openModule() can pass playback prefs (e.g. stories_autoplay) into a module.
  let modules = {};

  async function view() {
    const child = children.find((c) => c.id === activeId);
    // A clearly separate, labeled control — not an unlabeled icon crowded
    // next to the friend-switcher chips, which used to read as one cluster.
    const caregiverEntry = el(
      "button",
      { class: "caregiver-entry", onclick: onEnterCaregiver },
      icon("lock"),
      el("span", {}, "מצב מטפל"),
    );

    if (!children.length) {
      return el(
        "section",
        { class: "home", "data-mode": "user" },
        el("div", { class: "home-head" }, el("h1", {}, "ברוכים הבאים"), caregiverEntry),
        emptyState({
          body: "מטפל צריך להוסיף פרופיל חבר/ה במצב מטפל.",
        }),
      );
    }

    try {
      modules = await api.get(`/children/${activeId}/modules`);
    } catch {
      modules = {};
    }
    const enabled = Object.keys(MODULES).filter((k) => modules[k]);

    return el(
      "section",
      { class: "home", "data-mode": "user" },
      el("div", { class: "home-head" }, el("h1", {}, `שלום, ${child?.name ?? ""}`), caregiverEntry),
      enabled.length
        ? el(
            "div",
            { class: "tile-grid" },
            ...enabled.map((k) =>
              el(
                "button",
                { class: "tile", onclick: () => openModule(k, child) },
                el("span", { class: "tile-medallion" }, icon(MODULES[k].icon, { size: 40 })),
                el("span", {}, MODULES[k].label),
              ),
            ),
          )
        : emptyState({ title: "אין מודולים פעילים כרגע." }),
    );
  }

  function openModule(key, child) {
    const home = async () => mount(await view());
    if (key === "aac_enabled") {
      return renderAacBoard({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    if (key === "schedule_enabled") {
      return renderSchedule({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    if (key === "rules_enabled") {
      return renderRules({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    if (key === "calming_enabled") {
      return renderCalming({ childName: child.name, onExit: home, onHome: home });
    }
    if (key === "social_stories_enabled") {
      return renderStories({
        childId: child.id,
        childName: child.name,
        onExit: home,
        onHome: home,
        autoplay: modules.stories_autoplay !== false,
      });
    }
    if (key === "reading_writing_enabled") {
      return renderLearning({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    if (key === "typing_board_enabled") {
      return renderTyping({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    if (key === "tasks_enabled") {
      return renderMyTasks({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    if (key === "painting_enabled") {
      return renderPainting({ childId: child.id, childName: child.name, onExit: home, onHome: home });
    }
    toast("המודול יתווסף בשלב הבא");
  }

  mount(await view());
}
