// Reading practice by level. The child reads a graded text (with a modelled
// read-aloud) and self-marks it read — completed texts don't come back. Every 3
// completed texts in a level is a milestone; the caregiver releases the tokens
// with their PIN.

import { api, ApiError } from "../../api.js";
import { el, emptyState, errText, icon, toast } from "../../ui.js";
import { pinGate } from "../../pin-gate.js";

const EMPTY = { tasks: [], progress: { completed: 0, toward_next: 0, unclaimed: 0 } };

export function renderReading(host, { childId, onBalance }) {
  let level = 1;
  let data = EMPTY;
  let audio = null;

  async function load() {
    try {
      data = await api.get(`/learning/reading?child_id=${childId}&level=${level}`);
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
              ...data.tasks.map((t) =>
                el(
                  "button",
                  { class: "lesson-item", onclick: () => open(t) },
                  el("span", { class: "lesson-level" }, `רמה ${t.level}`),
                  el("span", {}, t.title),
                ),
              ),
            )
          : emptyState({ iconName: "menu_book", title: "כל הכבוד! סיימת את כל המטלות ברמה הזו." }),
      ),
    );
  }

  function open(text) {
    function speak() {
      audio?.pause();
      if (text.audio_url) {
        audio = new Audio(text.audio_url);
        audio.play().catch(() => {});
      }
    }
    async function done() {
      try {
        await api.post(`/learning/reading/${text.id}/done`, { child_id: childId });
        toast("כל הכבוד! 🎉");
        load();
      } catch (e) {
        toast(errText(e), "error");
      }
    }
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
          el("button", { class: "sb-btn", onclick: done }, icon("check"), " קראתי"),
        ),
      ),
    );
  }

  function claim() {
    audio?.pause();
    pinGate(host, {
      hint: "מטפל, הזינו קוד כדי לקבל את הנקודות:",
      onCancel: list,
      onElevated: async () => {
        let msg = "הנקודות ניתנו ✓";
        let kind;
        try {
          const res = await api.post("/learning/claim", {
            child_id: childId,
            kind: "reading",
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
  return () => audio?.pause();
}
