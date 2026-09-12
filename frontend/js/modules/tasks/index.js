// "המשימות שלי" module entry (User Mode). A checklist the child ticks off; the
// caregiver curates it and releases a token reward with their PIN once every
// task due today is done.

import { api, ApiError } from "../../api.js";
import { pinGate } from "../../pin-gate.js";
import { celebration, el, emptyState, errText, icon, mount, navBar, toast } from "../../ui.js";
import { audioUrl, loadDay, todayISO, toggleTask, visualNode } from "./data.js";

export async function renderMyTasks({ childId, childName, onExit, onHome }) {
  const dateISO = todayISO();
  let data = { items: [], reward_tokens: 0, reward_claimed: false, all_done: false };

  async function load() {
    try {
      data = await loadDay(childId, dateISO);
    } catch {
      toast("לא ניתן לטעון את המשימות", "error");
    }
  }

  const host = el("div", { class: "tasks-host" });
  // Live "n/total" pill in the nav bar — same slot/pattern as the tokens
  // count in modules/learning/index.js (a mutable text node updated in
  // place, rather than rebuilding the whole nav bar on every tick).
  const countText = el("span", {}, "0/0");
  const badge = el(
    "div",
    { class: "count-badge", "aria-label": "0 מתוך 0 משימות הושלמו" },
    icon("check_circle", { size: 22 }),
    countText,
  );
  function setCount() {
    const done = data.items.filter((t) => t.is_done).length;
    const total = data.items.length;
    countText.textContent = `${done}/${total}`;
    badge.setAttribute("aria-label", `${done} מתוך ${total} משימות הושלמו`);
    // No [hidden] reset in this codebase's CSS, so toggle display directly
    // rather than the hidden attribute (which .count-badge's own
    // display:inline-flex would otherwise just override).
    badge.style.display = total === 0 ? "none" : "";
  }
  const screen = el(
    "section",
    { class: "tasks", "data-mode": "user" },
    navBar({
      onBack: onExit,
      onHome: onHome ?? onExit,
      title: childName || "המשימות שלי",
      extra: badge,
    }),
    host,
  );

  let reading = false;

  async function readAll() {
    if (reading) return;
    reading = true;
    showList();
    for (const task of data.items) {
      const url = audioUrl(task.tts_asset_id);
      if (!url) continue;
      await new Promise((resolve) => {
        const a = new Audio(url);
        a.onended = a.onerror = resolve;
        a.play().catch(resolve);
      });
      if (!reading) break;
    }
    reading = false;
    showList();
  }

  function row(task) {
    return el(
      "div",
      { class: task.is_done ? "task-row done" : "task-row" },
      el("input", {
        type: "checkbox",
        checked: task.is_done,
        "aria-label": `סימון "${task.title}" כבוצע`,
        onchange: (e) => {
          toggleTask(task, e.target.checked, dateISO);
          data.all_done = data.items.length > 0 && data.items.every((t) => t.is_done);
          showList();
        },
      }),
      visualNode(task, "task-row-visual"),
      el("span", { class: "task-row-title" }, task.title),
    );
  }

  function rewardBlock() {
    if (!data.all_done) return null;
    if (data.reward_claimed) {
      return el(
        "div",
        { class: "task-reward" },
        celebration({ title: "כל הכבוד! סיימת את כל המשימות", body: "הפרס להיום כבר ניתן ✓" }),
      );
    }
    return el(
      "div",
      { class: "task-reward" },
      celebration({ title: "כל הכבוד! סיימת את כל המשימות" }),
      el(
        "button",
        { class: "btn-primary task-claim", onclick: showClaim },
        icon("star", { size: 18 }),
        ` קרא למטפל לקבלת הפרס (+${data.reward_tokens})`,
      ),
    );
  }

  function showList() {
    setCount();
    host.replaceChildren(
      el(
        "div",
        { class: "task-list" },
        el(
          "div",
          { class: "task-list-head" },
          el(
            "button",
            { class: "sb-btn speak", onclick: reading ? () => (reading = false) : readAll },
            reading ? icon("stop_circle") : icon("play_arrow"),
            reading ? " עצור" : " הקראת המשימות",
          ),
        ),
        data.items.length
          ? el("div", { class: "task-rows" }, ...data.items.map(row))
          : emptyState({ iconName: "check_circle", title: "אין משימות כרגע." }),
        rewardBlock(),
      ),
    );
  }

  // Reward release — the caregiver is handed the tablet, enters their PIN, and
  // the privileged claim runs. Elevation is always dropped afterwards and the
  // session is never switched, so the child stays in User Mode.
  function showClaim() {
    reading = false;
    pinGate(host, {
      hint: "מטפל, הזינו קוד כדי לשחרר את הפרס:",
      onCancel: showList,
      onElevated: async () => {
        let msg = "האסימונים ניתנו ✓";
        let kind;
        try {
          await api.post("/tasks/claim", { child_id: childId, the_date: dateISO });
        } catch (e) {
          msg =
            e instanceof ApiError && e.code === "reward_already_granted"
              ? "הפרס להיום כבר ניתן"
              : errText(e);
          kind = "error";
        } finally {
          await api.del("/auth/pin/elevation").catch(() => {});
        }
        await load();
        showList();
        toast(msg, kind);
      },
    });
  }

  mount(screen);
  await load();
  showList();
}
