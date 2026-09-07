// Caregiver Mode: the child's saved notes — read one, hear it, export/share it,
// delete it, and set the child's default typeface + size for new notes.

import { api } from "../../api.js";
import { destructiveDialog } from "../../dialog.js";
import { el, errText, icon, mount, toast, withBusy } from "../../ui.js";
import { renderBlocksReadOnly } from "./blocks.js";
import { applyFontVars, saveSettings } from "./data.js";
import { copyNote, downloadNote, shareNote } from "./export.js";

const FONTS = [
  { key: "rubik", label: "רוביק" },
  { key: "assistant", label: "אסיסטנט" },
  { key: "heebo", label: "חיבו" },
];
const SIZES = [
  { key: "sm", label: "קטן" },
  { key: "md", label: "רגיל" },
  { key: "lg", label: "גדול" },
  { key: "xl", label: "גדול מאוד" },
];

export async function renderTypingViewer({ childId, childName, onExit }) {
  let notes = [];
  let settings = { font_family: "rubik", font_scale: "md" };
  let audio = null;

  async function load() {
    try {
      [notes, settings] = await Promise.all([
        api.get(`/typing/notes?child_id=${encodeURIComponent(childId)}`).then((r) => r.notes),
        api.get(`/typing/settings?child_id=${encodeURIComponent(childId)}`),
      ]);
    } catch (e) {
      toast(errText(e), "error");
    }
    renderList();
  }

  function settingsCard() {
    const fontSel = el(
      "select",
      {
        "aria-label": "פונט ברירת מחדל",
        onchange: () => {
          settings.font_family = fontSel.value;
          saveSettings(childId, { font_family: fontSel.value });
        },
      },
      ...FONTS.map((f) => el("option", { value: f.key, selected: f.key === settings.font_family }, f.label)),
    );
    const sizeSel = el(
      "select",
      {
        "aria-label": "גודל ברירת מחדל",
        onchange: () => {
          settings.font_scale = sizeSel.value;
          saveSettings(childId, { font_scale: sizeSel.value });
        },
      },
      ...SIZES.map((s) => el("option", { value: s.key, selected: s.key === settings.font_scale }, s.label)),
    );
    return el(
      "div",
      { class: "card" },
      el("h3", {}, "ברירת מחדל לפתק חדש"),
      el("p", { class: "muted" }, "כל פתק שמור נשאר בפונט ובגודל שבהם נכתב."),
      el("div", { class: "field" }, el("label", {}, "פונט"), fontSel),
      el("div", { class: "field" }, el("label", {}, "גודל"), sizeSel),
    );
  }

  function renderList() {
    mount(
      el(
        "section",
        { class: "typing-viewer", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `פתקים — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        settingsCard(),
        el(
          "div",
          { class: "card" },
          el("h3", {}, "הפתקים של הילד/ה"),
          notes.length
            ? el(
                "div",
                { class: "editor-card-list" },
                ...notes.map((n) =>
                  el(
                    "button",
                    { class: "editor-card-row", onclick: () => openNote(n.id) },
                    el("span", { class: "editor-card-label" }, n.title || "פתק בלי שם"),
                    el("span", { class: "muted" }, n.preview || ""),
                  ),
                ),
              )
            : el("p", { class: "muted" }, "אין עדיין פתקים."),
        ),
      ),
    );
  }

  async function openNote(noteId) {
    let note;
    try {
      note = await api.get(`/typing/notes/${noteId}`);
    } catch (e) {
      toast(errText(e), "error");
      return;
    }

    const sheet = el("div", { class: "note-sheet note-print" });
    applyFontVars(sheet, note);
    if (note.title) sheet.append(el("h2", { class: "note-h1" }, note.title));
    sheet.append(renderBlocksReadOnly(note.blocks));

    function playAloud(btn) {
      return withBusy(btn, async () => {
        audio?.pause();
        try {
          const { audio_url } = await api.post(`/typing/notes/${noteId}/speak`, {
            child_id: childId,
          });
          if (!audio_url) return toast("הקראה לא זמינה כרגע");
          audio = new Audio(audio_url);
          audio.play().catch(() => {});
        } catch (e) {
          toast(errText(e), "error");
        }
      });
    }

    mount(
      el(
        "section",
        { class: "typing-viewer", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, note.title || "פתק"),
          el(
            "button",
            {
              class: "btn-link",
              onclick: () => {
                audio?.pause();
                renderList();
              },
            },
            "לרשימה",
          ),
        ),
        sheet,
        el(
          "div",
          { class: "note-actions" },
          el("button", { class: "sb-btn", onclick: (e) => playAloud(e.currentTarget) }, icon("volume_up"), " הקראה"),
          el("button", { class: "sb-btn", onclick: () => shareNote(note) }, " שיתוף"),
          el("button", { class: "sb-btn", onclick: () => downloadNote(note) }, " הורדה"),
          el("button", { class: "sb-btn", onclick: () => copyNote(note) }, " העתקה"),
          el("button", { class: "sb-btn", onclick: () => window.print() }, " הדפסה"),
          el(
            "button",
            {
              class: "btn-link danger",
              onclick: async () => {
                const ok = await destructiveDialog({
                  title: "מחיקת פתק",
                  body: `למחוק את הפתק "${note.title || "בלי שם"}"?`,
                });
                if (!ok) return;
                try {
                  await api.del(`/typing/notes/${noteId}`);
                  toast("נמחק");
                  await load();
                } catch (e) {
                  toast(errText(e), "error");
                }
              },
            },
            "מחיקה",
          ),
        ),
      ),
    );
  }

  await load();
}
