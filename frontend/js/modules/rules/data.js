import { api } from "../../api.js";
import { visual } from "../../ui.js";

export { speak as playExplanation, audioUrlFor, prefetch } from "../aac/speech.js";

// The caller's LOCAL date — the once-a-day key for the bonus. Same shape as
// schedule/data.js's todayISO(); kept local so this module doesn't pull in
// the schedule module.
export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function loadRulesModule(childId) {
  const id = encodeURIComponent(childId);
  return Promise.all([
    api.get(`/tokens/rules?child_id=${id}`).then((r) => r.rules),
    api.get(`/tokens/balance?child_id=${id}`),
    api.get(`/tokens/rewards?child_id=${id}`).then((r) => r.rewards),
    api.get(`/tokens/settings?child_id=${id}&on=${todayISO()}`),
  ]).then(([rules, bal, rewards, settings]) => ({
    rules,
    balance: bal.balance,
    transactions: bal.transactions,
    rewards,
    settings,
  }));
}

export function visualNode(item, cls = "rule-visual") {
  return visual(item, cls);
}
