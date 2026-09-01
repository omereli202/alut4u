// Reading practice: pick a graded text, read it (with a modelled read-aloud),
// then a caregiver marks pass/fail — which awards tokens. No speech recognition.

import { api, ApiError } from "../../api.js";
import { el, errText, icon, toast } from "../../ui.js";

export function renderReading(host, { childId, onBalance }) {
  let texts = [];
  let audio = null;

  async function load() {
    texts = (await api.get(`/learning/reading`).catch(() => ({ texts: [] }))).texts;
    list();
  }

  function list() {
    host.replaceChildren(
      el(
        "div",
        { class: "lesson-list" },
        ...texts.map((t) =>
          el(
            "button",
            { class: "lesson-item", onclick: () => open(t) },
            el("span", { class: "lesson-level" }, `רמה ${t.level}`),
            el("span", {}, t.title),
          ),
        ),
      ),
    );
  }

  function open(text) {
    let pinDigits = "";

    function speak() {
      audio?.pause();
      if (text.audio_url) {
        audio = new Audio(text.audio_url);
        audio.play().catch(() => {});
      }
    }

    async function verdict(v) {
      try {
        const res = await api.post(`/learning/reading/${text.id}/verdict`, {
          child_id: childId,
          verdict: v,
        });
        onBalance?.(res.balance);
        host.replaceChildren(
          el(
            "div",
            { class: "lesson-result" },
            el(
              "p",
              { class: "lesson-result-icon" },
              v === "pass" ? icon("celebration", { size: 64 }) : icon("thumb_up", { size: 64 }),
            ),
            el("p", {}, v === "pass" ? `כל הכבוד! +${res.tokens_awarded} אסימונים` : "עוד נתרגל יחד"),
            el("button", { class: "btn-link", onclick: list }, "לטקסט נוסף"),
          ),
        );
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) return renderPinGate();
        toast(errText(e), "error");
      }
    }

    function renderPinGate() {
      const err = el("p", { class: "err" });
      host.replaceChildren(
        el(
          "div",
          { class: "lesson-pin" },
          el("label", { for: "verdict-pin" }, "מטפל, הזינו קוד כדי לאשר את הקריאה:"),
          el("input", {
            id: "verdict-pin",
            type: "password",
            inputmode: "numeric",
            maxlength: 4,
            class: "pin-inline",
            oninput: (e) => (pinDigits = e.target.value),
          }),
          el(
            "button",
            {
              class: "btn-primary",
              onclick: async () => {
                try {
                  await api.post("/auth/pin", { pin: pinDigits });
                  view();
                } catch {
                  err.textContent = "קוד שגוי";
                }
              },
            },
            "אישור",
          ),
          err,
          el("button", { class: "btn-link", onclick: list }, "חזרה"),
        ),
      );
    }

    function view() {
      host.replaceChildren(
        el(
          "div",
          { class: "reading-view" },
          el(
            "div",
            { class: "lesson-top" },
            el("button", { class: "btn-link", onclick: list }, icon("arrow_back", { flip: true }), " חזרה"),
            el("strong", {}, text.title),
          ),
          el("p", { class: "reading-body" }, text.body),
          el(
            "div",
            { class: "lesson-actions" },
            el("button", { class: "sb-btn speak", onclick: speak }, icon("volume_up"), " שמיעה"),
            el("button", { class: "sb-btn", onclick: () => verdict("pass") }, icon("check"), " קרא/ה יפה"),
            el("button", { class: "sb-btn", onclick: () => verdict("fail") }, icon("cancel"), " עוד תרגול"),
          ),
        ),
      );
    }

    view();
  }

  load();
  return () => audio?.pause();
}
