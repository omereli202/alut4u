// Turn a bundled Mulberry symbol into a colouring page.
//
// Verified across all 755 bundled symbols: a <path> (or circle/rect/…) is an
// OUTLINE if its resolved `stroke` is not "none" (or it has no fill at all →
// default black); a REGION if it has no stroke and a real colour fill; an
// invisible bounding rect if `fill:none` with no stroke. ~315 files carry a
// <style> block with class-based fills, and a class rule beats a presentation
// attribute — so fills must be RESOLVED and written inline, and the <style>
// itself dropped (it is document-global once inlined).
//
// No innerHTML, no el()'s html: — DOMParser gives an inert document, we
// importNode individual shape nodes into two fresh <svg> roots.

import { symbolUrl } from "../../ui.js";
import { fnv1a32 } from "./model.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const SHAPES = new Set(["path", "circle", "ellipse", "rect", "polygon", "polyline", "line"]);
const BANNED = new Set([
  "script", "foreignobject", "image", "use", "a",
  "animate", "animatetransform", "animatemotion", "set", "style",
]);
const GEO_ATTRS = new Set([
  "d", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "points", "x1", "y1", "x2", "y2",
]);

// The curated default gallery. All verified present on disk and colourable
// (>=1 outline, 2..14 regions, no <text>/<image>). Kept as a client constant —
// bundled asset ids, no reason to round-trip.
export const CURATED = [
  "cat", "dog", "rabbit", "horse", "cow", "duck", "owl", "bear", "elephant",
  "fish", "frog", "butterfly", "snail", "turtle",
  "car", "bus", "train", "boat", "rocket",
  "tree", "flower", "mushroom", "rainbow", "star",
  "teddy-bear", "balloon", "heart", "crown", "kite", "drum",
];

const _cache = new Map();

const PAINT_ATTRS = ["fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"];

function resolveStyle(node, inherited, css) {
  const cur = { ...inherited };
  const cls = node.getAttribute("class");
  if (cls) for (const c of cls.split(/\s+/)) if (css[c]) Object.assign(cur, css[c]);
  for (const k of PAINT_ATTRS) {
    const v = node.getAttribute(k);
    if (v != null) cur[k] = v.trim();
  }
  const style = node.getAttribute("style");
  if (style) {
    for (const decl of style.split(";")) {
      const i = decl.indexOf(":");
      if (i > 0) cur[decl.slice(0, i).trim()] = decl.slice(i + 1).trim();
    }
  }
  return cur;
}

function parseCss(doc) {
  const css = {};
  for (const styleEl of doc.querySelectorAll("style")) {
    const text = styleEl.textContent || "";
    for (const m of text.matchAll(/\.([A-Za-z0-9_-]+)\s*\{([^}]*)\}/g)) {
      const decl = {};
      for (const part of m[2].split(";")) {
        const i = part.indexOf(":");
        if (i > 0) decl[part.slice(0, i).trim()] = part.slice(i + 1).trim();
      }
      css[m[1]] = decl;
    }
  }
  return css;
}

function geometryOf(node) {
  const bits = [];
  for (const a of node.attributes) {
    if (GEO_ATTRS.has(a.name)) bits.push(`${a.name}=${a.value}`);
  }
  return bits.sort().join(",");
}

function makeSvg(viewBox) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", viewBox);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  return svg;
}

// Parse + split. Returns null on any failure (caller falls back to a blank page).
export async function loadPage(symbolId) {
  if (_cache.has(symbolId)) return _cache.get(symbolId);
  let out = null;
  try {
    out = await _load(symbolId);
  } catch {
    out = null;
  }
  _cache.set(symbolId, out);
  return out;
}

async function _load(symbolId) {
  const res = await fetch(symbolUrl(symbolId), { credentials: "same-origin" });
  if (!res.ok) return null;
  const doc = new DOMParser().parseFromString(await res.text(), "image/svg+xml");
  if (doc.querySelector("parsererror")) return null;
  const root = doc.documentElement;
  if (root.namespaceURI !== SVG_NS || root.localName !== "svg") return null;
  if (doc.querySelector("text, image, foreignObject")) {
    return { eligible: false };
  }

  const viewBox = root.getAttribute("viewBox") || "0 0 850.394 850.394";
  const css = parseCss(doc);
  const regionsSvg = makeSvg(viewBox);
  const linesSvg = makeSvg(viewBox);
  const keys = [];
  const seen = new Map();

  const walk = (node, inherited) => {
    if (node.nodeType !== 1) return;
    const tag = node.localName.toLowerCase();
    if (BANNED.has(tag)) return;
    const resolved = resolveStyle(node, inherited, css);

    if (SHAPES.has(tag)) {
      const stroke = (resolved.stroke || "none").toLowerCase();
      const fill = resolved.fill;
      const isOutline =
        (stroke && stroke !== "none") || fill == null || fill === undefined;
      const isRegion = !isOutline && fill && fill.toLowerCase() !== "none";

      if (isRegion) {
        const copy = document.importNode(node, false);
        stripUnsafe(copy);
        let key = "r" + fnv1a32(`${tag}|${geometryOf(node)}|${fill}`);
        const n = (seen.get(key) || 0) + 1;
        seen.set(key, n);
        if (n > 1) key += `-${n}`;
        copy.setAttribute("data-region", key);
        copy.setAttribute("style", "fill:#ffffff;stroke:none");
        for (const a of PAINT_ATTRS) copy.removeAttribute(a);
        copy.removeAttribute("class");
        regionsSvg.append(copy);
        keys.push(key);
      } else if (isOutline) {
        const copy = document.importNode(node, false);
        stripUnsafe(copy);
        let decls;
        if (!stroke || stroke === "none") {
          // No stroke -> it was a bare (usually black) fill; keep it as a fill.
          decls = [`fill:${sanitizePaint(fill) || "#000000"}`, "stroke:none"];
        } else {
          decls = ["fill:none", `stroke:${sanitizePaint(stroke) || "#000000"}`];
          const sw = resolved["stroke-width"];
          decls.push(`stroke-width:${sw && /^[\d.]+$/.test(sw) ? sw : "12"}`);
          decls.push("stroke-linecap:round", "stroke-linejoin:round");
        }
        copy.setAttribute("style", decls.join(";"));
        for (const a of PAINT_ATTRS) copy.removeAttribute(a);
        copy.removeAttribute("class");
        linesSvg.append(copy);
      }
      return; // shapes have no shape children
    }

    for (const child of node.childNodes) walk(child, resolved);
  };
  for (const child of root.childNodes) walk(child, {});

  const eligible = keys.length >= 2 && linesSvg.childElementCount >= 1;
  const sig = fnv1a32(keys.join("|")).slice(0, 16);
  return { viewBox, regionsSvg, linesSvg, keys, sig, eligible };
}

function stripUnsafe(node) {
  for (const a of [...node.attributes]) {
    const n = a.name.toLowerCase();
    if (n.startsWith("on") || n === "href" || n === "xlink:href") node.removeAttribute(a.name);
  }
}

// Only allow a hex / rgb() / named-ish token through to a style string.
function sanitizePaint(v) {
  if (!v) return null;
  const t = v.trim().toLowerCase();
  if (/^#[0-9a-f]{3,8}$/.test(t)) return t;
  if (/^rgb\([\d\s,.%]+\)$/.test(t)) return t;
  if (/^[a-z]{3,20}$/.test(t)) return t;
  return null;
}

export async function isColourable(symbolId) {
  const p = await loadPage(symbolId);
  return !!(p && p.eligible);
}
