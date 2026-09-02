// Calming & sensory zone (User Mode). Three calm activities; nothing autoplays.

import { el, mount, navBar } from "../../ui.js";
import { renderBreathing } from "./breathing.js";
import { renderMemory } from "./memory.js";
import { renderSounds } from "./sounds.js";

const TABS = [
  ["sounds", "צלילים", renderSounds],
  ["breathing", "נשימה", renderBreathing],
  ["memory", "זיכרון", renderMemory],
];

export function renderCalming({ childName, onExit, onHome }) {
  let tab = "sounds";
  let cleanup = null;
  const host = el("div", { class: "calm-host" });

  function show(key) {
    cleanup?.();
    tab = key;
    const entry = TABS.find((t) => t[0] === key);
    cleanup = entry[2](host) || null;
    paintTabs();
  }

  function paintTabs() {
    tabsHost.replaceChildren(
      ...TABS.map(([key, label]) =>
        el(
          "button",
          { class: tab === key ? "cat-tab active" : "cat-tab", onclick: () => show(key) },
          label,
        ),
      ),
    );
  }

  const tabsHost = el("div", { class: "cat-tabs" });

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
      { class: "calming", "data-mode": "user" },
      navBar({ onBack: leave, onHome: goHome, title: "פינת רוגע" }),
      tabsHost,
      host,
    ),
  );
  show("sounds");
}
