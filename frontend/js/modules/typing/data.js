// Persistence for the typing board: server API + the offline draft (kv) + the
// outbox. The one place this module touches api.js / db.js / outbox.js.
//
// Offline model:
//   - The LIVE DRAFT is one kv entry per child, `typing.drafts.<childId>`, a map
//     of noteId -> draft. Written on every keystroke (debounced by the editor).
//     This is the "text is never lost" guarantee and never touches the network.
//   - The DURABLE SAVE goes through the outbox as POST /typing/notes, coalesced
//     under a stable entry id so ten minutes of offline edits are one queued
//     POST. The note id is client-generated so the replay is idempotent.

import { api } from "../../api.js";
import { kv } from "../../db.js";
import { dropQueued, enqueueAs } from "../../outbox.js";

const DRAFTS_KEY = (childId) => `typing.drafts.${childId}`;
const OPEN_KEY = (childId) => `typing.open.${childId}`;
const OUTBOX_ID = (noteId) => `typing:${noteId}`;

const FONT_FAMILIES = new Set(["rubik", "assistant", "heebo"]);
const SCALE = { sm: 0.85, md: 1, lg: 1.25, xl: 1.6 };
export const SCALE_STEPS = ["sm", "md", "lg", "xl"];

export function newNoteId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// --- drafts (kv) --------------------------------------------------------

// A wedged IndexedDB (e.g. a blocked deleteDatabase, or private mode) can make
// an op hang forever. The draft is a best-effort convenience — never let it
// stall the screen. Fall back to "no drafts" after a short wait.
function withTimeout(promise, ms, fallback) {
  return Promise.race([
    promise.catch(() => fallback),
    new Promise((res) => setTimeout(() => res(fallback), ms)),
  ]);
}

async function readDrafts(childId) {
  return withTimeout(
    (async () => (await kv.get(DRAFTS_KEY(childId))) || {})(),
    1500,
    {},
  );
}

async function writeDrafts(childId, map) {
  await withTimeout(kv.set(DRAFTS_KEY(childId), map), 1500, undefined);
}

export async function saveDraft(note) {
  const map = await readDrafts(note.child_id);
  map[note.note_id] = { ...note, ts: Date.now(), synced: false };
  await writeDrafts(note.child_id, map);
}

export async function dropDraft(childId, noteId) {
  const map = await readDrafts(childId);
  if (map[noteId]) {
    delete map[noteId];
    await writeDrafts(childId, map);
  }
}

export async function rememberOpen(childId, noteId) {
  await withTimeout(kv.set(OPEN_KEY(childId), noteId || ""), 1500, undefined);
}

export async function recallOpen(childId) {
  return withTimeout(
    (async () => (await kv.get(OPEN_KEY(childId))) || null)(),
    1500,
    null,
  );
}

// --- notes ------------------------------------------------------------

// Drop any draft the server has caught up on (server row exists with rev >=
// the draft's). Self-healing: once the outbox flushes, the next list/open call
// clears the stale "נשמר במכשיר" state. Returns the surviving draft map.
async function reconcile(childId, serverRevById) {
  const drafts = await readDrafts(childId);
  let changed = false;
  for (const [id, d] of Object.entries(drafts)) {
    if ((serverRevById.get(id) ?? -1) >= d.rev) {
      delete drafts[id];
      changed = true;
    }
  }
  if (changed) await writeDrafts(childId, drafts);
  return drafts;
}

// Server list, merged with genuinely-pending local drafts (deduped on note_id).
// A draft with no server row yet — or ahead of it — is flagged so the UI can
// show a "נשמר במכשיר" chip.
export async function listNotes(childId) {
  let server = [];
  try {
    server = (await api.get(`/typing/notes?child_id=${encodeURIComponent(childId)}`)).notes;
  } catch {
    server = [];
  }
  const byId = new Map(server.map((n) => [n.id, { ...n, unsynced: false }]));
  const drafts = await reconcile(childId, new Map(server.map((n) => [n.id, n.rev])));

  for (const d of Object.values(drafts)) {
    byId.set(d.note_id, {
      id: d.note_id,
      title: d.title,
      preview: (d.blocks || []).map((b) => b.s).join(" ").trim().slice(0, 80),
      rev: d.rev,
      font_family: d.font_family,
      font_scale: d.font_scale,
      updated_at: new Date(d.ts).toISOString(),
      unsynced: true,
    });
  }
  return [...byId.values()].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));
}

// The note to open: the newer of {server row, local draft}.
export async function getNote(childId, noteId) {
  let server = null;
  try {
    server = await api.get(`/typing/notes/${noteId}`);
  } catch {
    server = null;
  }
  const drafts = await reconcile(childId, new Map(server ? [[server.id, server.rev]] : []));
  const draft = drafts[noteId];
  if (draft && (!server || draft.rev >= server.rev)) {
    return {
      note_id: noteId,
      child_id: childId,
      title: draft.title,
      blocks: draft.blocks,
      rev: draft.rev,
      font_family: draft.font_family,
      font_scale: draft.font_scale,
      restoredDraft: !draft.synced,
    };
  }
  if (server) {
    return {
      note_id: server.id,
      child_id: childId,
      title: server.title,
      blocks: server.blocks,
      rev: server.rev,
      font_family: server.font_family,
      font_scale: server.font_scale,
      restoredDraft: false,
    };
  }
  return null;
}

// Durable save: draft first (synchronous safety), then a coalesced outbox POST.
// The caller owns `rev` and bumps it before each call.
export async function saveNote(note) {
  await saveDraft(note);
  await enqueueAs(OUTBOX_ID(note.note_id), "/typing/notes", {
    child_id: note.child_id,
    note_id: note.note_id,
    title: note.title,
    blocks: note.blocks,
    rev: note.rev,
    font_family: note.font_family,
    font_scale: note.font_scale,
  });
}

// Re-queue any draft that never reached the server (e.g. the app was killed
// while offline). Called on module entry.
export async function flushPendingDrafts(childId) {
  const drafts = await readDrafts(childId);
  for (const d of Object.values(drafts)) {
    if (!d.synced) {
      await enqueueAs(OUTBOX_ID(d.note_id), "/typing/notes", {
        child_id: d.child_id,
        note_id: d.note_id,
        title: d.title,
        blocks: d.blocks,
        rev: d.rev,
        font_family: d.font_family,
        font_scale: d.font_scale,
      });
    }
  }
}

export async function deleteNote(childId, noteId) {
  // Kill any queued save first so a stale replay can't resurrect the note.
  await dropQueued(OUTBOX_ID(noteId));
  await api.del(`/typing/notes/${noteId}`);
  await dropDraft(childId, noteId);
}

export async function speak(noteId, childId) {
  try {
    const { audio_url } = await api.post(`/typing/notes/${noteId}/speak`, { child_id: childId });
    return audio_url ? new Audio(audio_url) : null;
  } catch {
    return null;
  }
}

// --- settings + font application -------------------------------------

export async function loadSettings(childId) {
  try {
    return await api.get(`/typing/settings?child_id=${encodeURIComponent(childId)}`);
  } catch {
    return { font_family: "rubik", font_scale: "md" };
  }
}

export function saveSettings(childId, patch) {
  return api.put("/typing/settings", { child_id: childId, ...patch }).catch(() => {});
}

// Map the font KEY through a frozen allow-list to a data attribute + a scale
// custom property. Never interpolate a server string into a style.
export function applyFontVars(node, { font_family, font_scale } = {}) {
  node.dataset.font = FONT_FAMILIES.has(font_family) ? font_family : "rubik";
  node.style.setProperty("--note-scale", String(SCALE[font_scale] ?? 1));
}
