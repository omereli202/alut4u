// Caregiver Mode: "עריכת בוא נצייר" — curate the extra colouring pages for this
// child, and browse / share / print / delete the child's saved paintings.
// Calls mount() itself (caregiver-editor pattern).

import { api } from "../../api.js";
import { el, errText, icon, mount, symbolUrl, toast, withBusy } from "../../ui.js";
import { destructiveDialog } from "../../dialog.js";
import { createSymbolPicker } from "../aac/symbol-picker.js";
import { CURATED, isColourable } from "./pages.js";
import { thumbnailDataUrl } from "./render.js";
import { sharePainting, downloadPainting, printPainting } from "./export.js";

export async function renderPaintingViewer({ childId, childName, onExit }) {
  let paintings = [];
  let extraPages = [];

  async function load() {
    try {
      paintings = (
        await api.get(`/painting/paintings?child_id=${encodeURIComponent(childId)}`)
      ).paintings;
    } catch {
      paintings = [];
    }
    try {
      extraPages = (
        await api.get(`/painting/pages?child_id=${encodeURIComponent(childId)}`)
      ).symbol_ids;
    } catch {
      extraPages = [];
    }
    render();
  }

  async function saveExtra(ids) {
    try {
      const r = await api.put("/painting/pages", { child_id: childId, symbol_ids: ids });
      extraPages = r.symbol_ids;
    } catch (e) {
      toast(errText(e), "error");
    }
    render();
  }

  // --- pages card -------------------------------------------------

  function pagesCard() {
    const picker = createSymbolPicker(async (s) => {
      const id = s.id || (s.file_path || "").replace(/\.svg$/, "");
      if (CURATED.includes(id) || extraPages.includes(id)) {
        toast("הדף כבר ברשימה");
        return;
      }
      if (!(await isColourable(id))) {
        toast("הסמל הזה לא מתאים לצביעה", "error");
        return;
      }
      saveExtra([...extraPages, id]);
    });

    return el(
      "div",
      { class: "card" },
      el("h3", {}, "דפי צביעה"),
      el(
        "p",
        { class: "muted" },
        `${CURATED.length} דפים מובנים תמיד זמינים. אפשר להוסיף עוד:`,
      ),
      extraPages.length
        ? el(
            "div",
            { class: "paint-page-chips" },
            ...extraPages.map((id) =>
              el(
                "span",
                { class: "paint-page-chip" },
                el("img", { src: symbolUrl(id), alt: "" }),
                el(
                  "button",
                  {
                    class: "btn-link danger",
                    "aria-label": "הסרה",
                    onclick: () => saveExtra(extraPages.filter((x) => x !== id)),
                  },
                  icon("close"),
                ),
              ),
            ),
          )
        : el("p", { class: "muted" }, "לא הוספת דפים נוספים."),
      picker,
    );
  }

  // --- gallery card ----------------------------------------------

  function galleryCard() {
    const grid = el("div", { class: "paint-viewer-grid" });
    if (!paintings.length) {
      grid.append(el("p", { class: "muted" }, "אין עדיין ציורים."));
      return el("div", { class: "card" }, el("h3", {}, `הציורים של ${childName}`), grid);
    }
    const imgs = [];
    for (const p of paintings) {
      const img = el("img", { class: "paint-viewer-thumb", alt: p.title || "ציור" });
      grid.append(
        el(
          "button",
          { class: "paint-viewer-card", onclick: () => openDetail(p.id) },
          img,
          el("span", {}, p.title || "ציור"),
        ),
      );
      imgs.push([img, p.id]);
    }
    // Render thumbnails one at a time so a big gallery doesn't spawn N parallel
    // canvas rasterizations. Not blocking — the grid is already on screen.
    (async () => {
      for (const [img, id] of imgs) {
        try {
          const model = await api.get(`/painting/paintings/${id}`);
          img.src = await thumbnailDataUrl(model, 220);
        } catch {
          /* leave blank */
        }
      }
    })();
    return el("div", { class: "card" }, el("h3", {}, `הציורים של ${childName}`), grid);
  }

  async function openDetail(id) {
    let model;
    try {
      model = await api.get(`/painting/paintings/${id}`);
    } catch (e) {
      toast(errText(e), "error");
      return;
    }
    const big = el("img", { class: "paint-detail-img", alt: model.title || "ציור" });
    thumbnailDataUrl(model, 900).then((u) => (big.src = u));

    mount(
      el(
        "section",
        { class: "painting-detail", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, model.title || "ציור"),
          el("button", { class: "btn-link", onclick: render }, "חזרה"),
        ),
        el("div", { class: "card" }, big),
        el(
          "div",
          { class: "paint-detail-acts" },
          el(
            "button",
            {
              class: "btn-link",
              onclick: (e) => withBusy(e.currentTarget, () => sharePainting(model, model.title)),
            },
            "שיתוף",
          ),
          el(
            "button",
            {
              class: "btn-link",
              onclick: (e) => withBusy(e.currentTarget, () => downloadPainting(model, model.title)),
            },
            "הורדה",
          ),
          el(
            "button",
            { class: "btn-link", onclick: () => printPainting(model, model.title) },
            "הדפסה",
          ),
          el(
            "button",
            {
              class: "btn-link danger",
              onclick: async () => {
                if (
                  await destructiveDialog({
                    title: "למחוק את הציור?",
                    body: "הפעולה אינה הפיכה.",
                  })
                ) {
                  await api.del(`/painting/paintings/${id}`).catch((e) => toast(errText(e), "error"));
                  await load();
                }
              },
            },
            icon("delete"),
            " מחיקה",
          ),
        ),
      ),
    );
  }

  function render() {
    mount(
      el(
        "section",
        { class: "painting-viewer", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `עריכת בוא נצייר — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        pagesCard(),
        galleryCard(),
      ),
    );
  }

  await load();
}
