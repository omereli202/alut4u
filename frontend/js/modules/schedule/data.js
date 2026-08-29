// Schedule data helpers shared by the views.

import { api } from "../../api.js";
import { enqueue } from "../../outbox.js";

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function loadDay(childId, dateISO) {
  return api
    .get(`/schedule/day?child_id=${encodeURIComponent(childId)}&date=${dateISO}`)
    .then((r) => r.items);
}

// Optimistic + offline-safe: flip local state now, queue the write.
export function toggleItem(item, completed) {
  item.is_completed = completed;
  item.completed_at = completed ? new Date().toISOString() : null;
  return enqueue("/schedule/toggle", { item_id: item.id, completed });
}

export function audioUrl(id) {
  return id ? `/api/media/${id}` : null;
}

export function visualNode(el, item, cls = "sched-visual") {
  if (item.symbol_id) {
    return el("img", { class: cls, src: `/assets/symbols/${item.symbol_id}.svg`, alt: "" });
  }
  if (item.icon_asset_id) {
    return el("img", { class: cls, src: `/api/media/${item.icon_asset_id}`, alt: "" });
  }
  return el("div", { class: `${cls} sched-visual-text` }, item.title.slice(0, 2));
}
