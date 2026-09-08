// User Mode: the child's saved paintings, "ציור חדש", and the page chooser.
// Renders into `host` (host.replaceChildren) and returns a cleanup function.

import { el, emptyState, icon, symbolUrl } from "../../ui.js";
import { CURATED } from "./pages.js";
import { listPaintings, loadExtraPages } from "./data.js";

export function renderGallery(host, { childId, onOpen, onNew }) {
  let alive = true;

  async function showList() {
    host.replaceChildren(el("p", { class: "paint-status" }, "טוען…"));
    let items = [];
    try {
      items = await listPaintings(childId);
    } catch {
      /* offline / error — show the empty state */
    }
    if (!alive) return;
    host.replaceChildren(
      el(
        "div",
        { class: "paint-gallery" },
        el(
          "button",
          { class: "btn-primary paint-new", onclick: showChooser },
          icon("add"),
          " ציור חדש",
        ),
        items.length
          ? el(
              "div",
              { class: "paint-grid" },
              ...items.map((p) =>
                el(
                  "button",
                  { class: "paint-thumb-card", onclick: () => onOpen(p.id) },
                  thumb(p),
                  el("span", { class: "paint-thumb-title" }, p.title || "ציור"),
                  p.unsynced && el("span", { class: "paint-thumb-badge" }, "נשמר במכשיר"),
                ),
              ),
            )
          : emptyState({ iconName: "edit", title: "עדיין אין ציורים.", body: "אפשר להתחיל לצייר." }),
      ),
    );
  }

  function thumb(p) {
    if (p.page?.kind === "symbol" && p.page.symbol_id) {
      return el("img", { class: "paint-thumb-img", src: symbolUrl(p.page.symbol_id), alt: "" });
    }
    return el("span", { class: "paint-thumb-blank" }, icon("edit", { size: 32 }));
  }

  async function showChooser() {
    host.replaceChildren(el("p", { class: "paint-status" }, "טוען…"));
    let extra = [];
    try {
      extra = await loadExtraPages(childId);
    } catch {
      /* ignore */
    }
    if (!alive) return;
    const ids = [...new Set([...CURATED, ...extra])];
    host.replaceChildren(
      el(
        "div",
        { class: "paint-chooser" },
        el(
          "div",
          { class: "paint-chooser-head" },
          el("button", { class: "btn-link", onclick: showList }, "חזרה"),
          el("h2", {}, "מה נצייר?"),
        ),
        el(
          "div",
          { class: "paint-page-grid" },
          el(
            "button",
            { class: "paint-page-card", onclick: () => onNew({ kind: "blank" }) },
            el("span", { class: "paint-thumb-blank" }, icon("edit", { size: 40 })),
            el("span", {}, "דף חלק"),
          ),
          ...ids.map((sid) =>
            el(
              "button",
              {
                class: "paint-page-card",
                onclick: () => onNew({ kind: "symbol", symbol_id: sid }),
              },
              el("img", { class: "paint-page-img", src: symbolUrl(sid), alt: "" }),
            ),
          ),
        ),
      ),
    );
  }

  showList();

  return () => {
    alive = false;
  };
}
