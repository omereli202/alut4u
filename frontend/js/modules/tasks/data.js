// "המשימות שלי" data helpers — the only file here that talks to api.js / the
// offline outbox.

import { api } from "../../api.js";
import { enqueue } from "../../outbox.js";
import { visual } from "../../ui.js";

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Returns the whole payload: { items, reward_tokens, reward_claimed, all_done }.
export function loadDay(childId, dateISO) {
  return api.get(`/tasks/day?child_id=${encodeURIComponent(childId)}&date=${dateISO}`);
}

// Optimistic + offline-safe: flip local state now, queue the write. The date is
// sent from the client so a replay after midnight still lands on the day the
// child actually ticked it (same trade-off as the schedule module).
export function toggleTask(task, done, dateISO) {
  task.is_done = done;
  task.completed_on = done ? dateISO : null;
  return enqueue("/tasks/toggle", { task_id: task.id, the_date: dateISO, completed: done });
}

export function audioUrl(id) {
  return id ? `/api/media/${id}` : null;
}

export function visualNode(task, cls) {
  return visual(task, cls);
}
