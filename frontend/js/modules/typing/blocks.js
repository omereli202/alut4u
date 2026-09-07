// The note block model + the one safe read-only renderer.
//
// A note is an array of { t, s } blocks: t is "h1" | "h2" | "p" (literally the
// three toolbar styles), s is a plain string. NEVER HTML — `el()` appends string
// children as text nodes, so nothing here ever reaches the HTML parser. Do not
// introduce innerHTML or el()'s `html:` attribute anywhere in this module.

import { el } from "../../ui.js";

export const STYLES = [
  { key: "h1", label: "כותרת ראשית", short: "כותרת" },
  { key: "h2", label: "כותרת משנה", short: "משנה" },
  { key: "p", label: "טקסט רגיל", short: "רגיל" },
];

const KEYS = new Set(STYLES.map((s) => s.key));
const MAX_BLOCKS = 200;
const MAX_BLOCK_CHARS = 2000;

// A blank note is a single empty paragraph — the child opens straight into a
// writing surface, not a form.
export function normalizeBlocks(raw) {
  const out = [];
  for (const b of Array.isArray(raw) ? raw : []) {
    const t = KEYS.has(b?.t) ? b.t : "p";
    const s = typeof b?.s === "string" ? b.s.slice(0, MAX_BLOCK_CHARS) : "";
    out.push({ t, s });
    if (out.length >= MAX_BLOCKS) break;
  }
  return out.length ? out : [{ t: "p", s: "" }];
}

// Heading LEVELS are demoted — the page <h1> is the navBar title. Visual size
// comes from the .note-h1 / .note-h2 classes, so semantics and look stay
// independent.
export function blockTag(t) {
  return t === "h1" ? "h2" : t === "h2" ? "h3" : "p";
}

export function blocksToPlainText(blocks) {
  return normalizeBlocks(blocks)
    .map((b) => b.s)
    .join("\n")
    .trim();
}

export function renderBlocksReadOnly(blocks) {
  const frag = document.createDocumentFragment();
  for (const b of normalizeBlocks(blocks)) {
    frag.append(el(blockTag(b.t), { class: `note-blk-ro note-${b.t}` }, b.s || " "));
  }
  return frag;
}
