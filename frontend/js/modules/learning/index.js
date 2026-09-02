// User Mode: "קריאה וכתיבה" — graded reading + writing practice, with a live
// token counter (correct answers award tokens).

import { api } from "../../api.js";
import { el, icon, mount, navBar } from "../../ui.js";
import { renderReading } from "./reading.js";
import { renderWriting } from "./writing.js";

export async function renderLearning({ childId, childName, onExit, onHome }) {
  let balance = 0;
  try {
    balance = (await api.get(`/tokens/balance?child_id=${childId}`)).balance;
  } catch {
    /* tokens module may be off; counter just stays hidden */
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

  function show(key) {
    cleanup?.();
    tab = key;
    paintTabs();
    cleanup =
      key === "reading"
        ? renderReading(host, { childId, onBalance: setBalance })
        : renderWriting(host, { childId, onBalance: setBalance });
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
        "כתיבה",
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
        title: `תרגול קריאה וכתיבה — ${childName || ""}`,
        extra: badge,
      }),
      tabsHost,
      host,
    ),
  );
  show("reading");
}
