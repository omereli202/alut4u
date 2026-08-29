// User Mode: "קריאה וכתיבה" — graded reading + writing practice, with a live
// token counter (correct answers award tokens).

import { api } from "../../api.js";
import { el, mount } from "../../ui.js";
import { renderReading } from "./reading.js";
import { renderWriting } from "./writing.js";

export async function renderLearning({ childId, childName, onExit }) {
  let balance = 0;
  try {
    balance = (await api.get(`/tokens/balance?child_id=${childId}`)).balance;
  } catch {
    /* tokens module may be off; counter just stays hidden */
  }

  let tab = "reading";
  let cleanup = null;
  const host = el("div", { class: "learn-host" });
  const badge = el("div", { class: "token-badge" }, `⭐ ${balance}`);

  function setBalance(n) {
    balance = n;
    badge.textContent = `⭐ ${balance}`;
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

  const tabsHost = el("div", { class: "cat-tabs" });
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

  mount(
    el(
      "section",
      { class: "learning", "data-mode": "user" },
      el(
        "div",
        { class: "aac-topbar" },
        el(
          "button",
          { class: "lock-btn", "aria-label": "יציאה", onclick: () => { cleanup?.(); onExit(); } },
          "✕",
        ),
        el("h1", { class: "aac-title" }, `קריאה וכתיבה — ${childName || ""}`),
        badge,
      ),
      tabsHost,
      host,
    ),
  );
  show("reading");
}
