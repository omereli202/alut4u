// Pure painting model — no DOM, no network. The painting is:
//   { v:1, page:{kind,symbol_id?,sig?,sv?}, strokes:[{c,w,e,p:[x,y,...]}], fills:[{r,c}] }
// Coordinates are page-normalised 0..1, quantised to 3 decimals. `p` is a FLAT
// alternating x,y array (half the bytes of {x,y} objects).

import { isColour, DEFAULT_COLOUR } from "./palette.js";

export const MAX_STROKES = 400;
export const MAX_POINTS_PER_STROKE = 1000;
export const MAX_TOTAL_POINTS = 60_000;
export const MAX_FILLS = 300;

export function newPaintingId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function emptyModel(page = { kind: "blank" }) {
  return { v: 1, page: normalizePage(page), strokes: [], fills: [] };
}

function normalizePage(page) {
  if (!page || page.kind !== "symbol" || !page.symbol_id) return { kind: "blank" };
  const out = { kind: "symbol", symbol_id: String(page.symbol_id) };
  if (page.sig) out.sig = String(page.sig).slice(0, 16);
  if (page.sv) out.sv = String(page.sv).slice(0, 32);
  return out;
}

// Accept a server / draft object and return a clean model, dropping anything
// that doesn't validate (a stale asset, a bad colour). Never throws.
export function normalizeModel(raw) {
  const page = normalizePage(raw?.page);
  const strokes = [];
  for (const s of Array.isArray(raw?.strokes) ? raw.strokes : []) {
    if (strokes.length >= MAX_STROKES) break;
    const p = (Array.isArray(s?.p) ? s.p : []).map(clamp01);
    if (p.length < 4 || p.length % 2) continue;
    strokes.push({
      c: /^#[0-9a-f]{6}$/.test(s?.c) ? s.c : "#000000",
      w: typeof s?.w === "number" && s.w > 0 ? Math.min(s.w, 0.2) : 0.028,
      e: s?.e === 1 ? 1 : 0,
      p: p.slice(0, MAX_POINTS_PER_STROKE * 2),
    });
  }
  const fills = [];
  for (const f of Array.isArray(raw?.fills) ? raw.fills : []) {
    if (fills.length >= MAX_FILLS) break;
    if (/^r[0-9a-z]{1,14}$/.test(f?.r) && /^#[0-9a-f]{6}$/.test(f?.c)) {
      fills.push({ r: f.r, c: f.c });
    }
  }
  return { v: 1, page, strokes, fills };
}

const q3 = (n) => Math.round(n * 1000) / 1000;
const clamp01 = (n) => Math.min(1.05, Math.max(-0.05, q3(Number(n) || 0)));

// --- ops -> model -----------------------------------------------------
// The editor keeps an ordered op stack; strokes/fills are derived from it at
// save time so the two never drift.
//   op = { k:"stroke", stroke } | { k:"fill", region, colour, prev }

export function opsToModel(ops, page, title = "") {
  const strokes = [];
  const fillMap = new Map();
  for (const op of ops) {
    if (op.k === "stroke") {
      if (strokes.length < MAX_STROKES) strokes.push(op.stroke);
    } else if (op.k === "fill") {
      if (op.colour == null) fillMap.delete(op.region);
      else fillMap.set(op.region, op.colour);
    }
  }
  const fills = [...fillMap.entries()]
    .slice(0, MAX_FILLS)
    .map(([r, c]) => ({ r, c }));
  return { v: 1, page: normalizePage(page), title: String(title).slice(0, 80), strokes, fills };
}

// --- point thinning --------------------------------------------------

// Ramer-Douglas-Peucker on a flat [x,y,...] array. eps in normalised units.
export function simplify(pts, eps = 0.002) {
  if (pts.length <= 4) return pts.slice();
  const n = pts.length / 2;
  const keep = new Uint8Array(n);
  keep[0] = keep[n - 1] = 1;
  const stack = [[0, n - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let maxD = 0;
    let idx = -1;
    const ax = pts[a * 2];
    const ay = pts[a * 2 + 1];
    const bx = pts[b * 2];
    const by = pts[b * 2 + 1];
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy || 1e-9;
    for (let i = a + 1; i < b; i++) {
      const px = pts[i * 2];
      const py = pts[i * 2 + 1];
      const t = ((px - ax) * dx + (py - ay) * dy) / len2;
      const cx = ax + t * dx;
      const cy = ay + t * dy;
      const d = (px - cx) ** 2 + (py - cy) ** 2;
      if (d > maxD) {
        maxD = d;
        idx = i;
      }
    }
    if (idx !== -1 && Math.sqrt(maxD) > eps) {
      keep[idx] = 1;
      stack.push([a, idx], [idx, b]);
    }
  }
  const out = [];
  for (let i = 0; i < n; i++) {
    if (keep[i]) out.push(q3(pts[i * 2]), q3(pts[i * 2 + 1]));
  }
  return out.length >= 4 ? out : pts.slice();
}

export function quantize(pts) {
  return pts.map(q3);
}

// FNV-1a 32-bit -> base36. Used for region keys and the page signature.
export function fnv1a32(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h.toString(36);
}

export function totalPoints(strokes) {
  return strokes.reduce((n, s) => n + s.p.length / 2, 0);
}

export { isColour, DEFAULT_COLOUR };
