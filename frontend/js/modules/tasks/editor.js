// "המשימות שלי" editor (Caregiver Mode): curate the task list, attach a symbol
// to each, set how many tokens finishing the whole list is worth.

import { api } from "../../api.js";
import { el, errText, icon, mount, toast, withBusy } from "../../ui.js";
import { createVisualPicker } from "../../visual-picker.js";

const RECURRENCE_HE = { daily: "כל יום", once: "חד-פעמית" };

export async function renderTasksEditor({ childId, childName, onExit }) {
  let items = [];
  let rewardTokens = 1;

  async function load() {
    try {
      const r = await api.get(`/tasks/items?child_id=${encodeURIComponent(childId)}`);
      items = r.items;
      rewardTokens = r.reward_tokens;
    } catch (e) {
      items = [];
      toast(errText(e), "error");
    }
    render();
  }

  function itemRow(item) {
    const i = items.findIndex((x) => x.id === item.id);
    return el(
      "div",
      { class: "editor-card-row" },
      el(
        "span",
        { class: "editor-card-label" },
        `${item.title} · ${RECURRENCE_HE[item.recurrence]}`,
      ),
      el(
        "div",
        { class: "editor-card-actions" },
        el(
          "button",
          { class: "sb-btn", "aria-label": "הזז למעלה", disabled: i === 0, onclick: () => move(i, -1) },
          icon("chevron_right"),
        ),
        el(
          "button",
          {
            class: "sb-btn",
            "aria-label": "הזז למטה",
            disabled: i === items.length - 1,
            onclick: () => move(i, 1),
          },
          icon("chevron_left"),
        ),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              try {
                await api.del(`/tasks/items/${item.id}`);
                load();
              } catch (err) {
                toast(errText(err), "error");
              }
            },
          },
          "מחק",
        ),
      ),
    );
  }

  async function move(i, delta) {
    const order = items.map((x) => x.id);
    [order[i], order[i + delta]] = [order[i + delta], order[i]];
    try {
      await api.put("/tasks/items/order", { child_id: childId, order });
      await load();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  function itemForm() {
    const visualState = { symbol_id: null, icon_asset_id: null };
    return el(
      "form",
      { class: "sched-item-form", onsubmit: (e) => addItem(e, visualState) },
      el("input", { name: "title", type: "text", required: true, maxlength: 80, placeholder: "שם המשימה" }),
      el(
        "select",
        { name: "recurrence", "aria-label": "סוג המשימה" },
        el("option", { value: "daily" }, "כל יום"),
        el("option", { value: "once" }, "חד-פעמית"),
      ),
      createVisualPicker({ childId, state: visualState, kind: "schedule_icon", onChange: null }),
      el("button", { type: "submit", class: "btn-primary" }, "הוסף משימה"),
      el("p", { class: "err", role: "alert" }),
    );
  }

  async function addItem(e, visualState) {
    e.preventDefault();
    const f = new FormData(e.target);
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/tasks/items", {
          child_id: childId,
          title: f.get("title").trim(),
          recurrence: f.get("recurrence"),
          symbol_id: visualState.symbol_id,
          icon_asset_id: visualState.icon_asset_id,
          sort_order: items.length,
        });
        load();
      } catch (err) {
        e.target.querySelector(".err").textContent = errText(err);
      }
    });
  }

  function rewardForm() {
    return el(
      "form",
      { class: "sched-item-form", onsubmit: saveReward },
      el("label", { for: "task-reward" }, "אסימונים על סיום כל המשימות: "),
      el("input", {
        id: "task-reward",
        name: "reward_tokens",
        type: "number",
        min: 0,
        max: 20,
        value: String(rewardTokens),
        required: true,
      }),
      el("button", { type: "submit", class: "btn-link" }, "שמור"),
      el("p", { class: "muted" }, "הפרס ניתן פעם ביום, באישור קוד המטפל."),
    );
  }

  async function saveReward(e) {
    e.preventDefault();
    const n = Number(new FormData(e.target).get("reward_tokens"));
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        const r = await api.put("/tasks/settings", { child_id: childId, reward_tokens: n });
        rewardTokens = r.reward_tokens;
        toast("נשמר");
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  function render() {
    mount(
      el(
        "section",
        { class: "tasks-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `עריכת המשימות שלי — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        el(
          "div",
          { class: "card" },
          el("h3", {}, "המשימות"),
          items.length
            ? el("div", { class: "editor-card-list" }, ...items.map(itemRow))
            : el("p", { class: "muted" }, "אין עדיין משימות. הוסיפו למטה."),
          itemForm(),
        ),
        el("div", { class: "card" }, el("h3", {}, "פרס"), rewardForm()),
      ),
    );
  }

  await load();
}
