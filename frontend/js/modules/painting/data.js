// Persistence for "בוא נצייר": server API + the offline draft (kv) + the outbox.
// The one place this module touches api.js / db.js / outbox.js.
//
// Offline model (mirrors typing/data.js):
//   - LIVE DRAFT: one kv entry per child, `painting.drafts.<childId>`, a map of
//     paintingId -> draft. Written on an 800ms debounce by the editor (a
//     ~200KB structuredClone into IndexedDB is a coarser unit than a keystroke).
//   - DURABLE SAVE: outbox POST /painting/paintings, coalesced under a stable
//     entry id, monotonic client `rev`. The painting id is client-generated so
//     the replay is idempotent.

import { api } from "../../api.js";
import { kv } from "../../db.js";
import { dropQueued, enqueueAs } from "../../outbox.js";

const DRAFTS_KEY = (c) => `painting.drafts.${c}`;
const OPEN_KEY = (c) => `painting.open.${c}`;
const OUTBOX_ID = (id) => `painting:${id}`;

function withTimeout(promise, ms, fallback) {
  return Promise.race([
    promise.catch(() => fallback),
    new Promise((res) => setTimeout(() => res(fallback), ms)),
  ]);
}

async function readDrafts(childId) {
  return withTimeout((async () => (await kv.get(DRAFTS_KEY(childId))) || {})(), 1500, {});
}
async function writeDrafts(childId, map) {
  await withTimeout(kv.set(DRAFTS_KEY(childId), map), 1500, undefined);
}

export async function saveDraft(painting) {
  const map = await readDrafts(painting.child_id);
  map[painting.painting_id] = { ...painting, ts: Date.now(), synced: false };
  await writeDrafts(painting.child_id, map);
}

export async function dropDraft(childId, id) {
  const map = await readDrafts(childId);
  if (map[id]) {
    delete map[id];
    await writeDrafts(childId, map);
  }
}

export async function rememberOpen(childId, id) {
  await withTimeout(kv.set(OPEN_KEY(childId), id || ""), 1500, undefined);
}
export async function recallOpen(childId) {
  return withTimeout((async () => (await kv.get(OPEN_KEY(childId))) || null)(), 1500, null);
}

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

export async function listPaintings(childId) {
  let server = [];
  try {
    server = (await api.get(`/painting/paintings?child_id=${encodeURIComponent(childId)}`)).paintings;
  } catch {
    server = [];
  }
  const byId = new Map(server.map((p) => [p.id, { ...p, unsynced: false }]));
  const drafts = await reconcile(childId, new Map(server.map((p) => [p.id, p.rev])));
  for (const d of Object.values(drafts)) {
    byId.set(d.painting_id, {
      id: d.painting_id,
      title: d.title,
      page: d.page,
      rev: d.rev,
      updated_at: new Date(d.ts).toISOString(),
      unsynced: true,
      _draft: d,
    });
  }
  return [...byId.values()].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));
}

export async function getPainting(childId, id) {
  let server = null;
  try {
    server = await api.get(`/painting/paintings/${id}`);
  } catch {
    server = null;
  }
  const drafts = await reconcile(childId, new Map(server ? [[server.id, server.rev]] : []));
  const draft = drafts[id];
  if (draft && (!server || draft.rev >= server.rev)) {
    return {
      painting_id: id,
      child_id: childId,
      title: draft.title,
      page: draft.page,
      strokes: draft.strokes,
      fills: draft.fills,
      rev: draft.rev,
    };
  }
  if (server) {
    return {
      painting_id: server.id,
      child_id: childId,
      title: server.title,
      page: server.page,
      strokes: server.strokes,
      fills: server.fills,
      rev: server.rev,
    };
  }
  return null;
}

// Durable save: draft first (synchronous safety), then a coalesced outbox POST.
export async function savePainting(p) {
  await saveDraft(p);
  await enqueueAs(OUTBOX_ID(p.painting_id), "/painting/paintings", {
    child_id: p.child_id,
    painting_id: p.painting_id,
    title: p.title,
    page: p.page,
    strokes: p.strokes,
    fills: p.fills,
    rev: p.rev,
  });
}

export async function flushPendingDrafts(childId) {
  const drafts = await readDrafts(childId);
  for (const d of Object.values(drafts)) {
    if (!d.synced) {
      await enqueueAs(OUTBOX_ID(d.painting_id), "/painting/paintings", {
        child_id: d.child_id,
        painting_id: d.painting_id,
        title: d.title,
        page: d.page,
        strokes: d.strokes,
        fills: d.fills,
        rev: d.rev,
      });
    }
  }
}

export async function deletePainting(childId, id) {
  await dropQueued(OUTBOX_ID(id));
  await api.del(`/painting/paintings/${id}`);
  await dropDraft(childId, id);
}

// --- caregiver colouring pages --------------------------------------

export async function loadExtraPages(childId) {
  try {
    return (await api.get(`/painting/pages?child_id=${encodeURIComponent(childId)}`)).symbol_ids;
  } catch {
    return [];
  }
}

export function saveExtraPages(childId, symbolIds) {
  return api
    .put("/painting/pages", { child_id: childId, symbol_ids: symbolIds })
    .then((r) => r.symbol_ids)
    .catch(() => symbolIds);
}
