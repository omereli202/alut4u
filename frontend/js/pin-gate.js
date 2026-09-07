// Inline caregiver-PIN gate (pin.inline — docs/design.md §3): 4 password boxes,
// auto-advance. Renders into `host` (not a full mount), verifies via
// POST /auth/pin, then hands control back. The caller does the privileged call
// and drops elevation — this only gets the session elevated.

import { api } from "./api.js";
import { el, errText, icon } from "./ui.js";

export function pinGate(host, { hint, onElevated, onCancel }) {
  const err = el("p", { class: "err", role: "alert" });
  const digits = ["", "", "", ""];
  const boxes = [0, 1, 2, 3].map((i) =>
    el("input", {
      type: "password",
      inputmode: "numeric",
      maxlength: 1,
      class: "pin-box",
      "aria-label": `ספרה ${i + 1} מתוך 4`,
      oninput: (e) => {
        digits[i] = e.target.value.replace(/\D/g, "");
        e.target.value = digits[i];
        if (digits[i] && i < 3) boxes[i + 1].focus();
        if (digits.every((d) => d)) submit();
      },
      onkeydown: (e) => {
        if (e.key === "Backspace" && !digits[i] && i > 0) boxes[i - 1].focus();
      },
    }),
  );

  async function submit() {
    const pin = digits.join("");
    if (pin.length !== 4) return;
    try {
      await api.post("/auth/pin", { pin });
    } catch (e) {
      err.textContent = errText(e); // "קוד שגוי" / "יותר מדי ניסיונות…"
      digits.fill("");
      boxes.forEach((b) => (b.value = ""));
      boxes[0].focus();
      return;
    }
    onElevated();
  }

  host.replaceChildren(
    el(
      "div",
      { class: "pin-gate" },
      el("div", { class: "pin-gate-icon" }, icon("lock")),
      el("h2", {}, "אישור מטפל"),
      el("p", { class: "muted" }, hint || "מטפל, הזינו קוד:"),
      el("div", { class: "pin-boxes", dir: "ltr" }, ...boxes),
      err,
      el(
        "div",
        { class: "pin-gate-actions" },
        el("button", { class: "btn-link", onclick: onCancel }, "ביטול"),
      ),
    ),
  );
  boxes[0].focus();
}
