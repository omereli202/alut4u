import { api } from "../../api.js";
import { visual } from "../../ui.js";

export function loadRulesModule(childId) {
  const id = encodeURIComponent(childId);
  return Promise.all([
    api.get(`/tokens/rules?child_id=${id}`).then((r) => r.rules),
    api.get(`/tokens/balance?child_id=${id}`),
    api.get(`/tokens/rewards?child_id=${id}`).then((r) => r.rewards),
  ]).then(([rules, bal, rewards]) => ({
    rules,
    balance: bal.balance,
    transactions: bal.transactions,
    rewards,
  }));
}

export function visualNode(item, cls = "rule-visual") {
  return visual(item, cls);
}

export function playExplanation(rule) {
  const id = rule.audio_asset_id || rule.tts_asset_id;
  if (id) new Audio(`/api/media/${id}`).play().catch(() => {});
}
