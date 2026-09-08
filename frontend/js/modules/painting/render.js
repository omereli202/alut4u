// Pure replay of a painting model. Zero event code, zero module state — reused
// by the live surface, the caregiver gallery thumbnails and the PNG exporter.

import { loadPage } from "./pages.js";

// Draw a stroke list onto a 2D context sized `px` x `px`. Coordinates are
// normalised 0..1. Eraser strokes (e:1) punch holes with destination-out —
// which only removes canvas pixels, never the SVG layers under/over it.
export function drawStrokes(ctx, strokes, px) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const s of strokes) {
    if (s.p.length < 4) continue;
    ctx.globalCompositeOperation = s.e ? "destination-out" : "source-over";
    ctx.strokeStyle = s.e ? "#000000" : s.c;
    ctx.lineWidth = Math.max(1, s.w * px);
    ctx.beginPath();
    ctx.moveTo(s.p[0] * px, s.p[1] * px);
    for (let i = 2; i < s.p.length; i += 2) ctx.lineTo(s.p[i] * px, s.p[i + 1] * px);
    ctx.stroke();
  }
  ctx.restore();
}

// Apply a fills array ([{r,c}]) to a live regions <svg> (its shapes carry
// data-region). Unknown keys are ignored — that is the graceful-degradation
// path when a regenerated symbol no longer matches the saved `sig`.
export function applyFills(regionsSvg, fills) {
  const byKey = new Map((fills || []).map((f) => [f.r, f.c]));
  for (const shape of regionsSvg.querySelectorAll("[data-region]")) {
    const c = byKey.get(shape.getAttribute("data-region"));
    shape.setAttribute("style", `fill:${c || "#ffffff"};stroke:none`);
  }
}

function svgToDataUrl(svgEl, px) {
  svgEl.setAttribute("width", px);
  svgEl.setAttribute("height", px);
  const xml = new XMLSerializer().serializeToString(svgEl);
  // data:, not blob: — the CSP is `img-src 'self' data:` with no blob:.
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
}

function drawImage(ctx, url, px) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, px, px);
      resolve();
    };
    img.onerror = reject;
    img.src = url;
  });
}

// Flatten a model to a PNG Blob. Never uploaded — share / download / print only.
// Layer order is identical to the screen: white regions (with fills) → ink →
// black outline on top.
export async function rasterize(model, px = 1024) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff"; // paper — safe here, this canvas never erases
  ctx.fillRect(0, 0, px, px);

  if (model.page?.kind === "symbol" && model.page.symbol_id) {
    const page = await loadPage(model.page.symbol_id);
    if (page && page.regionsSvg) {
      const regions = page.regionsSvg.cloneNode(true);
      applyFills(regions, model.fills);
      try {
        await drawImage(ctx, svgToDataUrl(regions, px), px);
      } catch {
        /* region layer failed — carry on with strokes + outline */
      }
      drawStrokes(ctx, model.strokes, px);
      try {
        await drawImage(ctx, svgToDataUrl(page.linesSvg.cloneNode(true), px), px);
      } catch {
        /* outline failed — strokes still show */
      }
      return toBlob(canvas);
    }
  }
  drawStrokes(ctx, model.strokes, px);
  return toBlob(canvas);
}

function toBlob(canvas) {
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

// A small flattened preview as a data: URL (an <img> src — CSP forbids blob:
// there). Fixed pixel size, DPR ignored: slightly soft is fine for a tile.
export async function thumbnailDataUrl(model, px = 200) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, px, px);
  if (model.page?.kind === "symbol" && model.page.symbol_id) {
    const page = await loadPage(model.page.symbol_id);
    if (page && page.regionsSvg) {
      const regions = page.regionsSvg.cloneNode(true);
      applyFills(regions, model.fills);
      try {
        await drawImage(ctx, svgToDataUrl(regions, px), px);
        drawStrokes(ctx, model.strokes, px);
        await drawImage(ctx, svgToDataUrl(page.linesSvg.cloneNode(true), px), px);
      } catch {
        /* partial render is acceptable for a thumbnail */
      }
      return canvas.toDataURL("image/png");
    }
  }
  drawStrokes(ctx, model.strokes, px);
  return canvas.toDataURL("image/png");
}
