// Caregiver Mode: chat with the story-agent crew, compose the reviewed text,
// then let illustrations fill in page by page.

import { api } from "../../api.js";
import { el, errText, mount, toast } from "../../ui.js";

const SLOT_LABELS = {
  protagonist: "שם הדמות",
  situation: "המצב / הטריגר",
  schedule: "מתי האירוע",
  goal: "ההתנהגות הרצויה",
  sensory: "רגישויות חושיות",
  triggers: "טריגרים ידועים",
  extras: "משהו נוסף לכלול",
};

export async function renderStoriesEditor({ childId, childName, onExit }) {
  let stories = [];
  let messages = []; // {role, content}
  let slots = {};
  let ready = false;
  let busy = false;

  let draft = null; // the just-composed story we're illustrating
  let artBusy = false;
  let artNow = null; // page index currently being illustrated
  let artNote = "";
  let artToken = 0;
  let edits = null; // { title, pages: [text] } while the caregiver is editing
  let saving = false;

  async function load() {
    stories = (await api.get(`/stories?child_id=${childId}`).catch(() => ({ stories: [] }))).stories;
    if (!draft && !messages.length) await sendTurn(null); // kick off the first question
    else render();
  }

  async function sendTurn(userText) {
    busy = true;
    render();
    if (userText != null) messages.push({ role: "user", content: userText });
    try {
      const r = await api.post("/stories/chat", { child_id: childId, messages });
      messages.push({ role: "assistant", content: r.reply });
      slots = r.slots || {};
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
      draft = await api.post("/stories/compose", { child_id: childId, messages });
      seedEdits();
      messages = [];
      slots = {};
      ready = false;
      busy = false;
      render();
      startArt();
    } catch (err) {
      toast(errText(err), "error");
      busy = false;
      render();
    }
  }

  async function startArt() {
    if (artBusy || !draft) return;
    artBusy = true;
    artNote = "";
    const token = ++artToken;
    for (const idx of [...draft.art.pending_pages]) {
      if (token !== artToken) return; // a newer story superseded this loop
      artNow = idx;
      render();
      try {
        const r = await api.post(`/stories/${draft.id}/illustrate`, { page_index: idx });
        draft.pages[idx].image_url = r.image_url;
        draft.art = r.art;
      } catch (err) {
        if (err.status === 429) {
          artNote = "מכסת האיורים החודשית נגמרה. הסיפור נשמר עם הטקסט וההקראה.";
          break;
        }
        artNote = "איור אחד לא נוצר. אפשר לנסות שוב מאוחר יותר.";
      }
      render();
    }
    artBusy = false;
    artNow = null;
    render();
    await load();
  }

  async function resume(storyId) {
    try {
      draft = await api.get(`/stories/${storyId}`);
      draft.pages.forEach((p) => (p.image_url = p.image_url ?? null));
      seedEdits();
    } catch (err) {
      toast(errText(err), "error");
      return;
    }
    render();
    startArt();
  }

  function seedEdits() {
    edits = { title: draft.title, pages: draft.pages.map((p) => p.text) };
  }

  function editsDirty() {
    if (!edits) return false;
    return (
      edits.title !== draft.title || edits.pages.some((t, i) => t !== draft.pages[i].text)
    );
  }

  async function saveEdits() {
    if (!editsDirty() || saving) return;
    saving = true;
    render();
    try {
      const updated = await api.patch(`/stories/${draft.id}`, {
        title: edits.title,
        pages: edits.pages.map((text) => ({ text })),
      });
      draft = { ...updated, pages: updated.pages.map((p) => ({ ...p })) };
      seedEdits();
      toast("השינויים נשמרו");
    } catch (err) {
      toast(errText(err), "error");
    }
    saving = false;
    render();
  }

  function finishDraft() {
    if (artBusy || saving) return;
    draft = null;
    edits = null;
    artToken++;
    load();
  }

  function slotChecklist() {
    return el(
      "ul",
      { class: "slot-checklist" },
      ...Object.entries(SLOT_LABELS).map(([key, label]) => {
        const val = slots[key];
        return el(
          "li",
          { class: val ? "done" : "pending" },
          el("span", { class: "slot-label" }, `${val ? "✓" : "•"} ${label}`),
          val && el("span", { class: "slot-value" }, val),
        );
      }),
    );
  }

  function draftView() {
    const total = draft.art.total;
    const doneCount = draft.art.illustrated;
    return el(
      "div",
      { class: "card story-preview" },
      el("input", {
        class: "story-title-edit",
        value: edits.title,
        maxlength: 200,
        disabled: artBusy || saving,
        oninput: (e) => {
          edits.title = e.target.value;
          syncSaveButton();
        },
      }),
      el(
        "p",
        { class: draft.revised ? "review-chip revised" : "review-chip" },
        draft.revised
          ? "הסיפור עודכן לפי הערות קלינאי/ת התקשורת"
          : "נבדק ואושר על ידי קלינאי/ת התקשורת",
      ),
      draft.review_notes?.length &&
        el(
          "details",
          { class: "slp-notes" },
          el("summary", {}, `הערות מקצועיות (${draft.review_notes.length})`),
          el("ul", {}, ...draft.review_notes.map((t) => el("li", {}, t))),
        ),
      artBusy &&
        el(
          "div",
          { class: "art-progress" },
          el("progress", { max: String(total), value: String(doneCount) }),
          el("span", { class: "muted" }, `מאייר עמוד ${(artNow ?? 0) + 1} מתוך ${total}…`),
        ),
      artNote && el("p", { class: "muted" }, artNote),
      el(
        "div",
        { class: "preview-pages" },
        ...draft.pages.map((p, i) =>
          el(
            "div",
            { class: "preview-page" },
            p.image_url
              ? el("img", { src: p.image_url, alt: "" })
              : el("div", { class: "ph" }, artNow === i ? "…" : ""),
            el(
              "textarea",
              {
                class: "page-text-edit",
                rows: Math.max(3, Math.ceil((edits.pages[i] || "").length / 45)),
                maxlength: 2000,
                disabled: artBusy || saving,
                oninput: (e) => {
                  edits.pages[i] = e.target.value;
                  syncSaveButton();
                },
              },
              edits.pages[i],
            ),
          ),
        ),
      ),
      el(
        "div",
        { class: "story-preview-actions" },
        el(
          "button",
          {
            class: "btn-link save-edits-btn",
            disabled: !editsDirty() || saving || artBusy,
            onclick: saveEdits,
          },
          saving ? "שומר…" : "שמור שינויים",
        ),
        el(
          "button",
          { class: "btn-primary", disabled: artBusy || saving, onclick: finishDraft },
          "סיום",
        ),
      ),
    );
  }

  function syncSaveButton() {
    const btn = document.querySelector(".save-edits-btn");
    if (btn) btn.disabled = !editsDirty() || saving || artBusy;
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

        draft
          ? draftView()
          : el(
              "div",
              { class: "card" },
              el("h3", {}, "יצירת סיפור חדש"),
              slotChecklist(),
              el(
                "div",
                { class: "chat-log" },
                ...messages.map((m) =>
                  el(
                    "div",
                    { class: m.role === "user" ? "chat-msg me" : "chat-msg bot" },
                    m.content,
                  ),
                ),
                busy && el("div", { class: "chat-msg bot" }, "…"),
              ),
              ready
                ? el(
                    "button",
                    { class: "btn-primary", disabled: busy, onclick: compose },
                    "צור את הסיפור",
                  )
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
                    el("input", {
                      type: "text",
                      required: true,
                      maxlength: 300,
                      placeholder: "התשובה שלך…",
                      disabled: busy,
                    }),
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
                ...stories.map((s) => {
                  const pending = s.art?.pending_pages?.length ?? 0;
                  return el(
                    "div",
                    { class: "editor-card-row" },
                    el("span", { class: "editor-card-label" }, s.title),
                    pending > 0 &&
                      el(
                        "button",
                        { class: "btn-link", disabled: artBusy, onclick: () => resume(s.id) },
                        `המשך איור (${pending})`,
                      ),
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
                  );
                }),
              )
            : el("p", { class: "muted" }, "אין עדיין סיפורים."),
        ),
      ),
    );
  }

  await load();
}
