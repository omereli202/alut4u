// Sign-in / sign-up. First screen when nobody is authenticated.

import { api } from "../api.js";
import { applySessionPayload } from "../session.js";
import { el, errText, mount } from "../ui.js";

export function renderAuth(onDone) {
  let signup = false;

  function view() {
    const form = el(
      "form",
      { class: "card auth-card", onsubmit: submit },
      el("h1", {}, "alut4u"),
      el("p", { class: "muted" }, signup ? "יצירת חשבון מטפל" : "כניסה"),
      signup &&
        field("display_name", "שם", { type: "text", autocomplete: "name", required: true }),
      field("email", "אימייל", { type: "email", autocomplete: "email", required: true }),
      field("password", "סיסמה", {
        type: "password",
        autocomplete: signup ? "new-password" : "current-password",
        required: true,
        minlength: signup ? 8 : 1,
      }),
      signup &&
        el(
          "label",
          { class: "checkbox" },
          el("input", { type: "checkbox", name: "accept_terms", required: true }),
          " קראתי ואני מסכים/ה לתנאי השימוש ולמדיניות הפרטיות",
        ),
      el("button", { type: "submit", class: "btn-primary" }, signup ? "צור חשבון" : "כניסה"),
      el(
        "button",
        {
          type: "button",
          class: "btn-link",
          onclick: () => {
            signup = !signup;
            mount(view());
          },
        },
        signup ? "יש לי כבר חשבון" : "אין לי חשבון — הרשמה",
      ),
      el("p", { class: "err", id: "auth-err", role: "alert" }),
    );
    return form;
  }

  function field(name, label, attrs) {
    const id = `f-${name}`;
    return el(
      "div",
      { class: "field" },
      el("label", { for: id }, label),
      el("input", { id, name, ...attrs }),
    );
  }

  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const errEl = document.getElementById("auth-err");
    errEl.textContent = "";
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const payload = signup
        ? {
            email: f.get("email"),
            password: f.get("password"),
            display_name: f.get("display_name"),
            accept_terms: f.get("accept_terms") === "on",
          }
        : { email: f.get("email"), password: f.get("password") };
      const s = await api.post(signup ? "/auth/signup" : "/auth/login", payload);
      applySessionPayload(s);
      onDone();
    } catch (err) {
      errEl.textContent = errText(err);
      btn.disabled = false;
    }
  }

  mount(view());
}
