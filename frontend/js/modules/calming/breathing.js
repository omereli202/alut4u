// Guided breathing — a circle that grows on the in-breath and shrinks on the
// out-breath. Calm, slow. Respects prefers-reduced-motion (falls back to the
// text cue only). Speaks the phase names when a Hebrew voice is available.

import { el } from "../../ui.js";
import { cuesAvailable, speakCue, stopCues } from "./cues.js";

const PHASES = [
  { key: "in", label: "שאיפה", ms: 4000 },
  { key: "hold", label: "החזקה", ms: 2000 },
  { key: "out", label: "נשיפה", ms: 6000 },
];

export function renderBreathing(host) {
  let running = false;
  let timer = null;
  let phase = 0;
  let cuesOn = true;

  // Built once and never re-inserted: removing and re-adding this node would
  // cancel the running CSS transition and make the circle snap instead of
  // grow. toggle()/step() mutate it in place.
  const circle = el("div", { class: "breath-circle" });
  const label = el("p", { class: "breath-label", role: "status", "aria-live": "polite" }, "מוכנים?");
  const startBtn = el("button", { class: "btn-primary", onclick: toggle }, "התחלה");

  const cueBtn = el(
    "button",
    {
      class: "btn-link breath-cue-toggle",
      "aria-pressed": "true",
      onclick: toggleCues,
    },
    "🔊 הקראה",
  );

  function step() {
    const p = PHASES[phase];
    label.textContent = p.label;
    circle.dataset.phase = p.key;
    if (cuesOn) speakCue(p.label);
    timer = setTimeout(() => {
      phase = (phase + 1) % PHASES.length;
      step();
    }, p.ms);
  }

  function toggle() {
    running = !running;
    startBtn.textContent = running ? "עצירה" : "התחלה";
    if (running) {
      phase = 0;
      circle.dataset.phase = "out"; // small resting state
      // Let the small state paint before step() asks for the grow, so the
      // in-breath always animates from small rather than jumping.
      requestAnimationFrame(() => requestAnimationFrame(step));
    } else {
      clearTimeout(timer);
      stopCues();
      circle.dataset.phase = "";
      label.textContent = "מוכנים?";
    }
  }

  function toggleCues() {
    cuesOn = !cuesOn;
    cueBtn.setAttribute("aria-pressed", String(cuesOn));
    cueBtn.textContent = cuesOn ? "🔊 הקראה" : "🔇 הקראה";
    if (!cuesOn) stopCues();
  }

  const controls = el("div", { class: "breath-controls" }, startBtn);
  if (cuesAvailable()) controls.append(cueBtn);

  host.replaceChildren(el("div", { class: "breathing" }, circle, label, controls));

  return () => {
    clearTimeout(timer);
    stopCues();
  };
}
