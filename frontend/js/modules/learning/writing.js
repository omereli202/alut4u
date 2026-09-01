// Writing practice: copy/spell a target. Server checks it (lenient Hebrew
// comparison) and awards a token on success — fully self-serve.

import { api } from "../../api.js";
import { el, icon, toast } from "../../ui.js";

export function renderWriting(host, { childId, onBalance }) {
  let prompts = [];

  async function load() {
    prompts = (await api.get("/learning/writing").catch(() => ({ prompts: [] }))).prompts;
    list();
  }

  function list() {
    host.replaceChildren(
      el(
        "div",
        { class: "lesson-list" },
        ...prompts.map((p) =>
          el(
            "button",
            { class: "lesson-item", onclick: () => open(p) },
            el("span", { class: "lesson-level" }, `רמה ${p.level}`),
            el("span", {}, p.hint || "תרגיל כתיבה"),
          ),
        ),
      ),
    );
  }

  function open(prompt) {
    async function submit(e) {
      e.preventDefault();
      const value = e.target.querySelector("input").value.trim();
      if (!value) return;
      try {
        const res = await api.post("/learning/writing/attempt", {
          child_id: childId,
          prompt_id: prompt.id,
          submitted: value,
        });
        onBalance?.(res.balance);
        host.replaceChildren(
          el(
            "div",
            { class: "lesson-result" },
            el(
              "p",
              { class: "lesson-result-icon" },
              res.correct ? icon("celebration", { size: 64 }) : "🤏",
            ),
            el(
              "p",
              {},
              res.correct
                ? `נכון! +${res.tokens_awarded} אסימון`
                : `כמעט! הכיתוב הנכון: ${res.target}`,
            ),
            el("button", { class: "btn-link", onclick: () => open(prompt) }, "נסה שוב"),
            el("button", { class: "btn-link", onclick: list }, "תרגיל אחר"),
          ),
        );
      } catch {
        toast("לא ניתן לבדוק כרגע", "error");
      }
    }

    host.replaceChildren(
      el(
        "form",
        { class: "writing-view", onsubmit: submit },
        el(
          "div",
          { class: "lesson-top" },
          el("button", { type: "button", class: "btn-link", onclick: list }, icon("arrow_back", { flip: true }), " חזרה"),
        ),
        el("label", { class: "writing-hint", for: "writing-input" }, prompt.hint || "כתבו את המשפט"),
        el("input", {
          id: "writing-input",
          type: "text",
          class: "writing-input",
          required: true,
          maxlength: 300,
          autocomplete: "off",
          autocapitalize: "off",
          spellcheck: "false",
        }),
        el("button", { type: "submit", class: "btn-primary" }, "בדיקה"),
      ),
    );
  }

  load();
  return () => {};
}
