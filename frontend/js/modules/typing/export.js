// Getting a note out of the app: share sheet -> file download fallback, plus
// copy-to-clipboard. All plain text. The BOM ("﻿") is required or Windows
// Notepad / Excel mangle the Hebrew.

import { blocksToPlainText } from "./blocks.js";
import { toast } from "../../ui.js";

export function noteToText(note) {
  const title = (note.title || "").trim();
  const body = blocksToPlainText(note.blocks);
  return title ? `${title}\n\n${body}` : body;
}

function safeName(note) {
  const base = (note.title || "פתק").trim().replace(/[\\/:*?"<>|]+/g, " ").slice(0, 60);
  return `${base || "פתק"}.txt`;
}

function download(text, filename) {
  const blob = new Blob(["﻿" + text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function shareNote(note) {
  const text = noteToText(note);
  const filename = safeName(note);
  try {
    const file = new File(["﻿" + text], filename, { type: "text/plain" });
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], title: note.title || "פתק" });
      return;
    }
  } catch {
    /* user cancelled the share sheet, or it's unsupported — fall through */
  }
  download(text, filename);
}

export function downloadNote(note) {
  download(noteToText(note), safeName(note));
}

export async function copyNote(note) {
  try {
    await navigator.clipboard.writeText(noteToText(note));
    toast("הועתק");
  } catch {
    toast("לא ניתן להעתיק", "error");
  }
}
