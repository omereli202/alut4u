// Caregiver Mode: manage behavior rules, award tokens, manage the reward store,
// and resolve pending redemption requests.

import { api, ApiError } from "../../api.js";
import { confirmDialog } from "../../dialog.js";
import { el, errText, mount, toast, withBusy } from "../../ui.js";
import { createVisualPicker } from "../../visual-picker.js";
import { todayISO } from "./data.js";

const QUICK_AWARDS = [1, 2, 5];

export async function renderRulesEditor({ childId, childName, onExit }) {
  let state;

  async function load() {
    const id = encodeURIComponent(childId);
    const [rules, bal, rewards, queue, settings] = await Promise.all([
      api.get(`/tokens/rules?child_id=${id}`).then((r) => r.rules),
      api.get(`/tokens/balance?child_id=${id}`),
      api.get(`/tokens/rewards?child_id=${id}&all=1`).then((r) => r.rewards),
      api.get("/tokens/queue").then((r) => r.pending).catch(() => []),
      api.get(`/tokens/settings?child_id=${id}&on=${todayISO()}`),
    ]);
    state = { rules, balance: bal.balance, transactions: bal.transactions, rewards, queue, settings };
    render();
  }

  function render() {
    const myQueue = state.queue.filter((r) => r.child_id === childId);
    mount(
      el(
        "section",
        { class: "rules-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `עריכת כללים — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),

        // Tokens
        el(
          "div",
          { class: "card" },
          el("h3", {}, `אסימונים: ${state.balance} ⭐`),
          el(
            "form",
            { class: "award-form", onsubmit: award },
            ...QUICK_AWARDS.map((n) =>
              el("button", { type: "button", class: "sb-btn", onclick: (e) => quickAward(n, e.target) }, `+${n}`),
            ),
            el("input", { name: "amount", type: "number", placeholder: "כמות", min: -100, max: 100 }),
            el("input", { name: "reason", type: "text", placeholder: "סיבה (רשות)", maxlength: 120 }),
            el("button", { type: "submit", class: "btn-link" }, "הענקה"),
          ),

          // Daily bonus — the number the child sees at the bottom of the rules
          // list. Granting it is a normal award behind a confirm dialog.
          bonusBlock(),

          state.transactions.length
            ? el(
                "details",
                { class: "tx-history" },
                el("summary", {}, `היסטוריית אסימונים (${state.transactions.length})`),
                el(
                  "ul",
                  { class: "tx-list" },
                  ...state.transactions
                    .slice(0, 30)
                    .map((t) =>
                      el(
                        "li",
                        {},
                        el("span", { class: t.delta >= 0 ? "tx-pos" : "tx-neg" }, `${t.delta >= 0 ? "+" : ""}${t.delta}`),
                        " ",
                        t.reason || t.kind,
                      ),
                    ),
                ),
              )
            : null,
        ),

        // Approval queue
        el(
          "div",
          { class: "card" },
          el("h3", {}, `בקשות פרס ממתינות ${myQueue.length ? `(${myQueue.length})` : ""}`),
          myQueue.length
            ? el(
                "div",
                { class: "editor-card-list" },
                ...myQueue.map((r) =>
                  el(
                    "div",
                    { class: "editor-card-row" },
                    el("span", { class: "editor-card-label" }, `${r.title} — ${r.cost} ⭐`),
                    el(
                      "div",
                      { class: "editor-card-actions" },
                      el("button", { class: "btn-link", onclick: () => resolve(r.id, "approve") }, "אישור"),
                      el("button", { class: "btn-link danger", onclick: () => resolve(r.id, "reject") }, "דחייה (החזר אסימונים)"),
                    ),
                  ),
                ),
              )
            : el("p", { class: "muted" }, "אין בקשות."),
        ),

        // Rules
        el(
          "div",
          { class: "card" },
          el("h3", {}, "כללי התנהגות"),
          el("div", { class: "editor-card-list" }, ...state.rules.map(ruleRow)),
          ruleForm(),
        ),

        // Rewards
        el(
          "div",
          { class: "card" },
          el("h3", {}, "חנות הפרסים"),
          el("div", { class: "editor-card-list" }, ...state.rewards.map(rewardRow)),
          rewardForm(),
        ),
      ),
    );
  }

  // --- tokens -------------------------------------------------------

  async function quickAward(n, btn) {
    await withBusy(btn, async () => {
      try {
        const res = await api.post("/tokens/award", { child_id: childId, amount: n });
        state.balance = res.balance;
        await load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  async function award(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const amount = Number(f.get("amount"));
    if (!amount) return;
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/tokens/award", {
          child_id: childId,
          amount,
          reason: f.get("reason").trim() || null,
        });
        load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  async function resolve(id, action) {
    try {
      await api.post(`/tokens/redemptions/${id}/${action}`);
      load();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  // --- daily bonus ------------------------------------------------

  function bonusBlock() {
    const n = state.settings.daily_bonus;
    return el(
      "div",
      { class: "bonus-block" },
      el(
        "form",
        { class: "award-form", onsubmit: saveBonus },
        el("label", {}, "בונוס יומי על שמירה על הכללים:"),
        el("input", { name: "daily_bonus", type: "number", min: 0, max: 100, value: String(n) }),
        el("button", { type: "submit", class: "btn-link" }, "שמירה"),
      ),
      n > 0
        ? state.settings.bonus_granted_today
          ? el("p", { class: "muted" }, "הבונוס ניתן היום ✓")
          : el(
              "button",
              { type: "button", class: "btn-primary", onclick: (e) => grantBonus(n, e.target) },
              `⭐ הענקת בונוס יומי (+${n})`,
            )
        : el("p", { class: "muted" }, "0 — השורה לא מוצגת לילד."),
    );
  }

  async function saveBonus(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    const daily_bonus = Number(f.get("daily_bonus"));
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.put("/tokens/settings", { child_id: childId, daily_bonus });
        load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  async function grantBonus(n, btn) {
    const ok = await confirmDialog({
      title: "בונוס יומי",
      body: `להעניק ל${childName} ${n} אסימונים על שמירה על הכללים?`,
      confirmLabel: "הענקה",
    });
    if (!ok) return;
    await withBusy(btn, async () => {
      try {
        await api.post("/tokens/rules/bonus", { child_id: childId, on: todayISO() });
        load();
      } catch (err) {
        if (err instanceof ApiError && err.code === "bonus_already_granted") {
          toast("הבונוס כבר ניתן היום");
          load();
        } else {
          toast(errText(err), "error");
        }
      }
    });
  }

  // --- rules -------------------------------------------------------

  function ruleRow(rule) {
    return el(
      "div",
      { class: "editor-card-row" },
      el("span", { class: "editor-card-label" }, rule.title),
      el(
        "button",
        {
          class: "btn-link danger",
          onclick: async () => {
            await api.del(`/tokens/rules/${rule.id}`);
            load();
          },
        },
        "מחק",
      ),
    );
  }

  function ruleForm() {
    const visualState = { symbol_id: null, icon_asset_id: null };
    return el(
      "form",
      { class: "sched-item-form", onsubmit: (e) => addRule(e, visualState) },
      el("input", { name: "title", type: "text", required: true, maxlength: 60, placeholder: "שם הכלל" }),
      el("input", { name: "body", type: "text", maxlength: 300, placeholder: "הסבר (יוקרא בקול)" }),
      createVisualPicker({ childId, state: visualState, kind: "schedule_icon", onChange: null }),
      el("button", { type: "submit", class: "btn-primary" }, "הוסף כלל"),
      el("p", { class: "err", role: "alert" }),
    );
  }

  async function addRule(e, visualState) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/tokens/rules", {
          child_id: childId,
          title: f.get("title").trim(),
          body: f.get("body").trim() || null,
          symbol_id: visualState.symbol_id,
          icon_asset_id: visualState.icon_asset_id,
          sort_order: state.rules.length,
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  // --- rewards ----------------------------------------------------

  function rewardRow(reward) {
    return el(
      "div",
      { class: reward.is_active ? "editor-card-row" : "editor-card-row inactive" },
      el("span", { class: "editor-card-label" }, `${reward.title} — ${reward.cost} ⭐`),
      el(
        "div",
        { class: "editor-card-actions" },
        el(
          "button",
          {
            class: "btn-link",
            onclick: async () => {
              await api.patch(`/tokens/rewards/${reward.id}`, { is_active: !reward.is_active });
              load();
            },
          },
          reward.is_active ? "השבתה" : "הפעלה",
        ),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              await api.del(`/tokens/rewards/${reward.id}`);
              load();
            },
          },
          "מחק",
        ),
      ),
    );
  }

  function rewardForm() {
    const visualState = { symbol_id: null, icon_asset_id: null };
    return el(
      "form",
      { class: "sched-item-form", onsubmit: (e) => addReward(e, visualState) },
      el("input", { name: "title", type: "text", required: true, maxlength: 60, placeholder: "שם הפרס" }),
      el("input", { name: "cost", type: "number", required: true, min: 1, max: 1000, placeholder: "מחיר באסימונים" }),
      createVisualPicker({ childId, state: visualState, kind: "schedule_icon", onChange: null }),
      el("button", { type: "submit", class: "btn-primary" }, "הוסף פרס"),
      el("p", { class: "err", role: "alert" }),
    );
  }

  async function addReward(e, visualState) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/tokens/rewards", {
          child_id: childId,
          title: f.get("title").trim(),
          cost: Number(f.get("cost")),
          symbol_id: visualState.symbol_id,
          icon_asset_id: visualState.icon_asset_id,
          sort_order: state.rewards.length,
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  await load();
}
