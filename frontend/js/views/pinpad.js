// 4-digit PIN pad. Used both to set a PIN (onboarding) and to enter Caregiver
// Mode. Large targets, no text input focus traps.

import { el, mount } from "../ui.js";

export function renderPinpad({ title, hint, onSubmit, onCancel }) {
  let pin = "";

  function dots() {
    return el(
      "div",
      { class: "pin-dots", "aria-label": `${pin.length} מתוך 4 ספרות` },
      ...[0, 1, 2, 3].map((i) => el("span", { class: i < pin.length ? "dot filled" : "dot" })),
    );
  }

  function view() {
    const err = el("p", { class: "err", id: "pin-err", role: "alert" });
    const keys = el(
      "div",
      { class: "pin-keys" },
      ...["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) =>
        el("button", { type: "button", class: "pin-key", onclick: () => press(d) }, d),
      ),
      onCancel
        ? el("button", { type: "button", class: "pin-key subtle", onclick: onCancel }, "ביטול")
        : el("span"),
      el("button", { type: "button", class: "pin-key", onclick: () => press("0") }, "0"),
      el("button", { type: "button", class: "pin-key subtle", onclick: back }, "⌫"),
    );
    return el(
      "section",
      { class: "card pin-card", "data-mode": "caregiver" },
      el("h1", {}, title),
      hint && el("p", { class: "muted" }, hint),
      dots(),
      err,
      keys,
    );
  }

  function refreshDots() {
    const holder = document.querySelector(".pin-dots");
    holder?.replaceWith(dots());
  }

  function press(d) {
    if (pin.length >= 4) return;
    pin += d;
    refreshDots();
    if (pin.length === 4) submit();
  }

  function back() {
    pin = pin.slice(0, -1);
    refreshDots();
  }

  async function submit() {
    const err = document.getElementById("pin-err");
    err.textContent = "";
    try {
      await onSubmit(pin);
    } catch (e) {
      pin = "";
      refreshDots();
      err.textContent = e;
    }
  }

  mount(view());
}
