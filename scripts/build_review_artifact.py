#!/usr/bin/env python3
"""Build the Mulberry Symbols review page — an Artifact the caregiver/reviewer
uses to approve, edit or reject each candidate Hebrew label before it's
ingested (see scripts/mulberry_manifest.py, scripts/build_symbols.py).

    python scripts/build_review_artifact.py --batch locked
    python scripts/build_review_artifact.py --status pending --limit 300

Writes a single self-contained HTML file. Publish it with the Artifact tool
(capabilities: {"artifact": {}}); to add a later batch, run this again and
republish to the SAME artifact url — the page's own state (previously
approved/edited rows) lives in the artifact's last-published version, so
pass --merge-from to seed on top of a previously-read-back export rather
than the raw manifest, or just re-run against the manifest after Stage 2
has already merged prior decisions back into it.

IMPORTANT — why this isn't built by string-templating from a live DOM:
the artifact runtime's publish() explicitly warns that
document.documentElement.outerHTML carries viewer-session state and
platform-injected scripts and must never be republished. This script
generates the ENTIRE page (including the JS that later reconstructs it
for publish) from one Python string, so the file and the JS's own copy
of its "static shell" are byte-identical by construction — see SKELETON
below, embedded into the JS as a JSON string rather than hand-duplicated.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mulberry_manifest as mm

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_DIR = ROOT / "frontend" / "assets" / "symbols"


def _rows_for_locked(manifest: dict, zf: zipfile.ZipFile) -> list[dict]:
    rows = []
    for sid, e in manifest["entries"].items():
        if not e.get("locked"):
            continue
        svg = (
            zf.read(f"EN-symbols/{e['src']}.svg").decode("utf-8") if e["src"] else None
        )
        placeholder_svg = None
        if e["src"] is None or e.get("scrutiny") == "substitute":
            p = PLACEHOLDER_DIR / f"{e['id']}.svg"
            if p.exists():
                placeholder_svg = p.read_text(encoding="utf-8")
        rows.append(
            {
                "symbol_id": sid,
                "id": e["id"],
                "src": e["src"],
                "category_en": e["category_en"],
                "grammar": e["grammar"],
                "label_he": e["label_he"],
                "keywords_he": e["keywords_he"],
                "status": e["status"],
                "scrutiny": e["scrutiny"],
                "note": e["note"],
                "keep_placeholder": False,
                "svg": svg if svg is not None else placeholder_svg,
                "placeholder_svg": placeholder_svg,
            }
        )
    rows.sort(
        key=lambda r: (
            0 if r["scrutiny"] == "substitute" else (1 if r["src"] is None else 2),
            r["id"],
        )
    )
    return rows


def _rows_for_pending(
    manifest: dict,
    zf: zipfile.ZipFile,
    *,
    status: str,
    limit: int | None,
    category: str | None = None,
    labeled_only: bool = False,
) -> list[dict]:
    rows = []
    for sid, e in sorted(
        manifest["entries"].items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0
    ):
        if e.get("locked") or e["status"] != status:
            continue
        if category is not None and e["category_en"] != category:
            continue
        if labeled_only and not e["label_he"]:
            continue
        svg = zf.read(f"EN-symbols/{e['src']}.svg").decode("utf-8")
        rows.append(
            {
                "symbol_id": sid,
                "id": e["id"],
                "src": e["src"],
                "category_en": e["category_en"],
                "grammar": e["grammar"],
                "label_he": e["label_he"],
                "keywords_he": e["keywords_he"],
                "status": e["status"],
                "scrutiny": e["scrutiny"],
                "note": e["note"],
                "keep_placeholder": False,
                "svg": svg,
                "placeholder_svg": None,
            }
        )
        if limit and len(rows) >= limit:
            break
    return rows


SKELETON = r"""<title>__PAGE_TITLE__</title>
<meta name="description" content="בדיקת ההתאמות בין סמלי Mulberry Symbols למילות לוח התקשורת">
<style>
  :root {
    --bg: #f7f9f9; --surface: #ffffff; --surface-sunken: #eeedf2;
    --text: #2d3436; --text-muted: #636e72;
    --accent: #3a5d8b; --accent-contrast: #ffffff; --accent-soft: #d4e3ff;
    --good: #3e6658; --good-soft: #c0ecda;
    --warn: #e6a23c; --warn-ink: #8a5a00; --warn-soft: #fbedd2;
    --danger: #d66853; --danger-ink: #a63a25; --danger-soft: #f8ddd6;
    --border: #dcdfe6; --border-strong: #b9bfc7; --focus: #4a90e2;
    --font-ui: "Rubik", "Assistant", "Heebo", system-ui, sans-serif;
    --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", monospace;
    --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #1a1d1f; --surface: #232729; --surface-sunken: #2c3133;
      --text: #eef1f2; --text-muted: #9aa4a8;
      --accent: #7fa8d6; --accent-contrast: #12233a; --accent-soft: #274363;
      --good: #7fc9ac; --good-soft: #23423a;
      --warn: #eabb6a; --warn-ink: #f6d698; --warn-soft: #4a3a1c;
      --danger: #e6947f; --danger-ink: #f3c3b6; --danger-soft: #4a2a22;
      --border: #383e41; --border-strong: #4c5457; --focus: #7fa8d6;
    }
  }
  :root[data-theme="dark"] {
    --bg: #1a1d1f; --surface: #232729; --surface-sunken: #2c3133;
    --text: #eef1f2; --text-muted: #9aa4a8;
    --accent: #7fa8d6; --accent-contrast: #12233a; --accent-soft: #274363;
    --good: #7fc9ac; --good-soft: #23423a;
    --warn: #eabb6a; --warn-ink: #f6d698; --warn-soft: #4a3a1c;
    --danger: #e6947f; --danger-ink: #f3c3b6; --danger-soft: #4a2a22;
    --border: #383e41; --border-strong: #4c5457; --focus: #7fa8d6;
  }
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: var(--font-ui); line-height: 1.5; min-height: 100vh; margin: 0; }
  h1, h2, h3 { text-wrap: balance; font-weight: 700; margin: 0; }
  a { color: var(--accent); }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 24px 20px 80px; }
  @media (min-width: 700px) { .wrap { padding-top: 40px; } }
  header.top { display: flex; flex-wrap: wrap; gap: 20px 32px; align-items: flex-start; justify-content: space-between; padding-bottom: 24px; border-bottom: 1px solid var(--border); margin-bottom: 28px; }
  .title-block h1 { font-size: 1.65rem; }
  .title-block p { color: var(--text-muted); margin: 6px 0 0; max-width: 62ch; font-size: 0.95rem; }
  .batch-tag { font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); letter-spacing: 0.02em; margin-top: 8px; display: block; }
  .stats { display: flex; gap: 10px; flex-wrap: wrap; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 10px 16px; min-width: 84px; text-align: center; }
  .stat .n { font-family: var(--font-mono); font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
  .stat .l { font-size: 0.72rem; color: var(--text-muted); margin-top: 2px; }
  .stat.warn .n { color: var(--warn-ink); }
  .stat.good .n { color: var(--good); }
  .toolbar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 20px; position: sticky; top: 0; background: var(--bg); padding: 12px 0; z-index: 5; }
  .toolbar input[type="search"] { flex: 1; min-width: 180px; padding: 10px 14px; border-radius: var(--radius-md); border: 1px solid var(--border-strong); background: var(--surface); color: var(--text); font-family: var(--font-ui); font-size: 0.95rem; }
  .toolbar input[type="search"]:focus-visible, button:focus-visible, input:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  .chip-toggle { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 999px; border: 1px solid var(--border-strong); background: var(--surface); color: var(--text-muted); font-size: 0.85rem; cursor: pointer; user-select: none; font-family: var(--font-ui); }
  .chip-toggle.active { background: var(--warn-soft); border-color: var(--warn); color: var(--warn-ink); font-weight: 500; }
  .btn { font-family: var(--font-ui); font-size: 0.9rem; font-weight: 500; border-radius: var(--radius-md); padding: 10px 18px; border: 1px solid transparent; cursor: pointer; white-space: nowrap; }
  .btn-primary { background: var(--accent); color: var(--accent-contrast); }
  .btn-primary:disabled { opacity: 0.5; cursor: default; }
  .btn-ghost { background: var(--surface); border-color: var(--border-strong); color: var(--text); }
  .sync-status { font-size: 0.82rem; color: var(--text-muted); min-width: 120px; }
  .sync-status.err { color: var(--danger-ink); }
  .sync-status.ok { color: var(--good); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px; display: flex; flex-direction: column; gap: 12px; position: relative; }
  .card.scrutiny { border-inline-start: 4px solid var(--warn); padding-inline-start: 13px; }
  .card.dirty { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .card-head { display: flex; gap: 12px; align-items: flex-start; }
  .swatch { width: 64px; height: 64px; flex: none; background: var(--surface-sunken); border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; overflow: hidden; }
  .swatch svg, .swatch img { width: 42px; height: 42px; }
  .card-meta { flex: 1; min-width: 0; }
  .card-id { font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .en-name { font-size: 0.92rem; font-weight: 500; margin-top: 2px; }
  .cat-tag { font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); margin-top: 2px; }
  .scrutiny-flag { display: inline-flex; align-items: center; gap: 4px; font-size: 0.72rem; font-weight: 500; color: var(--warn-ink); background: var(--warn-soft); border-radius: 999px; padding: 2px 9px; margin-top: 6px; }
  .field-label { font-size: 0.72rem; color: var(--text-muted); margin-bottom: 4px; display: block; }
  .he-input, .kw-input, .note-input { width: 100%; font-family: var(--font-ui); background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; color: var(--text); font-size: 0.95rem; }
  .he-input { font-size: 1.05rem; }
  .note-input { font-size: 0.85rem; color: var(--text-muted); }
  .keep-placeholder-toggle { display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: var(--text); cursor: pointer; background: var(--bg); border: 1px dashed var(--border-strong); border-radius: var(--radius-sm); padding: 8px 10px; }
  .card-footer { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: auto; }
  .status-pill { font-size: 0.72rem; font-weight: 500; padding: 3px 10px; border-radius: 999px; }
  .status-approved { background: var(--good-soft); color: var(--good); }
  .status-edited { background: var(--accent-soft); color: var(--accent); }
  .reset-link { font-size: 0.78rem; color: var(--text-muted); background: none; border: none; cursor: pointer; text-decoration: underline; padding: 0; font-family: var(--font-ui); }
  .reset-link:disabled { visibility: hidden; }
  .empty { text-align: center; color: var(--text-muted); padding: 60px 0; }
  footer.note { margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); font-size: 0.82rem; color: var(--text-muted); }
  @media (prefers-reduced-motion: no-preference) { .card { transition: box-shadow 0.15s ease, border-color 0.15s ease; } }
  [hidden] { display: none !important; }
</style>
<div class="wrap" dir="rtl" lang="he">
  <header class="top">
    <div class="title-block">
      <h1 id="page-title"></h1>
      <p id="page-desc"></p>
      <span class="batch-tag" id="batch-tag"></span>
    </div>
    <div class="stats" id="stats"></div>
  </header>
  <div class="toolbar">
    <input type="search" id="search" placeholder="חיפוש לפי מילה, קטגוריה או מזהה…" autocomplete="off">
    <button class="chip-toggle" id="scrutiny-toggle" type="button">רק תחליפים לבדיקה</button>
    <button class="chip-toggle" id="dirty-toggle" type="button">רק שערכתי</button>
    <div style="flex:1"></div>
    <span class="sync-status" id="sync-status"></span>
    <button class="btn btn-ghost" id="reset-all" type="button">בטל את כל השינויים</button>
    <button class="btn btn-primary" id="sync" type="button" disabled>סנכרן שינויים</button>
  </div>
  <div class="grid" id="grid"></div>
  <p class="empty" id="empty" hidden>אין תוצאות</p>
  <footer class="note">
    כל שינוי כאן נשמר רק בלחיצה על "סנכרן שינויים" — הדף מתעדכן לגרסה החדשה עבור כל מי שפותח אותו.
    מזהה המילה (בסוגריים המנעול) לעולם לא ניתן לשינוי כאן — הוא מקושר לכרטיסיות קיימות בלוח ולכן קבוע.
  </footer>
</div>
"""

APP_JS = r"""
const OWN_SRC = document.currentScript.textContent;
const SKELETON = window.__SKELETON__;

let rows = window.__DATA__.rows.map(r => ({ ...r, _orig: JSON.parse(JSON.stringify(r)) }));
let scrutinyOnly = false;
let dirtyOnly = false;

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function isDirty(r) {
  return r.label_he !== r._orig.label_he
    || JSON.stringify(r.keywords_he) !== JSON.stringify(r._orig.keywords_he)
    || (r.note || "") !== (r._orig.note || "")
    || !!r.keep_placeholder !== !!r._orig.keep_placeholder;
}

function currentSvg(r) {
  if (r.scrutiny === "substitute" && r.keep_placeholder) return r.placeholder_svg || r.svg;
  return r.svg;
}

function renderStats() {
  const el = document.getElementById("stats");
  const total = rows.length;
  const scrutiny = rows.filter(r => r.scrutiny === "substitute").length;
  const dirty = rows.filter(isDirty).length;
  el.innerHTML =
    '<div class="stat"><div class="n">' + total + '</div><div class="l">סה"כ</div></div>' +
    '<div class="stat warn"><div class="n">' + scrutiny + '</div><div class="l">תחליפים לבדיקה</div></div>' +
    '<div class="stat good"><div class="n">' + dirty + '</div><div class="l">נערכו</div></div>';
}

function cardHtml(r, i) {
  const dirty = isDirty(r);
  const svg = currentSvg(r);
  const statusLabel = dirty ? "נערך" : (r.status === "approved" ? "אושר" : "טרם נבדק");
  const statusClass = dirty ? "status-edited" : "status-approved";
  const kwText = (r.keywords_he || []).join(", ");
  const enName = r.src ? r.src.replace(/_,_to$/, " (to)").replace(/_/g, " ") : "— (ללא סמל Mulberry)";
  return '' +
    '<article class="card ' + (r.scrutiny === "substitute" ? "scrutiny" : "") + ' ' + (dirty ? "dirty" : "") + '" data-i="' + i + '">' +
      '<div class="card-head">' +
        '<div class="swatch">' + (svg || "") + '</div>' +
        '<div class="card-meta">' +
          '<div class="card-id"><span title="מזהה קבוע, לא ניתן לשינוי">🔒 ' + esc(r.id) + '</span></div>' +
          '<div class="en-name">' + esc(enName) + '</div>' +
          '<div class="cat-tag">' + esc(r.category_en || "") + (r.grammar ? " · " + esc(r.grammar) : "") + '</div>' +
          (r.scrutiny === "substitute" ? '<span class="scrutiny-flag">⚠ תחליף מקורב</span>' : "") +
        '</div>' +
      '</div>' +
      (r.scrutiny === "substitute" ?
        '<label class="keep-placeholder-toggle"><input type="checkbox" class="keep-ph" ' + (r.keep_placeholder ? "checked" : "") + '>' +
        'השאר את הסמל הזמני הנוכחי (אל תשתמש בתחליף מ־Mulberry)</label>' : "") +
      '<div><label class="field-label">תווית בעברית</label><input class="he-input" dir="rtl" value="' + esc(r.label_he) + '"></div>' +
      '<div><label class="field-label">מילות מפתח (מופרדות בפסיק)</label><input class="kw-input" dir="rtl" value="' + esc(kwText) + '"></div>' +
      '<div><label class="field-label">הערה (אופציונלי)</label><input class="note-input" dir="rtl" value="' + esc(r.note) + '"></div>' +
      '<div class="card-footer"><span class="status-pill ' + statusClass + '">' + statusLabel + '</span>' +
        '<button class="reset-link" ' + (dirty ? "" : "disabled") + '>שחזר</button></div>' +
    '</article>';
}

function matchesFilters(r) {
  const q = document.getElementById("search").value.trim().toLowerCase();
  if (scrutinyOnly && r.scrutiny !== "substitute") return false;
  if (dirtyOnly && !isDirty(r)) return false;
  if (!q) return true;
  const hay = [r.id, r.src, r.category_en, r.label_he, ...(r.keywords_he || [])].join(" ").toLowerCase();
  return hay.includes(q);
}

function renderGrid() {
  const grid = document.getElementById("grid");
  const visible = rows.map((r, i) => [r, i]).filter(([r]) => matchesFilters(r));
  document.getElementById("empty").hidden = visible.length > 0;
  grid.innerHTML = visible.map(([r, i]) => cardHtml(r, i)).join("");
  document.getElementById("sync").disabled = !rows.some(isDirty);
  renderStats();
}

document.getElementById("page-title").textContent = window.__DATA__.title;
document.getElementById("page-desc").textContent = window.__DATA__.description;
document.getElementById("batch-tag").textContent =
  "Mulberry " + window.__DATA__.mulberry_version + " · אצווה: " + window.__DATA__.batch +
  " · " + rows.length + " שורות";

document.getElementById("search").addEventListener("input", renderGrid);
document.getElementById("scrutiny-toggle").addEventListener("click", e => {
  scrutinyOnly = !scrutinyOnly;
  e.target.classList.toggle("active", scrutinyOnly);
  renderGrid();
});
document.getElementById("dirty-toggle").addEventListener("click", e => {
  dirtyOnly = !dirtyOnly;
  e.target.classList.toggle("active", dirtyOnly);
  renderGrid();
});
document.getElementById("reset-all").addEventListener("click", () => {
  if (!confirm("לבטל את כל השינויים שלא סונכרנו?")) return;
  rows = window.__DATA__.rows.map(r => ({ ...r, _orig: JSON.parse(JSON.stringify(r)) }));
  renderGrid();
});
document.getElementById("grid").addEventListener("input", e => {
  const card = e.target.closest(".card");
  if (!card) return;
  const i = Number(card.dataset.i);
  const r = rows[i];
  let selector = null;
  if (e.target.classList.contains("he-input")) { r.label_he = e.target.value; selector = ".he-input"; }
  else if (e.target.classList.contains("kw-input")) { r.keywords_he = e.target.value.split(",").map(s => s.trim()).filter(Boolean); selector = ".kw-input"; }
  else if (e.target.classList.contains("note-input")) { r.note = e.target.value || null; selector = ".note-input"; }
  else return;
  renderGrid();
  const fresh = document.querySelector('.card[data-i="' + i + '"] ' + selector);
  if (fresh) { fresh.focus(); fresh.setSelectionRange(fresh.value.length, fresh.value.length); }
});
document.getElementById("grid").addEventListener("change", e => {
  const card = e.target.closest(".card");
  if (!card) return;
  const i = Number(card.dataset.i);
  if (e.target.classList.contains("keep-ph")) { rows[i].keep_placeholder = e.target.checked; renderGrid(); }
});
document.getElementById("grid").addEventListener("click", e => {
  if (!e.target.classList.contains("reset-link")) return;
  const i = Number(e.target.closest(".card").dataset.i);
  rows[i] = { ...rows[i]._orig, _orig: rows[i]._orig };
  renderGrid();
});

// Regenerate the full document from the Python-built SKELETON string + this
// script's own verbatim source (document.currentScript.textContent, captured
// once above) — never from document.documentElement/body, which the runtime
// explicitly warns carries viewer-session state and platform-injected
// scripts. SKELETON and OWN_SRC together reproduce the file byte-for-byte
// except for the data payload.
function buildHtml() {
  const outRows = rows.map(r => { const { _orig, ...clean } = r; return clean; });
  const outData = { ...window.__DATA__, rows: outRows };
  return "<!doctype html>\n" + SKELETON +
    '<script>window.__SKELETON__ = ' + JSON.stringify(SKELETON) + ";<\/script>\n" +
    '<script>window.__DATA__ = ' + JSON.stringify(outData) + ";<\/script>\n" +
    "<script>" + OWN_SRC + "<\/script>\n";
}

async function sync() {
  const btn = document.getElementById("sync");
  const status = document.getElementById("sync-status");
  btn.disabled = true;
  status.textContent = "מסנכרן…";
  status.className = "sync-status";
  try {
    const artifact = await Promise.race([
      window.claude ? window.claude.use("artifact") : Promise.resolve(null),
      new Promise(res => setTimeout(() => res(null), 10000)),
    ]);
    if (!artifact) {
      status.textContent = "אין אפשרות לשמור מהתצוגה הזו.";
      status.className = "sync-status err";
      btn.disabled = false;
      return;
    }
    await artifact.publish(buildHtml());
    status.textContent = "נשמר ✓";
    status.className = "sync-status ok";
  } catch (err) {
    status.textContent = (err && err.code === "conflict")
      ? "מישהו אחר שמר גרסה חדשה יותר — הדף ייטען מחדש."
      : "השמירה נכשלה: " + (err && err.message ? err.message : String(err));
    status.className = "sync-status err";
    btn.disabled = false;
  }
}
document.getElementById("sync").addEventListener("click", sync);

renderGrid();
"""


def render_page(
    *, title: str, description: str, batch: str, mulberry_version: str, rows: list[dict]
) -> str:
    data = {
        "title": title,
        "description": description,
        "batch": batch,
        "mulberry_version": mulberry_version,
        "rows": rows,
    }
    # The <title> tag always wins over the Artifact tool's `title` publish
    # param, so bake the real title into the skeleton itself — and into its
    # embedded self-copy (window.__SKELETON__), or a reviewer's "sync" would
    # republish with the placeholder title instead of this batch's.
    skeleton = SKELETON.replace("__PAGE_TITLE__", title)
    return (
        skeleton
        + f"<script>window.__SKELETON__ = {json.dumps(skeleton)};</script>\n"
        + f"<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False)};</script>\n"
        + f"<script>{APP_JS}</script>\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--batch", choices=["locked", "pending"], default="locked")
    p.add_argument(
        "--status",
        default="pending",
        help="for --batch pending: which status to include",
    )
    p.add_argument(
        "--limit", type=int, default=None, help="for --batch pending: max rows"
    )
    p.add_argument(
        "--category",
        default=None,
        help="for --batch pending: filter to one category_en",
    )
    p.add_argument(
        "--labeled-only",
        action="store_true",
        help="for --batch pending: skip rows with no label_he yet (not authored)",
    )
    p.add_argument("--out", default="/tmp/mulberry_review.html")
    args = p.parse_args()

    manifest = mm.load_manifest()
    with zipfile.ZipFile(mm.DEFAULT_SOURCE_ZIP) as zf:
        if args.batch == "locked":
            rows = _rows_for_locked(manifest, zf)
            title = "סמלי מולברי — אצווה 1"
            desc = (
                "אימות 36 ההתאמות ל־Mulberry Symbols (CC BY-SA 4.0) עבור המילים הקיימות בלוח. "
                "10 מהן הן תחליפים מקורבים (מסומנים בכתום) שכדאי לבדוק בעין במיוחד. "
                "3 מילים (עצור, תודה, לא רוצה) נשארות עם הסמל הזמני הקיים."
            )
            batch_name = "batch-1-locked"
        else:
            rows = _rows_for_pending(
                manifest,
                zf,
                status=args.status,
                limit=args.limit,
                category=args.category,
                labeled_only=args.labeled_only,
            )
            cat_note = f" ({args.category})" if args.category else ""
            title = f"סמלי מולברי — {len(rows)} מועמדים חדשים{cat_note}"
            desc = "תוויות עבריות מוצעות לסמלים חדשים מתוך Mulberry Symbols. אשרו, ערכו או דחו כל שורה."
            batch_name = f"pending-{args.category or 'all'}-{len(rows)}"

    html = render_page(
        title=title,
        description=desc,
        batch=batch_name,
        mulberry_version=manifest["mulberry_version"],
        rows=rows,
    )
    out_path = Path(args.out)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {len(rows)} rows -> {out_path} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
