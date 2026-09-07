// User Mode: "הפתקים שלי" — the child's list of saved notes, and the composer.
// A note is free text the child writes and saves to show a parent or therapist.

import { el, emptyState, icon, mount, navBar, toast } from "../../ui.js";
import { renderNoteEditor } from "./editor.js";
import {
  flushPendingDrafts,
  getNote,
  listNotes,
  loadSettings,
  newNoteId,
  recallOpen,
} from "./data.js";

export async function renderTyping({ childId, childName, onExit, onHome }) {
  const host = el("div", { class: "typing-host" });
  let cleanupEditor = null;
  // The new-note default; refreshed in the background so it's never a blocker.
  let settings = { font_family: "rubik", font_scale: "md" };

  async function leave() {
    const c = cleanupEditor;
    cleanupEditor = null;
    await c?.();
    onExit();
  }
  async function goHome() {
    const c = cleanupEditor;
    cleanupEditor = null;
    await c?.();
    (onHome ?? onExit)();
  }

  async function showList() {
    if (cleanupEditor) {
      await cleanupEditor();
      cleanupEditor = null;
    }
    host.replaceChildren(el("p", { class: "note-status" }, "טוען…"));
    let notes = [];
    try {
      notes = await listNotes(childId);
    } catch {
      toast("לא ניתן לטעון", "error");
    }
    host.replaceChildren(
      el(
        "div",
        { class: "typing" },
        el(
          "button",
          { class: "btn-primary note-new", onclick: () => openNew() },
          icon("add"),
          " פתק חדש",
        ),
        notes.length
          ? el(
              "div",
              { class: "note-list" },
              ...notes.map((n) =>
                el(
                  "button",
                  { class: "note-card", onclick: () => open(n.id) },
                  el("span", { class: "note-card-title" }, n.title || "פתק בלי שם"),
                  n.preview && el("span", { class: "note-card-meta" }, n.preview),
                  n.unsynced && el("span", { class: "note-card-unsynced" }, "נשמר במכשיר"),
                ),
              ),
            )
          : emptyState({
              iconName: "edit",
              title: "עדיין אין פתקים.",
              body: "אפשר להתחיל לכתוב.",
            }),
      ),
    );
  }

  function openEditor(note) {
    cleanupEditor = renderNoteEditor(host, {
      childId,
      note,
      onBack: showList,
      onSaved: () => {},
    });
  }

  function openNew() {
    openEditor({
      note_id: newNoteId(),
      title: "",
      blocks: [{ t: "p", s: "" }],
      rev: 1,
      font_family: settings.font_family,
      font_scale: settings.font_scale,
    });
  }

  async function open(noteId) {
    const note = await getNote(childId, noteId);
    if (!note) {
      toast("לא ניתן לפתוח את הפתק", "error");
      return;
    }
    openEditor(note);
  }

  mount(
    el(
      "section",
      { class: "typing-screen", "data-mode": "user" },
      navBar({ onBack: leave, onHome: goHome, title: `הפתקים של ${childName || ""}` }),
      host,
    ),
  );

  // Background, non-blocking: settings for the next new note, and re-queueing
  // any draft the app was killed before it could sync.
  loadSettings(childId).then((s) => {
    settings = s;
  });
  flushPendingDrafts(childId).catch(() => {});

  // Resume the note that was open when the app was last killed; otherwise the list.
  const resumeId = await recallOpen(childId);
  if (resumeId) {
    const note = await getNote(childId, resumeId);
    if (note) {
      openEditor(note);
      return;
    }
  }
  await showList();
}
