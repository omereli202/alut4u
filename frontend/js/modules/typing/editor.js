// The writing surface. A stack of borderless auto-growing textareas — one per
// block — on one "sheet", so a child who never touches the toolbar just sees
// one big textarea. The sticky toolbar acts on whichever block has focus.
//
// Persistence is not this file's job: it hands a plain note object to data.js
// (draft on a 400ms debounce, durable save on a 3s idle) and calls its cleanup
// on the way out.

import { el, icon, toast } from "../../ui.js";
import { STYLES, normalizeBlocks } from "./blocks.js";
import {
  SCALE_STEPS,
  applyFontVars,
  dropDraft,
  rememberOpen,
  saveDraft,
  saveNote,
  saveSettings,
  speak,
} from "./data.js";

const FONTS = [
  { key: "rubik", label: "רוביק" },
  { key: "assistant", label: "אסיסטנט" },
  { key: "heebo", label: "חיבו" },
];

const DRAFT_MS = 400;
const SAVE_MS = 3000;

export function renderNoteEditor(host, { childId, note, onBack, onSaved }) {
  const state = {
    note_id: note.note_id,
    child_id: childId,
    title: note.title || "",
    blocks: normalizeBlocks(note.blocks),
    rev: note.rev || 1,
    font_family: note.font_family || "rubik",
    font_scale: note.font_scale || "md",
  };

  let focused = 0;
  let dirty = false;
  let audio = null;
  let lastAnnounced = "";
  let draftTimer = null;
  let saveTimer = null;

  const rows = []; // { row, textarea, chip } per block, index-aligned with state.blocks

  const status = el("p", { class: "note-status", role: "status", "aria-live": "polite" });
  const sheet = el("div", { class: "note-sheet" });
  const titleInput = el("input", {
    class: "note-title-input",
    type: "text",
    dir: "auto",
    maxlength: 120,
    placeholder: "שם הפתק",
    "aria-label": "שם הפתק",
    value: state.title,
    oninput: () => {
      state.title = titleInput.value;
      markDirty();
    },
  });

  // --- announce (only on transitions) ---------------------------------
  function announce(msg) {
    if (msg === lastAnnounced) return;
    lastAnnounced = msg;
    status.textContent = msg;
  }

  // --- style toolbar ------------------------------------------------
  const styleButtons = STYLES.map((s) =>
    el(
      "button",
      {
        type: "button",
        class: "note-style-btn",
        role: "radio",
        "aria-checked": "false",
        // pointerdown + preventDefault: keep focus (and the soft keyboard) on
        // the textarea so the page doesn't reflow on every style change.
        onpointerdown: (e) => {
          e.preventDefault();
          setStyle(focused, s.key);
        },
        onclick: (e) => e.preventDefault(),
      },
      s.label,
    ),
  );

  function refreshToolbar() {
    const cur = state.blocks[focused]?.t ?? "p";
    STYLES.forEach((s, i) =>
      styleButtons[i].setAttribute("aria-checked", String(s.key === cur)),
    );
  }

  const toolbar = el(
    "div",
    { class: "note-toolbar", role: "toolbar", "aria-label": "עיצוב טקסט" },
    el("div", { class: "note-style-group", role: "radiogroup", "aria-label": "סגנון השורה" }, ...styleButtons),
    el(
      "div",
      { class: "note-size-group" },
      el("button", { type: "button", class: "note-chip", "aria-label": "טקסט קטן יותר", onclick: () => stepSize(-1) }, "א−"),
      el("button", { type: "button", class: "note-chip", "aria-label": "טקסט גדול יותר", onclick: () => stepSize(1) }, "א+"),
    ),
    (() => {
      const sel = el(
        "select",
        {
          class: "note-font-select",
          "aria-label": "בחירת פונט",
          onchange: () => {
            state.font_family = sel.value;
            applyFontVars(sheet, state);
            saveSettings(childId, { font_family: sel.value });
            markDirty();
          },
        },
        ...FONTS.map((f) => el("option", { value: f.key, selected: f.key === state.font_family }, f.label)),
      );
      return sel;
    })(),
  );

  function setStyle(i, t) {
    const b = state.blocks[i];
    if (!b || b.t === t) return;
    b.t = t;
    const meta = STYLES.find((s) => s.key === t);
    rows[i].textarea.className = `note-blk note-${t}`;
    rows[i].chip.textContent = meta.short;
    rows[i].chip.setAttribute("aria-label", `סגנון: ${meta.label}`);
    autoGrow(rows[i].textarea); // the new size may need more (or less) height
    refreshToolbar();
    markDirty();
  }

  function stepSize(delta) {
    const idx = Math.max(0, Math.min(SCALE_STEPS.length - 1, SCALE_STEPS.indexOf(state.font_scale) + delta));
    if (SCALE_STEPS[idx] === state.font_scale) return;
    state.font_scale = SCALE_STEPS[idx];
    applyFontVars(sheet, state);
    saveSettings(childId, { font_scale: state.font_scale });
    markDirty();
  }

  // --- blocks -----------------------------------------------------
  function autoGrow(ta) {
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }

  function buildRow(i) {
    const b = state.blocks[i];
    const meta = STYLES.find((s) => s.key === b.t);

    const chip = el(
      "button",
      {
        type: "button",
        class: "note-chip note-style-chip",
        "aria-label": `סגנון: ${meta.label}`,
        onclick: () => {
          const order = STYLES.map((s) => s.key);
          setStyle(i, order[(order.indexOf(state.blocks[i].t) + 1) % order.length]);
          rows[i].textarea.focus();
        },
      },
      meta.short,
    );

    const textarea = el("textarea", {
      class: `note-blk note-${b.t}`,
      dir: "auto",
      rows: 1,
      onfocus: () => {
        focused = i;
        refreshToolbar();
      },
      oninput: () => {
        state.blocks[i].s = textarea.value;
        autoGrow(textarea);
        markDirty();
      },
      onkeydown: (e) => onKey(e, i),
    });
    // A <textarea>'s value is its content, not an attribute — set it as a
    // property, not through el()'s attribute path.
    textarea.value = b.s;

    const del = el(
      "button",
      {
        type: "button",
        class: "note-chip note-del",
        "aria-label": "מחיקת שורה",
        onclick: () => removeBlock(i),
      },
      icon("backspace", { flip: true }),
    );

    const row = el(
      "div",
      { class: "note-row" },
      chip,
      textarea,
      state.blocks.length > 1 ? del : null,
    );
    return { row, textarea, chip };
  }

  function paintBlocks() {
    rows.length = 0;
    sheet.replaceChildren(
      titleInput,
      ...state.blocks.map((_, i) => {
        const r = buildRow(i);
        rows.push(r);
        return r.row;
      }),
    );
    state.blocks.forEach((_, i) => autoGrow(rows[i].textarea));
    refreshToolbar();
  }

  function focusBlock(i, caret) {
    const ta = rows[i]?.textarea;
    if (!ta) return;
    ta.focus();
    if (caret != null) ta.setSelectionRange(caret, caret);
    ta.scrollIntoView({ block: "nearest", behavior: "auto" });
  }

  function addBlockAfter(i, text = "") {
    state.blocks.splice(i + 1, 0, { t: "p", s: text });
    focused = i + 1;
    paintBlocks();
    focusBlock(i + 1, 0);
    markDirty();
  }

  function removeBlock(i) {
    if (state.blocks.length <= 1) return;
    state.blocks.splice(i, 1);
    focused = Math.max(0, i - 1);
    paintBlocks();
    focusBlock(focused, rows[focused].textarea.value.length);
    markDirty();
  }

  function onKey(e, i) {
    const ta = rows[i].textarea;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const at = ta.selectionStart;
      const after = ta.value.slice(at);
      state.blocks[i].s = ta.value.slice(0, at);
      addBlockAfter(i, after); // paintBlocks() rebuilds row i from state
      return;
    }
    if (e.key === "Backspace" && ta.selectionStart === 0 && ta.selectionEnd === 0 && i > 0) {
      e.preventDefault();
      const prev = state.blocks[i - 1];
      const mergeAt = prev.s.length;
      prev.s += state.blocks[i].s;
      state.blocks.splice(i, 1);
      focused = i - 1;
      paintBlocks();
      focusBlock(i - 1, mergeAt);
      markDirty();
    }
  }

  // --- save lifecycle -------------------------------------------
  // A note with no title and no block text is not worth saving — changing only
  // the font or a block style on an untouched note must not spawn a ghost.
  function isBlank() {
    return !state.title.trim() && state.blocks.every((b) => !b.s.trim());
  }

  function snapshot() {
    return { ...state, blocks: state.blocks.map((b) => ({ ...b })) };
  }

  function markDirty() {
    dirty = true;
    clearTimeout(draftTimer);
    clearTimeout(saveTimer);
    if (isBlank()) {
      announce("");
      return;
    }
    announce("שומר…");
    draftTimer = setTimeout(persistDraft, DRAFT_MS);
    saveTimer = setTimeout(commit, SAVE_MS);
  }

  function persistDraft() {
    if (!isBlank()) saveDraft(snapshot());
  }

  async function commit({ force = false, announceSaved = true } = {}) {
    clearTimeout(draftTimer);
    clearTimeout(saveTimer);
    if ((!dirty && !force) || isBlank()) return;
    dirty = false;
    state.rev += 1;
    await saveNote(snapshot());
    if (announceSaved) {
      announce(navigator.onLine ? "נשמר" : "נשמר במכשיר — יעלה כשתהיה רשת");
    }
    onSaved?.();
  }

  // --- read aloud ----------------------------------------------
  async function readAloud() {
    audio?.pause();
    if (isBlank()) {
      toast("אין מה להקריא עדיין");
      return;
    }
    await commit({ force: true, announceSaved: false });
    const a = await speak(state.note_id, childId);
    if (!a) {
      toast("הקראה לא זמינה כרגע");
      return;
    }
    audio = a;
    a.play().catch(() => {});
  }

  // --- page-level draft safety --------------------------------
  const onHide = () => {
    if (document.visibilityState === "hidden") persistDraft();
  };
  document.addEventListener("visibilitychange", onHide);
  window.addEventListener("pagehide", persistDraft);

  // --- mount --------------------------------------------------
  applyFontVars(sheet, state);
  rememberOpen(childId, state.note_id);

  host.replaceChildren(
    el(
      "div",
      { class: "typing-editor" },
      el(
        "div",
        { class: "note-editor-top" },
        el(
          "button",
          { type: "button", class: "btn-link", onclick: () => leave() },
          icon("arrow_back", { flip: true }),
          " הפתקים",
        ),
        el(
          "div",
          { class: "note-top-actions" },
          el("button", { type: "button", class: "sb-btn", onclick: readAloud }, icon("volume_up"), " הקראה"),
          el("button", { type: "button", class: "btn-primary", onclick: () => commit({ force: true }).then(() => toast("נשמר")) }, "שמירה"),
        ),
      ),
      toolbar,
      sheet,
      el("button", { type: "button", class: "note-add-row", onclick: () => addBlockAfter(state.blocks.length - 1) }, icon("add"), " שורה חדשה"),
      status,
    ),
  );
  // Now that the sheet is in the document, build the blocks so scrollHeight is
  // real and each textarea grows to fit its content.
  paintBlocks();
  if (note.restoredDraft) announce("טיוטה שלא נשמרה — שוחזרה");
  focusBlock(0, state.blocks[0].s.length);

  async function leave() {
    await cleanup();
    onBack();
  }

  let cleaned = false;
  async function cleanup() {
    if (cleaned) return;
    cleaned = true;
    document.removeEventListener("visibilitychange", onHide);
    window.removeEventListener("pagehide", persistDraft);
    audio?.pause();
    clearTimeout(draftTimer);
    clearTimeout(saveTimer);
    if (isBlank()) {
      await dropDraft(childId, state.note_id); // never leave a ghost
    } else {
      persistDraft();
      if (dirty) await commit({ announceSaved: false });
    }
    await rememberOpen(childId, null);
  }

  return cleanup;
}
