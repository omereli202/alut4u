// Offline write queue.
//
// User-Mode actions that must not be lost when the tablet is offline (schedule
// completions, token events, usage pings) are appended here with a client-side
// idempotency key, then flushed in order when connectivity returns. The server
// dedupes on the idempotency key so a double-flush is harmless.
//
// Phase 0: structure only. Phase 3 wires real endpoints and a Background Sync
// registration.

import { api, ApiError } from "./api.js";
import { outboxStore } from "./db.js";

function newId() {
  return (crypto.randomUUID?.() ?? String(Date.now() + Math.random())).replace(/-/g, "");
}

export async function enqueue(endpoint, body) {
  const entry = { id: newId(), endpoint, body, ts: Date.now() };
  await outboxStore.add(entry);
  if (navigator.onLine) flush();
  return entry.id;
}

let flushing = false;

export async function flush() {
  if (flushing || !navigator.onLine) return;
  flushing = true;
  try {
    const entries = (await outboxStore.all()).sort((a, b) => a.ts - b.ts);
    for (const entry of entries) {
      try {
        await api.post(entry.endpoint, { ...entry.body, idempotency_key: entry.id });
        await outboxStore.del(entry.id);
      } catch (e) {
        // 4xx that isn't auth => permanently bad, drop it. Otherwise stop and
        // retry the whole queue later.
        if (e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 401) {
          await outboxStore.del(entry.id);
          continue;
        }
        break;
      }
    }
  } finally {
    flushing = false;
  }
}

export function startOutbox() {
  window.addEventListener("online", flush);
  flush();
}
