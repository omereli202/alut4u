// User Mode: "כללים ואסימונים" — token balance, behavior rule cards, reward store.

import { api, ApiError } from "../../api.js";
import { el, mount, toast } from "../../ui.js";
import { loadRulesModule, playExplanation, visualNode } from "./data.js";

export async function renderRules({ childId, childName, onExit }) {
  let data;
  try {
    data = await loadRulesModule(childId);
  } catch {
    return mount(
      el("p", { class: "err" }, "לא ניתן לטעון."),
      el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
    );
  }

  let tab = "rules";

  function view() {
    return el(
      "section",
      { class: "rules-screen", "data-mode": "user" },
      el(
        "div",
        { class: "aac-topbar" },
        el("button", { class: "lock-btn", "aria-label": "יציאה", onclick: onExit }, "✕"),
        el("h1", { class: "aac-title" }, childName || "כללים ואסימונים"),
        el(
          "div",
          { class: "token-badge", "aria-label": `${data.balance} אסימונים` },
          "⭐ ",
          String(data.balance),
        ),
      ),
      el(
        "div",
        { class: "cat-tabs" },
        tabBtn("rules", "כללים"),
        tabBtn("store", "חנות הפרסים"),
      ),
      tab === "rules" ? rulesView() : storeView(),
    );
  }

  function tabBtn(key, label) {
    return el(
      "button",
      {
        class: tab === key ? "cat-tab active" : "cat-tab",
        onclick: () => {
          tab = key;
          mount(view());
        },
      },
      label,
    );
  }

  function rulesView() {
    if (!data.rules.length) return el("p", { class: "muted" }, "אין כללים כרגע.");
    return el(
      "div",
      { class: "rules-list" },
      ...data.rules.map((rule) =>
        el(
          "button",
          { class: "rule-card", onclick: () => playExplanation(rule) },
          visualNode(rule),
          el(
            "div",
            { class: "rule-text" },
            el("strong", {}, rule.title),
            rule.body && el("span", { class: "muted" }, rule.body),
          ),
        ),
      ),
    );
  }

  function storeView() {
    if (!data.rewards.length) return el("p", { class: "muted" }, "אין פרסים כרגע.");
    return el(
      "div",
      { class: "tile-grid" },
      ...data.rewards.map((reward) => {
        const affordable = data.balance >= reward.cost;
        return el(
          "button",
          {
            class: affordable ? "reward-tile" : "reward-tile locked",
            onclick: () => redeem(reward),
          },
          visualNode(reward, "reward-visual"),
          el("span", { class: "card-label" }, reward.title),
          el("span", { class: "reward-cost" }, `⭐ ${reward.cost}`),
        );
      }),
    );
  }

  async function redeem(reward) {
    if (data.balance < reward.cost) {
      return toast("אין מספיק אסימונים");
    }
    if (!confirm(`לממש "${reward.title}" תמורת ${reward.cost} אסימונים?`)) return;
    try {
      const res = await api.post("/tokens/redeem", {
        child_id: childId,
        reward_id: reward.id,
      });
      data.balance = res.balance;
      mount(view());
      toast("הבקשה נשלחה למטפל ✓");
    } catch (e) {
      if (e instanceof ApiError && e.code === "insufficient_tokens") toast("אין מספיק אסימונים");
      else toast("לא ניתן לממש כרגע", "error");
    }
  }

  mount(view());
}
