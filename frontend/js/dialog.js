// Confirmation dialogs — replaces native confirm()/prompt() (docs/design.md §3
// "commission these": dialog / dialog.destructive / dialog.type-to-confirm).
//
// Built on native <dialog>: showModal() gives a real focus trap and Esc-to-close
// for free, so none of that is hand-rolled here. A click that lands on the
// <dialog> element itself (not a descendant) is a backdrop click and also
// closes it. No backdrop-blur — docs/design/stitch-export flagged that as
// glassmorphism, which docs/design.md §3 rules out.

import { el, icon } from "./ui.js";

function open(dialog) {
  document.body.append(dialog);
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener(
      "close",
      () => {
        resolve(dialog.returnValue === "confirm");
        dialog.remove();
      },
      { once: true },
    );
  });
}

function shell({ variant, iconName, title, body, mode }, ...actionsExtra) {
  return el(
    "dialog",
    { class: variant ? `dialog ${variant}` : "dialog", "data-mode": mode || "caregiver" },
    el(
      "div",
      { class: "dialog-head" },
      el("div", { class: "dialog-icon" }, icon(iconName)),
      el("h2", {}, title),
    ),
    body && el("p", { class: "dialog-body" }, body),
    ...actionsExtra,
  );
}

/**
 * Standard confirm/cancel. Resolves true if confirmed.
 * `mode: "user"` sizes buttons to the 60px User-Mode floor (the redeem-reward
 * dialog is the one child-facing case).
 */
export function confirmDialog({ title, body, confirmLabel = "אישור", cancelLabel = "ביטול", mode }) {
  const dialog = shell(
    { iconName: "info", title, body, mode },
    el(
      "form",
      { method: "dialog", class: "dialog-actions" },
      el("button", { class: "btn-link", value: "cancel" }, cancelLabel),
      el("button", { class: "btn-primary", value: "confirm" }, confirmLabel),
    ),
  );
  return open(dialog);
}

/** Same shape, confirm button is destructive. Resolves true if confirmed. */
export function destructiveDialog({ title, body, confirmLabel = "מחיקה", cancelLabel = "ביטול", mode }) {
  const dialog = shell(
    { variant: "destructive", iconName: "warning", title, body, mode },
    el(
      "form",
      { method: "dialog", class: "dialog-actions" },
      el("button", { class: "btn-link", value: "cancel" }, cancelLabel),
      el("button", { class: "btn-primary danger", value: "confirm" }, confirmLabel),
    ),
  );
  return open(dialog);
}

/**
 * Destructive + a text field that must contain `word` verbatim before confirm
 * enables. Account deletion only (docs/design.md T3.9).
 */
export function typeToConfirmDialog({ title, body, word = "DELETE", confirmLabel = "מחיקה", cancelLabel = "ביטול" }) {
  const confirmBtn = el(
    "button",
    { class: "btn-primary danger", value: "confirm", disabled: true },
    confirmLabel,
  );
  const input = el("input", {
    type: "text",
    dir: "ltr",
    "aria-label": `הקלידו ${word} לאישור`,
    oninput: (e) => (confirmBtn.disabled = e.target.value !== word),
  });
  const dialog = shell(
    { variant: "destructive", iconName: "warning", title, body, mode: "caregiver" },
    el("div", { class: "field" }, input),
    el(
      "form",
      { method: "dialog", class: "dialog-actions" },
      el("button", { class: "btn-link", value: "cancel" }, cancelLabel),
      confirmBtn,
    ),
  );
  return open(dialog);
}
