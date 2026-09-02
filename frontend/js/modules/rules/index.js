// User Mode: "כללים ואסימונים" — token balance, behavior rule cards, reward store.

import { api, ApiError } from "../../api.js";
import { el, emptyState, icon, mount, navBar, toast } from "../../ui.js";
import { confirmDialog } from "../../dialog.js";
import { loadRulesModule, playExplanation, visualNode } from "./data.js";

export async function renderRules({ childId, childName, onExit, onHome }) {
  let data;
  try {
    data = await loadRulesModule(childId);
  } catch {
    return mount(emptyState({ title: "לא ניתן לטעון.", onBack: onExit }));
  }

  let tab = "rules";

  function view() {
    return el(
      "section",
      { class: "rules-screen", "data-mode": "user" },
      navBar({
        onBack: onExit,
        onHome: onHome ?? onExit,
        title: childName || "הכללים שלי",
        extra: el(
          "div",
          { class: "token-badge", "aria-label": `${data.balance} אסימונים` },
          icon("star", { size: 22 }),
          String(data.balance),
        ),
      }),
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
    if (!data.rules.length) return emptyState({ iconName: "inbox", title: "אין כללים כרגע." });
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
    if (!data.rewards.length) return emptyState({ iconName: "toll", title: "אין פרסים כרגע." });
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
          el("span", { class: "reward-cost" }, icon("star", { size: 18 }), String(reward.cost)),
        );
      }),
    );
  }

  async function redeem(reward) {
    if (data.balance < reward.cost) {
      return toast("אין מספיק אסימונים");
    }
    const ok = await confirmDialog({
      title: "מימוש פרס",
      body: `לממש "${reward.title}" תמורת ${reward.cost} אסימונים?`,
      confirmLabel: "מימוש",
      mode: "user",
    });
    if (!ok) return;
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
