// Guided breathing — a circle that grows on the in-breath and shrinks on the
// out-breath. Calm, slow, no sound. Respects prefers-reduced-motion (falls back
// to text cues only).

import { el } from "../../ui.js";

const PHASES = [
  { key: "in", label: "שאיפה", ms: 4000 },
  { key: "hold", label: "החזקה", ms: 2000 },
  { key: "out", label: "נשיפה", ms: 6000 },
];

export function renderBreathing(host) {
  let running = false;
  let timer = null;
  let phase = 0;

  const circle = el("div", { class: "breath-circle" });
  const label = el("p", { class: "breath-label" }, "מוכנים?");

  function step() {
    const p = PHASES[phase];
    label.textContent = p.label;
    circle.dataset.phase = p.key;
    timer = setTimeout(() => {
      phase = (phase + 1) % PHASES.length;
      step();
    }, p.ms);
  }

  function toggle() {
    running = !running;
    if (running) {
      phase = 0;
      step();
    } else {
      clearTimeout(timer);
      circle.dataset.phase = "";
      label.textContent = "מוכנים?";
    }
    render();
  }

  function render() {
    host.replaceChildren(
      el(
        "div",
        { class: "breathing" },
        circle,
        label,
        el("button", { class: "btn-primary", onclick: toggle }, running ? "עצירה" : "התחלה"),
      ),
    );
  }

  render();
  return () => clearTimeout(timer);
}
