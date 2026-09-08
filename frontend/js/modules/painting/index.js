// User Mode: "בוא נצייר" — the child's saved paintings and the drawing screen.
//
// mount() runs ONCE here and the surface is created ONCE — both must survive
// the gallery <-> editor swap, because mount() replaces all of #main and a
// re-created <canvas> loses its bitmap. The gallery and editor render into a
// stable `host` via host.replaceChildren.

import { el, mount, navBar, toast } from "../../ui.js";
import { createSurface } from "./surface.js";
import { renderGallery } from "./gallery.js";
import { renderPaintEditor } from "./editor.js";
import { emptyModel, newPaintingId } from "./model.js";
import { flushPendingDrafts, getPainting, recallOpen, rememberOpen } from "./data.js";

export async function renderPainting({ childId, childName, onExit, onHome }) {
  const host = el("div", { class: "paint-host" });
  const surface = createSurface();
  let cleanup = null; // gallery or editor cleanup

  async function swap(fn) {
    if (cleanup) {
      await cleanup();
      cleanup = null;
    }
    fn();
  }

  function showGallery() {
    rememberOpen(childId, "").catch(() => {});
    swap(() => {
      cleanup = renderGallery(host, { childId, onOpen: openExisting, onNew: openNew });
    });
  }

  async function openEditor(painting) {
    rememberOpen(childId, painting.painting_id).catch(() => {});
    await surface.load(painting);
    surface.setTool("brush");
    swap(() => {
      cleanup = renderPaintEditor(host, {
        childId,
        painting,
        surface,
        onBack: showGallery,
        onSaved: () => {},
      });
    });
  }

  function openNew(page) {
    openEditor({ ...emptyModel(page), painting_id: newPaintingId(), title: "", rev: 1 });
  }

  async function openExisting(id) {
    const p = await getPainting(childId, id);
    if (!p) {
      toast("לא ניתן לפתוח את הציור", "error");
      return;
    }
    openEditor(p);
  }

  async function leave() {
    if (cleanup) await cleanup();
    surface.destroy();
    onExit();
  }
  async function goHome() {
    if (cleanup) await cleanup();
    surface.destroy();
    (onHome ?? onExit)();
  }

  mount(
    el(
      "section",
      { class: "paint-screen", "data-mode": "user" },
      navBar({ onBack: leave, onHome: goHome, title: `הציורים של ${childName || ""}` }),
      host,
    ),
  );

  flushPendingDrafts(childId).catch(() => {});

  const resumeId = await recallOpen(childId);
  if (resumeId) {
    const p = await getPainting(childId, resumeId);
    if (p) {
      await openEditor(p);
      return;
    }
  }
  showGallery();
}
