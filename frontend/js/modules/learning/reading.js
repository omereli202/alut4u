// Reading practice: pick a graded text, read it (with a modelled read-aloud),
// then a caregiver marks pass/fail — which awards tokens. No speech recognition.

import { api, ApiError } from "../../api.js";
import { celebration, el, errText, icon, toast } from "../../ui.js";

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
            v === "pass"
              ? celebration({
                  iconName: "celebration",
                  title: "כל הכבוד!",
                  body: `+${res.tokens_awarded} אסימונים`,
                })
              : el(
                  "div",
                  { class: "lesson-result-gentle" },
                  icon("thumb_up", { size: 48 }),
                  el("p", {}, "עוד נתרגל יחד"),
                ),
            el("button", { class: "btn-link", onclick: list }, "לטקסט נוסף"),
          ),
        );
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) return renderPinGate();
        toast(errText(e), "error");
      }
    }

    // pin.inline (docs/design.md §3 / docs/design/stitch-export-2's `pin/`):
    // 4 separate digit boxes, auto-advance forward on input, back on
    // Backspace-when-empty — distinct from the full pin.keypad in
    // views/pinpad.js, which this screen doesn't use.
    function renderPinGate() {
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
          },
          onkeydown: (e) => {
            if (e.key === "Backspace" && !digits[i] && i > 0) boxes[i - 1].focus();
          },
        }),
      );

      async function submit() {
        pinDigits = digits.join("");
        if (pinDigits.length !== 4) return;
        try {
          await api.post("/auth/pin", { pin: pinDigits });
          view();
        } catch {
          err.textContent = "קוד שגוי";
          digits.fill("");
          boxes.forEach((b) => (b.value = ""));
          boxes[0].focus();
        }
      }

      host.replaceChildren(
        el(
          "div",
          { class: "pin-gate" },
          el("div", { class: "pin-gate-icon" }, icon("lock")),
          el("h2", {}, "אישור מטפל"),
          el("p", { class: "muted" }, "מטפל, הזינו קוד כדי לאשר את הקריאה:"),
          el("div", { class: "pin-boxes", dir: "ltr" }, ...boxes),
          err,
          el(
            "div",
            { class: "pin-gate-actions" },
            el("button", { class: "btn-primary", onclick: submit }, "אישור"),
            el("button", { class: "btn-link", onclick: list }, "ביטול"),
          ),
        ),
      );
      boxes[0].focus();
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
