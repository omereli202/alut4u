// User Mode: "קריאה והקלדה" — level-based reading + typing practice. Tokens come
// from milestones (every 3 completed tasks in a level), released by the
// caregiver's PIN — handled inside each tab.

import { api } from "../../api.js";
import { el, icon, mount, navBar } from "../../ui.js";
import { renderReading } from "./reading.js";
import { renderWriting } from "./writing.js";

export async function renderLearning({ childId, childName, onExit, onHome }) {
  let balance = 0;
  try {
    balance = (await api.get(`/tokens/balance?child_id=${childId}`)).balance;
  } catch {
    /* tokens module may be off; counter just stays at 0 */
  }

  let tab = "reading";
  let cleanup = null;
  const host = el("div", { class: "learn-host" });
  const balanceText = el("span", {}, String(balance));
  const badge = el(
    "div",
    { class: "token-badge", "aria-label": `${balance} אסימונים` },
    icon("star", { size: 22 }),
    balanceText,
  );

  function setBalance(n) {
    balance = n;
    balanceText.textContent = String(balance);
    badge.setAttribute("aria-label", `${balance} אסימונים`);
  }

  // Live "n/total" pill for whichever tab is open — reading and writing each
  // report their own per-level progress (see reading.js/writing.js's
  // onProgress), and switching tabs re-renders that tab from scratch, so the
  // pill naturally follows whichever one is currently showing.
  const countText = el("span", {}, "0/0");
  const countBadge = el(
    "div",
    { class: "count-badge", "aria-label": "0 מתוך 0 הושלמו" },
    icon("check_circle", { size: 22 }),
    countText,
  );
  function setProgress({ completed, total }) {
    countText.textContent = `${completed}/${total}`;
    countBadge.setAttribute("aria-label", `${completed} מתוך ${total} הושלמו`);
  }

  function show(key) {
    cleanup?.();
    tab = key;
    paintTabs();
    cleanup =
      key === "reading"
        ? renderReading(host, { childId, onBalance: setBalance, onProgress: setProgress })
        : renderWriting(host, { childId, onBalance: setBalance, onProgress: setProgress });
  }

  const tabsHost = el("div", { class: "cat-tabs segmented" });
  function paintTabs() {
    tabsHost.replaceChildren(
      el(
        "button",
        { class: tab === "reading" ? "cat-tab active" : "cat-tab", onclick: () => show("reading") },
        "קריאה",
      ),
      el(
        "button",
        { class: tab === "writing" ? "cat-tab active" : "cat-tab", onclick: () => show("writing") },
        "הקלדה",
      ),
    );
  }

  function leave() {
    cleanup?.();
    onExit();
  }
  function goHome() {
    cleanup?.();
    (onHome ?? onExit)();
  }

  mount(
    el(
      "section",
      { class: "learning", "data-mode": "user" },
      navBar({
        onBack: leave,
        onHome: goHome,
        title: `קריאה והקלדה — ${childName || ""}`,
        extra: [countBadge, badge],
      }),
      tabsHost,
      host,
    ),
  );
  show("reading");
}
