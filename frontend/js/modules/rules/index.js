// User Mode: "כללים ואסימונים" — token balance, behavior rule cards, reward store.

import { api, ApiError } from "../../api.js";
import { el, emptyState, errText, icon, mount, navBar, toast } from "../../ui.js";
import { confirmDialog } from "../../dialog.js";
import { renderPinpad } from "../../views/pinpad.js";
import {
  audioUrlFor,
  loadRulesModule,
  playExplanation,
  prefetch,
  todayISO,
  visualNode,
} from "./data.js";

export async function renderRules({ childId, childName, onExit, onHome }) {
  let data;
  try {
    data = await loadRulesModule(childId);
  } catch {
    return mount(emptyState({ title: "לא ניתן לטעון.", onBack: onExit }));
  }

  let tab = "rules";
  let reading = false;
  let speakingIdx = -1;

  // Rules, then the closing bonus line (when the caregiver set one). Passed as
  // one sequence to the read-aloud button.
  function readAloudItems() {
    const items = data.rules.map((rule, i) => ({ ...rule, __idx: i }));
    if (data.settings.daily_bonus > 0 && data.settings.bonus_tts_asset_id) {
      items.push({ tts_asset_id: data.settings.bonus_tts_asset_id, __idx: data.rules.length });
    }
    return items;
  }

  async function readAll() {
    if (reading) return;
    reading = true;
    for (const item of readAloudItems()) {
      const url = audioUrlFor(item);
      speakingIdx = item.__idx;
      mount(view());
      if (url) {
        await new Promise((resolve) => {
          const a = new Audio(url);
          a.onended = a.onerror = resolve;
          a.play().catch(resolve);
        });
      }
      if (!reading) break;
    }
    reading = false;
    speakingIdx = -1;
    mount(view());
  }

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
          if (reading) reading = false;
          tab = key;
          mount(view());
        },
      },
      label,
    );
  }

  function rulesView() {
    if (!data.rules.length) return emptyState({ iconName: "inbox", title: "אין כללים כרגע." });
    const bonusOn = data.settings.daily_bonus > 0 && data.settings.bonus_text;
    return el(
      "div",
      { class: "rules-list" },
      el(
        "button",
        { class: "sb-btn speak", onclick: reading ? () => (reading = false) : readAll },
        reading ? icon("stop_circle") : icon("play_arrow"),
        reading ? " עצור" : " הקראת הכללים",
      ),
      ...data.rules.map((rule, i) =>
        el(
          "button",
          {
            class: speakingIdx === i ? "rule-card speaking" : "rule-card",
            onclick: () => playExplanation(rule),
          },
          visualNode(rule),
          el(
            "div",
            { class: "rule-text" },
            el("strong", {}, rule.title),
            rule.body && el("span", { class: "muted" }, rule.body),
          ),
        ),
      ),
      bonusOn &&
        el(
          "div",
          {
            class:
              speakingIdx === data.rules.length ? "rules-bonus speaking" : "rules-bonus",
          },
          el("span", { class: "rules-bonus-text" }, icon("star", { size: 24 }), data.settings.bonus_text),
          data.settings.bonus_granted_today
            ? el(
                "span",
                { class: "rules-bonus-done" },
                icon("check_circle", { size: 20 }),
                "הבונוס ניתן היום",
              )
            : el(
                "button",
                { class: "rules-bonus-claim", onclick: claimBonus },
                icon("check", { size: 20 }),
                "שמרת על הכללים",
              ),
        ),
    );
  }

  // The caregiver grants the bonus from the child's own page: tap → PIN screen
  // (same one as "מצב מטפל") → award → drop elevation. We never touch
  // session.state, so the child is never routed to the dashboard.
  function claimBonus() {
    renderPinpad({
      title: "כניסה למצב מטפל",
      hint: "הזינו את קוד המטפל כדי להעניק את הבונוס",
      onCancel: () => mount(view()),
      onSubmit: async (pin) => {
        try {
          await api.post("/auth/pin", { pin });
        } catch (e) {
          throw errText(e); // wrong / locked — stays on the PIN screen
        }
        // PIN accepted — from here always leave the pad and report via toast.
        let msg = "הבונוס ניתן ✓";
        let kind;
        try {
          const res = await api.post("/tokens/rules/bonus", {
            child_id: childId,
            on: todayISO(),
          });
          data.balance = res.balance;
        } catch (e) {
          if (e instanceof ApiError && e.code === "bonus_already_granted") {
            msg = "הבונוס כבר ניתן היום";
          } else {
            msg = errText(e);
            kind = "error";
          }
        } finally {
          await api.del("/auth/pin/elevation").catch(() => {});
          data.settings = await api
            .get(`/tokens/settings?child_id=${encodeURIComponent(childId)}&on=${todayISO()}`)
            .catch(() => data.settings);
        }
        mount(view());
        toast(msg, kind);
      },
    });
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

  prefetch([
    ...data.rules,
    ...(data.settings.bonus_tts_asset_id
      ? [{ tts_asset_id: data.settings.bonus_tts_asset_id }]
      : []),
  ]);
  mount(view());
}
