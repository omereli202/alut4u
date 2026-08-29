// Caregiver Mode: chat with the story agent, then compose + save the story.

import { api } from "../../api.js";
import { el, errText, mount, toast } from "../../ui.js";

export async function renderStoriesEditor({ childId, childName, onExit }) {
  let stories = [];
  let messages = []; // {role, content}
  let ready = false;
  let busy = false;

  async function load() {
    stories = (await api.get(`/stories?child_id=${childId}`).catch(() => ({ stories: [] }))).stories;
    if (!messages.length) await sendTurn(null); // kick off the first question
    else render();
  }

  async function sendTurn(userText) {
    busy = true;
    render();
    if (userText != null) messages.push({ role: "user", content: userText });
    try {
      const r = await api.post("/stories/chat", { child_id: childId, messages });
      messages.push({ role: "assistant", content: r.reply });
      ready = r.ready;
    } catch (err) {
      toast(errText(err), "error");
    }
    busy = false;
    render();
  }

  async function compose() {
    if (!ready || busy) return;
    busy = true;
    render();
    try {
      const story = await api.post("/stories/compose", { child_id: childId, messages });
      toast(`הסיפור "${story.title}" נשמר`);
      messages = [];
      ready = false;
      await sendTurn(null);
      await load();
    } catch (err) {
      toast(errText(err), "error");
      busy = false;
      render();
    }
  }

  function render() {
    mount(
      el(
        "section",
        { class: "stories-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `סיפורים חברתיים — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),

        el(
          "div",
          { class: "card" },
          el("h3", {}, "יצירת סיפור חדש"),
          el(
            "div",
            { class: "chat-log" },
            ...messages.map((m) =>
              el("div", { class: m.role === "user" ? "chat-msg me" : "chat-msg bot" }, m.content),
            ),
            busy && el("div", { class: "chat-msg bot" }, "…"),
          ),
          ready
            ? el("button", { class: "btn-primary", disabled: busy, onclick: compose }, "צור את הסיפור")
            : el(
                "form",
                {
                  class: "chat-form",
                  onsubmit: (e) => {
                    e.preventDefault();
                    const inp = e.target.querySelector("input");
                    if (inp.value.trim()) sendTurn(inp.value.trim());
                    inp.value = "";
                  },
                },
                el("input", { type: "text", required: true, maxlength: 300, placeholder: "התשובה שלך…", disabled: busy }),
                el("button", { type: "submit", class: "btn-link", disabled: busy }, "שליחה"),
              ),
        ),

        el(
          "div",
          { class: "card" },
          el("h3", {}, "סיפורים קיימים"),
          stories.length
            ? el(
                "div",
                { class: "editor-card-list" },
                ...stories.map((s) =>
                  el(
                    "div",
                    { class: "editor-card-row" },
                    el("span", { class: "editor-card-label" }, s.title),
                    el(
                      "button",
                      {
                        class: "btn-link danger",
                        onclick: async () => {
                          await api.del(`/stories/${s.id}`);
                          load();
                        },
                      },
                      "מחק",
                    ),
                  ),
                ),
              )
            : el("p", { class: "muted" }, "אין עדיין סיפורים."),
        ),
      ),
    );
  }

  await load();
}
