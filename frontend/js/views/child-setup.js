// Caregiver Mode — guided setup wizard for a child profile. Walks the caregiver
// through every module editor in one sequence, so all the content can be
// prepared up front before the tablet is handed to the child. Reached right
// after creating a child, and from a "הגדרת הפרופיל" button on every child card.
//
// Every editor calls mount() (ui.js), which replaces all of #main — so the
// wizard can't wrap an editor in a frame *inside* #main. Instead it keeps a
// fixed bar appended to <body>, outside #main, which survives each editor's
// re-render. finish() removes it.
//
// Every step is always shown, even for a module whose toggle is off: the
// point is to let the caregiver prepare content first and enable the module
// later. "פינת רוגע" has no per-child editor, so it isn't a step.

import { el, emptyState, icon, mount, toast } from "../ui.js";
import { renderAacEditor } from "../modules/aac/editor.js";
import { renderScheduleEditor } from "../modules/schedule/editor.js";
import { renderRulesEditor } from "../modules/rules/editor.js";
import { renderStoriesEditor } from "../modules/stories/editor.js";
import { renderLearningEditor } from "../modules/learning/editor.js";
import { renderTypingViewer } from "../modules/typing/viewer.js";
import { renderTasksEditor } from "../modules/tasks/editor.js";
import { renderPaintingViewer } from "../modules/painting/viewer.js";

const STEPS = [
  { label: "בוא נדבר", render: renderAacEditor },
  { label: "סדר יום", render: renderScheduleEditor },
  { label: "הכללים שלי", render: renderRulesEditor },
  { label: "סיפורים חברתיים", render: renderStoriesEditor },
  { label: "קריאה והקלדה", render: renderLearningEditor },
  { label: "הפתקים שלי", render: renderTypingViewer },
  { label: "המשימות שלי", render: renderTasksEditor },
  { label: "בוא נצייר", render: renderPaintingViewer },
];

export function renderChildSetup({ childId, childName, onDone }) {
  let i = 0;

  const title = el("span", { class: "setup-bar-title" });
  const fill = el("span", { class: "setup-bar-fill" });
  const nextBtn = el("button", { class: "btn-primary", type: "button", onclick: advance });

  const bar = el(
    "div",
    { class: "setup-bar", role: "region", "aria-label": `הגדרת הפרופיל של ${childName}` },
    el(
      "div",
      { class: "setup-bar-info" },
      title,
      el("span", { class: "setup-bar-track" }, fill),
    ),
    el(
      "div",
      { class: "setup-bar-actions" },
      el("button", { class: "btn-link", type: "button", onclick: finish }, "סיום ההגדרה"),
      el("button", { class: "btn-link", type: "button", onclick: advance }, "דלג"),
      nextBtn,
    ),
  );

  function showStep() {
    const step = STEPS[i];
    const last = i === STEPS.length - 1;
    title.textContent = `שלב ${i + 1} מתוך ${STEPS.length} — ${step.label}`;
    fill.style.inlineSize = `${((i + 1) / STEPS.length) * 100}%`;
    nextBtn.replaceChildren(
      el("span", {}, last ? "סיום" : "הבא"),
      icon(last ? "check" : "arrow_forward", { size: 18, flip: !last }),
    );
    // The editor's own "חזרה" button is wired to onExit → advance, so it moves
    // forward through the wizard rather than dead-ending. If the editor fails
    // to load (a module editor throws on its initial fetch), show a placeholder
    // in #main so it doesn't contradict the step title, and let the caregiver
    // move on — the module can be set up later from its card.
    const rendering = i;
    Promise.resolve(step.render({ childId, childName, onExit: advance })).catch(() => {
      if (i !== rendering) return; // already moved on
      toast("לא ניתן לטעון את שלב ההגדרה", "error");
      mount(
        el(
          "section",
          { class: "child-setup-error", "data-mode": "caregiver" },
          emptyState({
            iconName: "wifi_off",
            title: `לא הצלחנו לטעון את "${step.label}"`,
            body: "אפשר להמשיך ולהגדיר את המודול הזה מאוחר יותר מכרטיס הפרופיל.",
          }),
        ),
      );
    });
  }

  function advance() {
    if (i >= STEPS.length - 1) return finish();
    i += 1;
    showStep();
  }

  function finish() {
    bar.remove();
    delete document.body.dataset.setup;
    onDone();
  }

  document.body.dataset.setup = "1";
  document.body.append(bar);
  showStep();
}
