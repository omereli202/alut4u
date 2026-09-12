// Forgot password — a 6-digit email code, then a new password. Two steps in
// one screen; the server verifies the code and sets the password in a single
// call, so there is no half-reset state to track here.

import { api } from "../api.js";
import { applySessionPayload } from "../session.js";
import { el, errText, mount } from "../ui.js";

const RESEND_SECONDS = 60; // matches [auth.email].max_frequency

export function renderPasswordReset({ onDone, onCancel, email = "" }) {
  let step = "request"; // "request" | "confirm"
  let address = email;
  let resendAt = 0;
  let resendTimer = null;

  function render() {
    mount(el("div", { class: "auth-screen" }, view()));
  }

  function view() {
    return step === "request" ? requestView() : confirmView();
  }

  function field(name, label, attrs) {
    const id = `f-reset-${name}`;
    return el(
      "div",
      { class: "field" },
      el("label", { for: id }, label),
      el("input", { id, name, ...attrs }),
    );
  }

  function requestView() {
    const form = el(
      "form",
      { class: "card auth-card", onsubmit: submitRequest },
      el("h1", {}, "alut4u"),
      el("p", { class: "muted" }, "איפוס סיסמה"),
      el("p", {}, "הזינו את כתובת האימייל של החשבון ונשלח אליכם קוד בן 6 ספרות."),
      field("email", "אימייל", {
        type: "email",
        autocomplete: "email",
        required: true,
        value: address,
      }),
      el("button", { type: "submit", class: "btn-primary" }, "שלחו לי קוד"),
      el("button", { type: "button", class: "btn-link", onclick: onCancel }, "חזרה לכניסה"),
      el("p", { class: "err", id: "reset-err", role: "alert" }),
    );
    return form;
  }

  // The resend countdown updates its own button's label every second — it
  // must NEVER trigger a full re-render, or it wipes whatever the caregiver
  // has already typed into the code/password fields underneath it.
  function resendLabel(secondsLeft) {
    return secondsLeft > 0 ? `שלחו קוד חדש (${secondsLeft})` : "שלחו קוד חדש";
  }

  function tickResendButton() {
    const btn = document.getElementById("reset-resend-btn");
    const secondsLeft = Math.max(0, Math.ceil((resendAt - Date.now()) / 1000));
    if (!btn) {
      if (resendTimer) clearInterval(resendTimer);
      resendTimer = null;
      return;
    }
    btn.textContent = resendLabel(secondsLeft);
    btn.disabled = secondsLeft > 0;
    if (secondsLeft <= 0 && resendTimer) {
      clearInterval(resendTimer);
      resendTimer = null;
    }
  }

  function startResendCountdown() {
    resendAt = Date.now() + RESEND_SECONDS * 1000;
    if (resendTimer) clearInterval(resendTimer);
    tickResendButton();
    resendTimer = setInterval(tickResendButton, 1000);
  }

  function confirmView() {
    const secondsLeft = Math.max(0, Math.ceil((resendAt - Date.now()) / 1000));
    const form = el(
      "form",
      { class: "card auth-card", onsubmit: submitConfirm },
      el("h1", {}, "alut4u"),
      el("p", { class: "muted" }, "הזינו את הקוד"),
      el("p", {}, `שלחנו קוד בן 6 ספרות לכתובת ${address}. הקוד תקף ל-10 דקות.`),
      field("code", "קוד בן 6 ספרות", {
        type: "text",
        inputmode: "numeric",
        autocomplete: "one-time-code",
        pattern: "[0-9]{6}",
        maxlength: 6,
        minlength: 6,
        required: true,
        dir: "ltr",
        class: "otp-input",
      }),
      field("password", "סיסמה חדשה", {
        type: "password",
        autocomplete: "new-password",
        required: true,
        minlength: 8,
      }),
      el("p", { class: "muted" }, "לפחות 8 תווים."),
      el("button", { type: "submit", class: "btn-primary" }, "עדכנו סיסמה והיכנסו"),
      el(
        "button",
        {
          id: "reset-resend-btn",
          type: "button",
          class: "btn-link",
          disabled: secondsLeft > 0,
          onclick: resend,
        },
        resendLabel(secondsLeft),
      ),
      el("button", { type: "button", class: "btn-link", onclick: onCancel }, "חזרה לכניסה"),
      el("p", { class: "muted", id: "reset-notice", role: "status" }),
      el("p", { class: "err", id: "reset-err", role: "alert" }),
    );
    return form;
  }

  async function submitRequest(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    address = f.get("email");
    const errEl = document.getElementById("reset-err");
    errEl.textContent = "";
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      await api.post("/auth/password-reset", { email: address });
      step = "confirm";
      render(); // first entry into the confirm form — nothing typed yet to lose
      startResendCountdown();
    } catch (err) {
      errEl.textContent = errText(err);
      btn.disabled = false;
    }
  }

  async function resend() {
    const errEl = document.getElementById("reset-err");
    try {
      await api.post("/auth/password-reset", { email: address });
      startResendCountdown(); // patches the button in place, no remount
      const notice = document.getElementById("reset-notice");
      if (notice) notice.textContent = "קוד חדש נשלח";
    } catch (err) {
      if (errEl) errEl.textContent = errText(err);
    }
  }

  async function submitConfirm(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const errEl = document.getElementById("reset-err");
    errEl.textContent = "";
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const s = await api.post("/auth/password-reset/confirm", {
        email: address,
        code: f.get("code"),
        password: f.get("password"),
      });
      if (resendTimer) clearInterval(resendTimer);
      applySessionPayload(s);
      onDone();
    } catch (err) {
      errEl.textContent = errText(err);
      btn.disabled = false;
      if (err?.code === "invalid_code") {
        const codeEl = document.getElementById("f-reset-code");
        if (codeEl) {
          codeEl.value = "";
          codeEl.focus();
        }
      }
    }
  }

  render();
}
