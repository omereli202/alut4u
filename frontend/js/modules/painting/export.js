// Share / download a painting as a PNG. Rasterised client-side, on demand,
// NEVER uploaded (CLAUDE.md rule 4 + the vector-JSON storage decision).
// Mirrors typing/export.js.

import { rasterize } from "./render.js";

function safeName(title) {
  const base = (title || "ציור").replace(/[\\/:*?"<>|]+/g, "").trim().slice(0, 40) || "ציור";
  return `${base}.png`;
}

export async function sharePainting(model, title) {
  const blob = await rasterize(model, 1024);
  if (!blob) return;
  const file = new File([blob], safeName(title), { type: "image/png" });
  try {
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], title: title || "ציור" });
      return;
    }
  } catch {
    /* user cancelled or unsupported — fall through to download */
  }
  downloadBlob(blob, file.name);
}

export async function downloadPainting(model, title) {
  const blob = await rasterize(model, 1024);
  if (blob) downloadBlob(blob, safeName(title));
}

function downloadBlob(blob, name) {
  // A download anchor is not img-src — a blob: href is fine here.
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function printPainting(model, title) {
  const blob = await rasterize(model, 1400);
  if (!blob) return;
  const url = URL.createObjectURL(blob);
  const w = window.open("", "_blank");
  if (!w) {
    URL.revokeObjectURL(url);
    return;
  }
  w.document.write(
    `<title>${(title || "ציור").replace(/[<>&]/g, "")}</title>` +
      `<style>body{margin:0}img{width:100%}</style>` +
      `<img src="${url}" onload="window.print()">`,
  );
  w.document.close();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
