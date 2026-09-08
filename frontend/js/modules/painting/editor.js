// The drawing screen: a toolbar + the shared surface. Renders into `host`
// (host.replaceChildren — never mount(), which would blow away the canvas) and
// returns a cleanup function.

import { el, icon } from "../../ui.js";
import { destructiveDialog } from "../../dialog.js";
import { COLOURS, BRUSH_SIZES, DEFAULT_COLOUR } from "./palette.js";
import { saveDraft, savePainting } from "./data.js";

const DRAFT_MS = 800; // kv draft only — a ~200KB structuredClone is coarser than a keystroke
const COMMIT_MS = 3000; // coalesced outbox POST + rev bump

const TOOL_LABEL = { brush: "מברשת", bucket: "צבע", eraser: "מחק" };

export function renderPaintEditor(host, { childId, painting, surface, onBack, onSaved }) {
  let rev = painting.rev || 1;
  let colour = DEFAULT_COLOUR;
  let tool = "brush";
  let brushIdx = 1;
  let dirty = false;
  let draftT = null;
  let commitT = null;
  let alive = true;

  surface.setColour(colour);
  surface.setBrush(BRUSH_SIZES[brushIdx].w);
  surface.setTool(tool);

  const snapshot = () => ({
    child_id: childId,
    painting_id: painting.painting_id,
    rev,
    ...surface.toModel(painting.title || ""),
  });

  function persistDraft() {
    if (!alive) return;
    saveDraft(snapshot()).catch(() => {});
  }

  async function commit({ final = false } = {}) {
    clearTimeout(draftT);
    clearTimeout(commitT);
    if (!alive || !dirty) {
      if (final) onSaved?.();
      return;
    }
    dirty = false;
    rev += 1;
    await savePainting(snapshot()).catch(() => {});
    if (final) onSaved?.();
  }

  function markDirty(flag) {
    if (flag === "full") {
      status.textContent = "הדף מלא — אפשר להתחיל דף חדש";
      return;
    }
    dirty = true;
    status.textContent = "נשמר במכשיר";
    clearTimeout(draftT);
    clearTimeout(commitT);
    draftT = setTimeout(persistDraft, DRAFT_MS);
    commitT = setTimeout(() => commit(), COMMIT_MS);
    undoBtn.disabled = !surface.canUndo();
  }
  surface.setOnChange(markDirty);

  // --- toolbar pieces ----------------------------------------------

  const status = el("span", { class: "paint-status", role: "status" }, "");

  const swatches = COLOURS.map((c) =>
    el("button", {
      class: "paint-swatch",
      style: `--sw:${c}`,
      "aria-label": `צבע`,
      "aria-pressed": c === colour ? "true" : "false",
      onclick: () => {
        colour = c;
        surface.setColour(c);
        paintSwatchState();
      },
    }),
  );
  function paintSwatchState() {
    COLOURS.forEach((c, i) => swatches[i].setAttribute("aria-pressed", c === colour ? "true" : "false"));
  }
  paintSwatchState();

  const toolBtns = ["brush", "bucket", "eraser"]
    .filter((t) => t !== "bucket" || painting.page?.kind === "symbol")
    .map((t) =>
      el(
        "button",
        {
          class: "paint-tool",
          "aria-pressed": t === tool ? "true" : "false",
          onclick: () => {
            tool = t;
            surface.setTool(t);
            toolBtns.forEach((b) => b.setAttribute("aria-pressed", b.dataset.tool === t ? "true" : "false"));
          },
          dataset: { tool: t },
        },
        TOOL_LABEL[t],
      ),
    );

  const sizeBtns = BRUSH_SIZES.map((b, i) =>
    el(
      "button",
      {
        class: "paint-size",
        "aria-pressed": i === brushIdx ? "true" : "false",
        "aria-label": `מברשת ${b.label}`,
        onclick: () => {
          brushIdx = i;
          surface.setBrush(b.w);
          sizeBtns.forEach((x, j) => x.setAttribute("aria-pressed", j === i ? "true" : "false"));
        },
      },
      el("span", { class: "paint-size-dot", style: `--d:${Math.round(6 + i * 8)}px` }),
    ),
  );

  const undoBtn = el(
    "button",
    { class: "paint-act", disabled: true, onclick: () => { surface.undo(); markDirty(); } },
    icon("undo"),
    el("span", {}, "בטל"),
  );

  const clearBtn = el(
    "button",
    {
      class: "paint-act",
      onclick: async () => {
        if (await destructiveDialog({
          title: "לנקות את הדף?",
          body: "כל הציור יימחק.",
          confirmLabel: "נקה",
          mode: "user",
        })) {
          surface.clear();
          markDirty();
        }
      },
    },
    icon("delete"),
    el("span", {}, "דף חדש"),
  );

  const backBtn = el(
    "button",
    {
      class: "btn-primary paint-done",
      onclick: async () => {
        await commit({ final: true });
        teardown();
        onBack();
      },
    },
    "שמרתי",
  );

  host.replaceChildren(
    el(
      "div",
      { class: "paint-editor" },
      el(
        "div",
        { class: "paint-toolbar" },
        el("div", { class: "paint-tools" }, ...toolBtns),
        el("div", { class: "paint-sizes" }, ...sizeBtns),
        el("div", { class: "paint-acts" }, undoBtn, clearBtn),
      ),
      el("div", { class: "paint-swatches" }, ...swatches),
      surface.node,
      el("div", { class: "paint-footer" }, status, backBtn),
    ),
  );
  undoBtn.disabled = !surface.canUndo(); // a resumed painting starts with ops

  function teardown() {
    if (!alive) return;
    clearTimeout(draftT);
    clearTimeout(commitT);
    surface.setOnChange(null);
    // last-chance durable save before we lose the editor
    if (dirty) {
      dirty = false;
      rev += 1;
      savePainting(snapshot()).catch(() => {});
    }
    alive = false;
  }

  // page-level draft safety — the app can be killed mid-painting
  const onHide = () => {
    if (document.visibilityState === "hidden") persistDraft();
  };
  document.addEventListener("visibilitychange", onHide);
  window.addEventListener("pagehide", onHide);

  return () => {
    document.removeEventListener("visibilitychange", onHide);
    window.removeEventListener("pagehide", onHide);
    teardown();
  };
}
