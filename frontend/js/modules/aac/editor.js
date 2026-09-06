// AAC card editor (Caregiver Mode). Manage categories (which nest) and cards
// for one child.

import { api } from "../../api.js";
import { el, errText, icon, mount, symbolUrl, toast, withBusy } from "../../ui.js";
import { confirmDialog, destructiveDialog } from "../../dialog.js";
import { renderAacBoard } from "./board.js";
import { recordClip } from "./recorder.js";
import { createSymbolPicker } from "./symbol-picker.js";

// Keep in sync with _CATEGORY_PALETTE in backend/app/api/aac.py — the same
// hues the backend auto-assigns to a new category with no colour.
const CATEGORY_COLORS = [
  "#1f6feb",
  "#1a7f37",
  "#9a6700",
  "#b42318",
  "#8250df",
  "#bf3989",
  "#0e7490",
  "#a24e00",
  "#4d7c0f",
  "#57606a",
];

export async function renderAacEditor({ childId, childName, onExit }) {
  let board;
  let voiceConsent = false;

  async function load() {
    [board] = await Promise.all([
      api.get(`/aac/board?child_id=${encodeURIComponent(childId)}`),
      api
        .get("/auth/session")
        .then((s) => {
          voiceConsent = s.onboarding?.voice_consent ?? false;
        })
        .catch(() => {}),
    ]);
    render();
  }

  function cardsOf(catId) {
    return board.cards
      .filter((c) => c.category_id === catId)
      .sort((a, b) => a.grid_order - b.grid_order);
  }

  // Flat list of { cat, depth }, roots first, each category immediately
  // followed by its own sub-tree (depth-first, siblings by sort_order).
  function categoryTree() {
    const byParent = new Map();
    for (const c of board.categories) {
      const p = c.parent_id ?? "";
      if (!byParent.has(p)) byParent.set(p, []);
      byParent.get(p).push(c);
    }
    for (const list of byParent.values()) list.sort((a, b) => a.sort_order - b.sort_order);
    const out = [];
    (function walk(parent, depth) {
      for (const c of byParent.get(parent) ?? []) {
        out.push({ cat: c, depth });
        walk(c.id, depth + 1);
      }
    })("", 0);
    return out;
  }

  function descendantIds(catId) {
    const kids = board.categories.filter((c) => c.parent_id === catId);
    return kids.flatMap((k) => [k.id, ...descendantIds(k.id)]);
  }

  function render() {
    mount(
      el(
        "section",
        { class: "aac-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `עריכת בוא נדבר — ${childName}`),
          el("button", { class: "btn-link", onclick: openPreview }, "תצוגה מקדימה"),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        ...categoryTree().map(({ cat, depth }) => categoryBlock(cat, depth)),
        el(
          "form",
          { class: "card add-cat", onsubmit: addCategory },
          el("input", {
            name: "name",
            type: "text",
            required: true,
            maxlength: 40,
            placeholder: "שם קטגוריה חדשה (רמה עליונה)",
          }),
          el("button", { type: "submit", class: "btn-primary" }, "הוסף קטגוריה"),
        ),
      ),
    );
  }

  function categoryBlock(cat, depth) {
    return el(
      "article",
      {
        class: "card cat-block",
        "data-depth": depth || null,
        style: depth ? `margin-inline-start: calc(${depth} * var(--space-6))` : null,
      },
      el(
        "div",
        { class: "cat-block-head" },
        catThumb(cat),
        el("span", { class: "cat-block-name" }, cat.name),
        el(
          "div",
          { class: "editor-card-actions" },
          el("button", { class: "btn-link", onclick: () => openCategoryForm(cat) }, "ערוך קטגוריה"),
          el(
            "button",
            {
              class: "btn-link",
              onclick: () => openCategoryForm({ parent_id: cat.id }),
            },
            "+ תת-קטגוריה",
          ),
          el(
            "button",
            {
              class: "btn-link danger",
              onclick: async () => {
                const ok = await destructiveDialog({
                  title: "מחיקת קטגוריה",
                  body: `למחוק את הקטגוריה "${cat.name}"? סעיפי המשנה והכרטיסים שבה יעברו לרמה העליונה.`,
                });
                if (!ok) return;
                await api.del(`/aac/categories/${cat.id}`);
                load();
              },
            },
            "מחק קטגוריה",
          ),
        ),
      ),
      el("div", { class: "editor-card-list" }, ...cardsOf(cat.id).map((c) => cardRow(c, cat.id))),
      el(
        "button",
        { class: "btn-link", onclick: () => openCardForm({ category_id: cat.id }) },
        "+ הוסף כרטיס",
      ),
    );
  }

  function catThumb(cat) {
    if (cat.symbol_id) {
      return el("img", { class: "editor-thumb", src: symbolUrl(cat.symbol_id), alt: "" });
    }
    if (cat.icon_asset_id) {
      return el("img", { class: "editor-thumb", src: `/api/media/${cat.icon_asset_id}`, alt: "" });
    }
    return el("span", { class: "editor-thumb editor-thumb-text" }, cat.name.slice(0, 2));
  }

  function cardRow(card, catId) {
    const siblings = cardsOf(catId);
    const i = siblings.findIndex((c) => c.id === card.id);
    return el(
      "div",
      { class: "editor-card-row" },
      cardThumb(card),
      el("span", { class: "editor-card-label" }, card.label),
      el(
        "div",
        { class: "editor-card-actions" },
        el(
          "button",
          { class: "sb-btn", "aria-label": "הזז ימינה", disabled: i === 0, onclick: () => move(siblings, i, -1) },
          icon("chevron_right"),
        ),
        el(
          "button",
          {
            class: "sb-btn",
            "aria-label": "הזז שמאלה",
            disabled: i === siblings.length - 1,
            onclick: () => move(siblings, i, 1),
          },
          icon("chevron_left"),
        ),
        el("button", { class: "btn-link", onclick: () => openCardForm(card) }, "ערוך"),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              const ok = await destructiveDialog({ title: "מחיקת כרטיס", body: `למחוק את "${card.label}"?` });
              if (!ok) return;
              await api.del(`/aac/cards/${card.id}`);
              load();
            },
          },
          "מחק",
        ),
      ),
    );
  }

  function cardThumb(card) {
    if (card.symbol_id) {
      return el("img", { class: "editor-thumb", src: symbolUrl(card.symbol_id), alt: "" });
    }
    if (card.icon_asset_id) {
      return el("img", { class: "editor-thumb", src: `/api/media/${card.icon_asset_id}`, alt: "" });
    }
    return el("span", { class: "editor-thumb editor-thumb-text" }, card.label.slice(0, 2));
  }

  async function move(siblings, i, delta) {
    const j = i + delta;
    const order = siblings.map((c) => c.id);
    [order[i], order[j]] = [order[j], order[i]];
    try {
      await api.put("/aac/cards/order", { child_id: childId, order });
      await load();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  async function addCategory(e) {
    e.preventDefault();
    const name = new FormData(e.target).get("name").trim();
    const btn = e.target.querySelector('button[type="submit"]');
    await withBusy(btn, async () => {
      try {
        await api.post("/aac/categories", { child_id: childId, name });
        load();
      } catch (err) {
        toast(errText(err), "error");
      }
    });
  }

  // Opens the real child-facing board, read-only, in a near-full-screen
  // dialog — so "does it fit without scrolling" is answered by the actual
  // renderer, not a second hand-built layout that could drift from it.
  function openPreview() {
    const previewHost = el("div", { class: "preview-body" });
    const dlg = el("dialog", { class: "dialog dialog-preview" }, previewHost);
    document.body.append(dlg);
    dlg.addEventListener("click", (e) => {
      if (e.target === dlg) dlg.close();
    });
    dlg.addEventListener("close", () => dlg.remove(), { once: true });
    dlg.showModal();
    renderAacBoard({ childId, childName, preview: true, host: previewHost, onExit: () => dlg.close() });
  }

  // --- shared picture control (card form + category form) ----------------

  // Mutates `state.symbol_id` / `state.icon_asset_id` in place and calls
  // `onChange` after every pick/upload/clear. The two are mutually exclusive
  // (same rule the backend enforces), so setting one clears the other.
  function visualEditor(state, onChange) {
    const preview = el("div", { class: "visual-preview" });
    function refresh() {
      if (state.symbol_id) {
        preview.replaceChildren(el("img", { src: symbolUrl(state.symbol_id), alt: "" }));
      } else if (state.icon_asset_id) {
        preview.replaceChildren(el("img", { src: `/api/media/${state.icon_asset_id}`, alt: "" }));
      } else {
        preview.replaceChildren(el("span", { class: "muted" }, "אין תמונה"));
      }
    }
    refresh();

    const picker = createSymbolPicker((s) => {
      state.symbol_id = s.id;
      state.icon_asset_id = null;
      refresh();
      onChange?.();
    });

    const iconInput = el("input", {
      type: "file",
      accept: "image/png,image/jpeg,image/webp",
      onchange: async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
          const up = await uploadMedia("card_icon", file);
          state.icon_asset_id = up.id;
          state.symbol_id = null;
          refresh();
          onChange?.();
        } catch (err) {
          toast(errText(err), "error");
        }
      },
    });

    const clearBtn = el(
      "button",
      {
        type: "button",
        class: "btn-link",
        onclick: () => {
          state.symbol_id = null;
          state.icon_asset_id = null;
          refresh();
          onChange?.();
        },
      },
      "הסר תמונה",
    );

    return el(
      "div",
      { class: "visual-editor" },
      preview,
      picker,
      el("label", { class: "file-row" }, "או העלאת תמונה משלך: ", iconInput),
      clearBtn,
    );
  }

  // Flattened category <select>, indented by depth. `excludeId` (and its
  // sub-tree) is omitted — a category can't be its own ancestor.
  function categorySelect(selectedId, excludeId) {
    const blocked = excludeId ? new Set([excludeId, ...descendantIds(excludeId)]) : new Set();
    const sel = el(
      "select",
      { name: "category" },
      el("option", { value: "" }, "— ללא (רמה עליונה) —"),
      ...categoryTree()
        .filter(({ cat }) => !blocked.has(cat.id))
        .map(({ cat, depth }) =>
          el("option", { value: cat.id }, `${"  ".repeat(depth)}${cat.name}`),
        ),
    );
    sel.value = selectedId ?? "";
    return sel;
  }

  // --- category add/edit form ------------------------------------------

  function openCategoryForm(cat) {
    const editing = !!cat.id;
    const state = {
      symbol_id: cat.symbol_id || null,
      icon_asset_id: cat.icon_asset_id || null,
      color: cat.color || null,
    };
    const parentSelect = categorySelect(cat.parent_id ?? "", cat.id);

    // Colour swatches — the picked one gets a ring. For a new category an
    // "אוטומטי" chip (state.color = null) lets the backend pick the first free
    // palette hue; once a category exists it always has a colour, so editing
    // just offers the swatches.
    const swatchRow = el("div", { class: "swatch-row" });
    function paintSwatches() {
      const auto = el(
        "button",
        {
          type: "button",
          class: state.color ? "swatch swatch-auto" : "swatch swatch-auto swatch-on",
          onclick: () => {
            state.color = null;
            paintSwatches();
          },
        },
        "אוטומטי",
      );
      swatchRow.replaceChildren(
        ...(editing ? [] : [auto]),
        ...CATEGORY_COLORS.map((hex) =>
          el("button", {
            type: "button",
            class: state.color === hex ? "swatch swatch-on" : "swatch",
            style: `--sw:${hex}`,
            "aria-label": `צבע ${hex}`,
            onclick: () => {
              state.color = hex;
              paintSwatches();
            },
          }),
        ),
      );
    }
    paintSwatches();

    const form = el(
      "form",
      { class: "card card-form", onsubmit: submit },
      el("h3", {}, editing ? "עריכת קטגוריה" : "קטגוריה חדשה"),
      field("name", "שם הקטגוריה", cat.name || "", { required: true, maxlength: 40 }),
      el("div", { class: "field" }, el("label", {}, "נמצאת תחת"), parentSelect),
      el("p", { class: "muted" }, "צבע:"),
      swatchRow,
      el("p", { class: "muted" }, "תמונה:"),
      visualEditor(state, null),
      el(
        "div",
        { class: "form-actions" },
        el("button", { type: "submit", class: "btn-primary" }, "שמור"),
        el("button", { type: "button", class: "btn-link", onclick: render }, "ביטול"),
      ),
      el("p", { class: "err", id: "cat-err", role: "alert" }),
    );

    async function submit(e) {
      e.preventDefault();
      const f = new FormData(e.target);
      const body = {
        name: f.get("name").trim(),
        parent_id: f.get("category") || null,
        symbol_id: state.symbol_id,
        icon_asset_id: state.icon_asset_id,
      };
      // New: send color (null → backend auto-picks). Editing: only when set, so
      // an untouched form never clears an existing colour.
      if (!editing || state.color) body.color = state.color;
      const btn = e.target.querySelector('button[type="submit"]');
      await withBusy(btn, async () => {
        try {
          if (editing) {
            await api.patch(`/aac/categories/${cat.id}`, body);
          } else {
            await api.post("/aac/categories", { child_id: childId, ...body });
          }
          load();
        } catch (err) {
          document.getElementById("cat-err").textContent = errText(err);
        }
      });
    }

    mount(form);
  }

  // --- card add/edit form ------------------------------------------------

  function openCardForm(card) {
    const editing = !!card.id;
    const state = {
      symbol_id: card.symbol_id || null,
      icon_asset_id: card.icon_asset_id || null,
      audio_asset_id: card.audio_asset_id || null,
    };

    const catSelect = categorySelect(card.category_id ?? "", null);
    const audioStatus = el("span", { class: "muted" }, state.audio_asset_id ? "הוקלט" : "TTS");

    const dialog = el(
      "form",
      { class: "card card-form", onsubmit: submit },
      el("h3", {}, editing ? "עריכת כרטיס" : "כרטיס חדש"),
      field("label", "מילה / תווית", card.label || "", { required: true, maxlength: 40 }),
      field("tts_text", "טקסט להקראה (רשות)", card.tts_text || "", { maxlength: 200 }),
      el("div", { class: "field" }, el("label", {}, "קטגוריה"), catSelect),
      el("p", { class: "muted" }, "תמונה:"),
      visualEditor(state, null),
      el(
        "div",
        { class: "audio-row" },
        el("span", {}, "קול: "),
        audioStatus,
        el(
          "button",
          {
            type: "button",
            class: "btn-link",
            onclick: () => attachRecording(audioStatus, (id) => (state.audio_asset_id = id)),
          },
          icon("mic"),
          " הקלטה",
        ),
        state.audio_asset_id &&
          el(
            "button",
            {
              type: "button",
              class: "btn-link",
              onclick: () => {
                state.audio_asset_id = null;
                audioStatus.textContent = "TTS";
              },
            },
            "הסר הקלטה",
          ),
      ),
      el("div", { class: "form-actions" },
        el("button", { type: "submit", class: "btn-primary" }, "שמור"),
        el("button", { type: "button", class: "btn-link", onclick: render }, "ביטול"),
      ),
      el("p", { class: "err", id: "cf-err", role: "alert" }),
    );

    async function submit(e) {
      e.preventDefault();
      const f = new FormData(e.target);
      const body = {
        label: f.get("label").trim(),
        tts_text: f.get("tts_text").trim() || null,
        symbol_id: state.symbol_id,
        icon_asset_id: state.icon_asset_id,
        category_id: f.get("category") || null,
      };
      const btn = e.target.querySelector('button[type="submit"]');
      await withBusy(btn, async () => {
        try {
          if (editing) {
            await api.patch(`/aac/cards/${card.id}`, { ...body, audio_asset_id: state.audio_asset_id });
          } else {
            await api.post("/aac/cards", { child_id: childId, ...body });
            if (state.audio_asset_id) {
              // second call to attach the recording to the just-created card
              const created = (await api.get(
                `/aac/board?child_id=${encodeURIComponent(childId)}`,
              )).cards.at(-1);
              await api.patch(`/aac/cards/${created.id}`, { audio_asset_id: state.audio_asset_id });
            }
          }
          load();
        } catch (err) {
          document.getElementById("cf-err").textContent = errText(err);
        }
      });
    }

    mount(dialog);
  }

  async function attachRecording(statusEl, setId) {
    if (!voiceConsent) {
      const ok = await confirmDialog({
        title: "הקלטת קול",
        body: "הקלטת קול דורשת אישור. לאשר עכשיו?",
        confirmLabel: "אישור",
      });
      if (!ok) return;
      try {
        await api.post("/auth/voice-consent", { accept: true });
        voiceConsent = true;
      } catch (err) {
        return toast(errText(err), "error");
      }
    }
    statusEl.textContent = "מקליט… (לחץ שוב לעצירה)";
    let session;
    try {
      session = await recordClip();
    } catch {
      statusEl.textContent = "אין גישה למיקרופון";
      return;
    }
    statusEl.onclick = null;
    const stopBtn = statusEl;
    stopBtn.style.cursor = "pointer";
    stopBtn.onclick = async () => {
      const blob = await session.stop();
      stopBtn.onclick = null;
      try {
        const up = await uploadMedia("card_audio", new File([blob], "clip.webm", { type: blob.type }));
        setId(up.id);
        statusEl.textContent = "הוקלט";
      } catch (err) {
        statusEl.textContent = "שגיאה בהעלאה";
        toast(errText(err), "error");
      }
    };
  }

  async function uploadMedia(kind, file) {
    const fd = new FormData();
    fd.append("kind", kind);
    fd.append("child_id", childId);
    fd.append("file", file);
    const res = await fetch("/api/media", { method: "POST", credentials: "include", body: fd });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw Object.assign(new Error("upload"), { code: body?.error, body });
    return body;
  }

  function field(name, label, value, attrs = {}) {
    return el(
      "div",
      { class: "field" },
      el("label", {}, label),
      el("input", { name, type: "text", value, ...attrs }),
    );
  }

  await load();
}
