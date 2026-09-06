// Typing practice by level. The child copies/spells a target; the server checks
// it (lenient Hebrew comparison). A correct answer completes the task — it
// doesn't come back. Every 3 completed tasks in a level is a milestone the
// caregiver releases with their PIN.

import { api, ApiError } from "../../api.js";
import { el, emptyState, errText, icon, toast } from "../../ui.js";
import { pinGate } from "./pin-gate.js";

const EMPTY = { tasks: [], progress: { completed: 0, toward_next: 0, unclaimed: 0 } };

export function renderWriting(host, { childId, onBalance }) {
  let level = 1;
  let data = EMPTY;

  async function load() {
    try {
      data = await api.get(`/learning/writing?child_id=${childId}&level=${level}`);
    } catch {
      data = EMPTY;
    }
    list();
  }

  function levelTabs() {
    return el(
      "div",
      { class: "cat-tabs" },
      ...[1, 2, 3].map((n) =>
        el(
          "button",
          {
            class: n === level ? "cat-tab active" : "cat-tab",
            onclick: () => {
              if (n === level) return;
              level = n;
              load();
            },
          },
          `רמה ${n}`,
        ),
      ),
    );
  }

  function progressRow() {
    const p = data.progress;
    return el(
      "div",
      { class: "learn-progress" },
      el("span", {}, `הושלמו ברמה זו: ${p.completed} · לפרס הבא: ${p.toward_next}/3`),
      p.unclaimed > 0 &&
        el(
          "button",
          { class: "btn-primary learn-claim", onclick: claim },
          icon("star", { size: 18 }),
          ` קרא למטפל לקבלת הנקודות (+${p.unclaimed * 3})`,
        ),
    );
  }

  function list() {
    host.replaceChildren(
      el(
        "div",
        { class: "learning-tab" },
        levelTabs(),
        progressRow(),
        data.tasks.length
          ? el(
              "div",
              { class: "lesson-list" },
              ...data.tasks.map((p) =>
                el(
                  "button",
                  { class: "lesson-item", onclick: () => open(p) },
                  el("span", { class: "lesson-level" }, `רמה ${p.level}`),
                  el("span", {}, p.hint || "תרגיל הקלדה"),
                ),
              ),
            )
          : emptyState({ iconName: "menu_book", title: "כל הכבוד! סיימת את כל המטלות ברמה הזו." }),
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
        if (res.correct) {
          toast("נכון! 🎉");
          load();
          return;
        }
        host.replaceChildren(
          el(
            "div",
            { class: "lesson-result" },
            el(
              "div",
              { class: "lesson-result-gentle" },
              icon("thumb_up", { size: 48 }),
              el("p", {}, `כמעט! הכיתוב הנכון: ${res.target}`),
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

  function claim() {
    pinGate(host, {
      hint: "מטפל, הזינו קוד כדי לקבל את הנקודות:",
      onCancel: list,
      onElevated: async () => {
        let msg = "הנקודות ניתנו ✓";
        let kind;
        try {
          const res = await api.post("/learning/claim", {
            child_id: childId,
            kind: "writing",
            level,
          });
          onBalance?.(res.balance);
        } catch (e) {
          msg =
            e instanceof ApiError && e.code === "nothing_to_claim"
              ? "אין פרס לממש"
              : errText(e);
          kind = "error";
        } finally {
          await api.del("/auth/pin/elevation").catch(() => {});
        }
        await load();
        toast(msg, kind);
      },
    });
  }

  load();
  return () => {};
}
