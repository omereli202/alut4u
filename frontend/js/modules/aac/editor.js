// AAC card editor (Caregiver Mode). Manage categories and cards for one child.

import { api } from "../../api.js";
import { el, errText, icon, mount, toast } from "../../ui.js";
import { confirmDialog, destructiveDialog } from "../../dialog.js";
import { recordClip } from "./recorder.js";
import { createSymbolPicker } from "./symbol-picker.js";

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

  function render() {
    mount(
      el(
        "section",
        { class: "aac-editor", "data-mode": "caregiver" },
        el(
          "header",
          { class: "dash-head" },
          el("h1", {}, `לוח תקשורת — ${childName}`),
          el("button", { class: "btn-link", onclick: onExit }, "חזרה"),
        ),
        ...board.categories.map(categoryBlock),
        el(
          "form",
          { class: "card add-cat", onsubmit: addCategory },
          el("input", {
            name: "name",
            type: "text",
            required: true,
            maxlength: 40,
            placeholder: "שם קטגוריה חדשה",
          }),
          el("button", { type: "submit", class: "btn-primary" }, "הוסף קטגוריה"),
        ),
      ),
    );
  }

  function categoryBlock(cat) {
    return el(
      "article",
      { class: "card cat-block" },
      el(
        "div",
        { class: "cat-block-head" },
        el("input", {
          class: "cat-name-input",
          value: cat.name,
          "aria-label": "שם קטגוריה",
          onchange: async (e) => {
            try {
              await api.patch(`/aac/categories/${cat.id}`, { name: e.target.value.trim() });
            } catch (err) {
              toast(errText(err), "error");
            }
          },
        }),
        el(
          "button",
          {
            class: "btn-link danger",
            onclick: async () => {
              const ok = await destructiveDialog({
                title: "מחיקת קטגוריה",
                body: `למחוק את הקטגוריה "${cat.name}"? הכרטיסים יישארו ללא קטגוריה.`,
              });
              if (!ok) return;
              await api.del(`/aac/categories/${cat.id}`);
              load();
            },
          },
          "מחק קטגוריה",
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
      return el("img", { class: "editor-thumb", src: `/assets/symbols/${card.symbol_id}.svg`, alt: "" });
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
    try {
      await api.post("/aac/categories", { child_id: childId, name });
      load();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  // --- card add/edit form ------------------------------------------------

  function openCardForm(card) {
    const editing = !!card.id;
    const state = {
      label: card.label || "",
      tts_text: card.tts_text || "",
      symbol_id: card.symbol_id || null,
      icon_asset_id: card.icon_asset_id || null,
      audio_asset_id: card.audio_asset_id || null,
      category_id: card.category_id ?? null,
    };

    const visualPreview = el("div", { class: "visual-preview" });
    function refreshPreview() {
      if (state.symbol_id) {
        visualPreview.replaceChildren(
          el("img", { src: `/assets/symbols/${state.symbol_id}.svg`, alt: "" }),
        );
      } else if (state.icon_asset_id) {
        visualPreview.replaceChildren(
          el("img", { src: `/api/media/${state.icon_asset_id}`, alt: "" }),
        );
      } else {
        visualPreview.replaceChildren(el("span", { class: "muted" }, "אין תמונה"));
      }
    }
    refreshPreview();

    const picker = createSymbolPicker((s) => {
      state.symbol_id = s.id;
      state.icon_asset_id = null;
      refreshPreview();
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
          refreshPreview();
        } catch (err) {
          toast(errText(err), "error");
        }
      },
    });

    const audioStatus = el("span", { class: "muted" }, state.audio_asset_id ? "הוקלט" : "TTS");

    const dialog = el(
      "form",
      { class: "card card-form", onsubmit: submit },
      el("h3", {}, editing ? "עריכת כרטיס" : "כרטיס חדש"),
      field("label", "מילה / תווית", state.label, { required: true, maxlength: 40 }),
      field("tts_text", "טקסט להקראה (רשות)", state.tts_text, { maxlength: 200 }),
      el("p", { class: "muted" }, "תמונה:"),
      visualPreview,
      picker,
      el("label", { class: "file-row" }, "או העלאת תמונה משלך: ", iconInput),
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
        category_id: state.category_id,
      };
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
