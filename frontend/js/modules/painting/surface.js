// The interactive drawing surface for "בוא נצייר".
//
// THE INVARIANT: the canvas bitmap is derived state; the ops stack is the
// state. A resize / rotate / undo is just "re-measure, replay". No bitmap is
// ever preserved or copied.
//
// Layer stack (bottom → top):
//   svg.paint-regions   real DOM, shapes hit-testable  (bucket taps land here)
//   canvas.paint-ink    pointer-events:none, TRANSPARENT (never filled white —
//                       the eraser's destination-out would punch through to the
//                       app background; paper is CSS background:#fff)
//   svg.paint-lines     pointer-events:none — outline always on top so a child
//                       scribbling can never destroy the line art.

import { el } from "../../ui.js";
import { loadPage } from "./pages.js";
import { drawStrokes } from "./render.js";
import { simplify, MAX_STROKES, MAX_POINTS_PER_STROKE } from "./model.js";
import { DEFAULT_COLOUR, BRUSH_SIZES } from "./palette.js";

const GATE = 0.004; // ignore a move closer than this (normalised) to the last kept point
const DPR_CAP = 2;

export function createSurface({ onChange } = {}) {
  const regions = svgLayer("paint-regions");
  const canvas = el("canvas", { class: "paint-ink" });
  const lines = svgLayer("paint-lines");
  const node = el(
    "div",
    { class: "paint-surface", role: "img", "aria-label": "משטח ציור" },
    regions,
    canvas,
    lines,
  );

  const ctx = canvas.getContext("2d"); // WITH alpha — regions below must show through
  let changeCb = onChange || null;
  let page = { kind: "blank" }; // {kind, symbol_id, sig, sv}
  let loadedPage = null; // { regionsSvg, linesSvg, keys, sig } or null
  let ops = []; // { k:"stroke", stroke } | { k:"fill", region, colour, prev }
  let tool = "brush";
  let colour = DEFAULT_COLOUR;
  let brushW = BRUSH_SIZES[1].w;

  // per-stroke state
  let activeId = null;
  let raw = []; // captured points for the in-progress stroke, normalised
  let lastKept = null;
  let downRegion = null;
  let travel = 0;
  let pendingResize = false;

  // --- sizing / replay ------------------------------------------------

  function px() {
    return canvas.width; // square backing store
  }

  function fullRedraw() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawStrokes(
      ctx,
      ops.filter((o) => o.k === "stroke").map((o) => o.stroke),
      px(),
    );
  }

  const ro = new ResizeObserver((entries) => {
    const b = entries[0].contentBoxSize?.[0] ?? entries[0].contentRect;
    const w = Math.round(b.inlineSize ?? b.width);
    const h = Math.round(b.blockSize ?? b.height);
    if (!w || !h) return; // detached / display:none — never set width = 0
    if (activeId !== null) {
      pendingResize = true;
      return;
    }
    applyResize(Math.min(w, h));
  });

  function applyResize(cssSide) {
    const dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);
    const side = Math.round(cssSide * dpr);
    if (side === canvas.width) return; // RO fires on every layout
    canvas.width = canvas.height = side; // clears the bitmap + resets ctx state
    fullRedraw();
  }

  // --- pointer routing ----------------------------------------------

  function toNorm(e) {
    const r = node.getBoundingClientRect();
    const s = Math.min(r.width, r.height) || 1;
    // surface is square + centred; account for letterboxing
    const ox = (r.width - s) / 2;
    const oy = (r.height - s) / 2;
    return [(e.clientX - r.left - ox) / s, (e.clientY - r.top - oy) / s];
  }

  function regionAt(target) {
    return target?.closest?.("[data-region]") || null;
  }

  function currentFill(shape) {
    const m = /fill:\s*(#[0-9a-f]{6})/i.exec(shape.getAttribute("style") || "");
    const c = m && m[1].toLowerCase();
    return c && c !== "#ffffff" ? c : null;
  }

  function setRegionFill(shape, c) {
    shape.setAttribute("style", `fill:${c || "#ffffff"};stroke:none`);
  }

  function pushOp(op) {
    ops.push(op);
    changeCb?.();
  }

  function fillRegion(shape, c) {
    if (!shape) return;
    const key = shape.getAttribute("data-region");
    pushOp({ k: "fill", region: key, colour: c, prev: currentFill(shape) });
    setRegionFill(shape, c);
  }

  function onDown(e) {
    if (!e.isPrimary || activeId !== null) return; // palm rejection
    if (ops.filter((o) => o.k === "stroke").length >= MAX_STROKES && tool !== "bucket") {
      changeCb?.("full");
      return;
    }
    activeId = e.pointerId;
    downRegion = regionAt(e.target); // BEFORE capture
    travel = 0;
    try {
      node.setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    e.preventDefault();

    if (tool === "bucket") {
      fillRegion(downRegion, colour);
      activeId = null;
      return;
    }
    raw = [];
    lastKept = null;
    addPoint(toNorm(e));
    drawLiveReset();
  }

  function onMove(e) {
    if (e.pointerId !== activeId) return;
    const evs = e.getCoalescedEvents?.() ?? [e];
    for (const ev of evs) addPoint(toNorm(ev));
    drawLiveSegment();
  }

  function onUp(e) {
    if (e.pointerId !== activeId) return;
    finishStroke(e);
  }

  function onCancel(e) {
    if (e.pointerId !== activeId) return;
    // iOS fires this on a system gesture. Finalize, never discard — the child
    // watched those pixels appear.
    finishStroke(e);
  }

  function finishStroke(e) {
    try {
      node.releasePointerCapture(activeId);
    } catch {
      /* ignore */
    }
    const wasEraser = tool === "eraser";

    if (wasEraser && travel < GATE * 2 && downRegion && currentFill(downRegion)) {
      // tap on a filled region with the eraser = reset that fill
      pushOp({
        k: "fill",
        region: downRegion.getAttribute("data-region"),
        colour: null,
        prev: currentFill(downRegion),
      });
      setRegionFill(downRegion, null);
    }

    if (raw.length >= 4) {
      const p = simplify(raw, 0.002).slice(0, MAX_POINTS_PER_STROKE * 2);
      pushOp({ k: "stroke", stroke: { c: colour, w: brushW, e: wasEraser ? 1 : 0, p } });
    }
    raw = [];
    lastKept = null;
    downRegion = null;
    activeId = null;
    fullRedraw(); // fold the live layer back into a clean replay
    if (pendingResize) {
      pendingResize = false;
      const r = node.getBoundingClientRect();
      applyResize(Math.min(r.width, r.height));
    }
  }

  function addPoint([x, y]) {
    if (lastKept) {
      const dx = x - lastKept[0];
      const dy = y - lastKept[1];
      travel += Math.hypot(dx, dy);
      if (dx * dx + dy * dy < GATE * GATE) return;
    }
    if (raw.length >= MAX_POINTS_PER_STROKE * 2) {
      // finalize this run and seamlessly start another at the same point
      const p = simplify(raw, 0.002);
      pushOp({ k: "stroke", stroke: { c: colour, w: brushW, e: tool === "eraser" ? 1 : 0, p } });
      raw = raw.slice(-2);
    }
    raw.push(x, y);
    lastKept = [x, y];
  }

  // --- live drawing (incremental; full redraw only on undo/clear/resize/load)

  function drawLiveReset() {
    ctx.save();
    ctx.lineCap = ctx.lineJoin = "round";
    ctx.globalCompositeOperation = tool === "eraser" ? "destination-out" : "source-over";
    ctx.strokeStyle = tool === "eraser" ? "#000" : colour;
    ctx.lineWidth = Math.max(1, brushW * px());
    ctx.restore();
  }

  function drawLiveSegment() {
    if (raw.length < 4) return;
    ctx.save();
    ctx.lineCap = ctx.lineJoin = "round";
    ctx.globalCompositeOperation = tool === "eraser" ? "destination-out" : "source-over";
    ctx.strokeStyle = tool === "eraser" ? "#000" : colour;
    ctx.lineWidth = Math.max(1, brushW * px());
    const n = raw.length;
    ctx.beginPath();
    ctx.moveTo(raw[n - 4] * px(), raw[n - 3] * px());
    ctx.lineTo(raw[n - 2] * px(), raw[n - 1] * px());
    ctx.stroke();
    ctx.restore();
  }

  // --- page ---------------------------------------------------------

  async function setPage(nextPage) {
    page = nextPage && nextPage.kind === "symbol" ? { ...nextPage } : { kind: "blank" };
    regions.replaceChildren();
    lines.replaceChildren();
    loadedPage = null;
    if (page.kind === "symbol") {
      const p = await loadPage(page.symbol_id);
      if (p && p.regionsSvg) {
        loadedPage = p;
        page.sig = p.sig;
        for (const shape of p.regionsSvg.cloneNode(true).childNodes) {
          const c = shape.cloneNode(true);
          c.setAttribute("tabindex", "0");
          c.setAttribute("role", "button");
          c.setAttribute("aria-label", "אזור לצביעה");
          regions.append(c);
        }
        for (const shape of p.linesSvg.cloneNode(true).childNodes) lines.append(shape.cloneNode(true));
        regions.setAttribute("viewBox", p.viewBox);
        lines.setAttribute("viewBox", p.viewBox);
      }
    }
  }

  // --- public API -------------------------------------------------

  function toModel(title = "") {
    const fillMap = new Map();
    const strokes = [];
    for (const op of ops) {
      if (op.k === "stroke") strokes.push(op.stroke);
      else if (op.k === "fill") {
        if (op.colour == null) fillMap.delete(op.region);
        else fillMap.set(op.region, op.colour);
      }
    }
    const pageOut =
      page.kind === "symbol"
        ? { kind: "symbol", symbol_id: page.symbol_id, sig: page.sig, sv: page.sv }
        : { kind: "blank" };
    return {
      v: 1,
      title: String(title).slice(0, 80),
      page: pageOut,
      strokes: strokes.slice(0, MAX_STROKES),
      fills: [...fillMap.entries()].map(([r, c]) => ({ r, c })),
    };
  }

  async function load(model) {
    await setPage(model?.page ?? { kind: "blank" });
    ops = [];
    for (const s of model?.strokes ?? []) ops.push({ k: "stroke", stroke: s });
    // apply saved fills by key; a key the current art no longer has is dropped
    const known = new Set(loadedPage?.keys ?? []);
    for (const f of model?.fills ?? []) {
      if (!known.size || known.has(f.r)) {
        ops.push({ k: "fill", region: f.r, colour: f.c, prev: null });
        const shape = regions.querySelector(`[data-region="${cssEsc(f.r)}"]`);
        if (shape) setRegionFill(shape, f.c);
      }
    }
    fullRedraw();
    changeCb?.();
  }

  function undo() {
    const op = ops.pop();
    if (!op) return;
    if (op.k === "fill") {
      const shape = regions.querySelector(`[data-region="${cssEsc(op.region)}"]`);
      if (shape) setRegionFill(shape, op.prev);
    } else {
      fullRedraw();
    }
    changeCb?.();
  }

  function clear() {
    ops = [];
    for (const shape of regions.querySelectorAll("[data-region]")) setRegionFill(shape, null);
    fullRedraw();
    changeCb?.();
  }

  function destroy() {
    ro.disconnect();
    node.removeEventListener("pointerdown", onDown);
    node.removeEventListener("pointermove", onMove);
    node.removeEventListener("pointerup", onUp);
    node.removeEventListener("pointercancel", onCancel);
    try {
      if (activeId !== null) node.releasePointerCapture(activeId);
    } catch {
      /* ignore */
    }
  }

  node.addEventListener("pointerdown", onDown);
  node.addEventListener("pointermove", onMove);
  node.addEventListener("pointerup", onUp);
  node.addEventListener("pointercancel", onCancel);
  // keyboard fill path for the SVG regions (a11y — canvas drawing stays pointer-only)
  regions.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const shape = regionAt(e.target);
    if (!shape) return;
    e.preventDefault();
    if (tool === "eraser") {
      pushOp({
        k: "fill",
        region: shape.getAttribute("data-region"),
        colour: null,
        prev: currentFill(shape),
      });
      setRegionFill(shape, null);
    } else {
      fillRegion(shape, colour);
    }
  });
  ro.observe(node);

  return {
    node,
    setPage,
    setOnChange: (fn) => {
      changeCb = fn || null;
    },
    setTool: (t) => {
      tool = t;
    },
    setColour: (c) => {
      colour = c;
    },
    setBrush: (w) => {
      brushW = w;
    },
    load,
    undo,
    canUndo: () => ops.length > 0,
    isFull: () => ops.filter((o) => o.k === "stroke").length >= MAX_STROKES,
    clear,
    toModel,
    destroy,
  };
}

function svgLayer(cls) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("class", cls);
  s.setAttribute("viewBox", "0 0 100 100");
  s.setAttribute("preserveAspectRatio", "xMidYMid meet");
  return s;
}

function cssEsc(s) {
  return window.CSS?.escape ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&");
}
