// Shared picture control — bundled-symbol search, in-app camera capture, and
// file upload — for every editor that attaches an image to a card-like item
// (AAC cards/categories, schedule items, My Tasks items, token rules and
// rewards). Lifted out of modules/aac/editor.js so those other editors get
// the same option instead of being limited to bundled symbols.
//
// Mutates `state.symbol_id` / `state.icon_asset_id` in place and calls
// `onChange` after every pick/capture/upload/clear — the two are mutually
// exclusive, the same rule the backend enforces (schemas/*.py `_Visual`).

import { api } from "./api.js";
import { el, errText, toast, visual } from "./ui.js";
import { createSymbolPicker } from "./modules/aac/symbol-picker.js";
import { isCameraSupported, capturePhoto } from "./camera.js";
import { scaleForUpload } from "./image-scale.js";

export function createVisualPicker({ childId, state, kind = "card_icon", onChange }) {
  const preview = el("div", { class: "visual-preview" });
  function refresh() {
    if (state.symbol_id || state.icon_asset_id) {
      preview.replaceChildren(visual(state, "visual-preview-img"));
    } else {
      preview.replaceChildren(el("span", { class: "muted" }, "אין תמונה"));
    }
  }
  refresh();

  async function attachAsset(file) {
    try {
      const up = await api.upload("/media", { kind, child_id: childId }, file);
      state.icon_asset_id = up.id;
      state.symbol_id = null;
      refresh();
      onChange?.();
    } catch (err) {
      toast(errText(err), "error");
    }
  }

  const picker = createSymbolPicker((s) => {
    state.symbol_id = s.id;
    state.icon_asset_id = null;
    refresh();
    onChange?.();
  });

  const cameraBtn = isCameraSupported()
    ? el(
        "button",
        {
          type: "button",
          class: "btn-link",
          onclick: async () => {
            const file = await capturePhoto();
            if (file) await attachAsset(file);
          },
        },
        "צלם תמונה",
      )
    : null;

  const iconInput = el("input", {
    type: "file",
    accept: "image/png,image/jpeg,image/webp",
    onchange: async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        await attachAsset(await scaleForUpload(file));
      } catch {
        toast("לא ניתן להשתמש בקובץ הזה", "error");
      } finally {
        e.target.value = "";
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
    cameraBtn,
    el("label", { class: "file-row" }, "או העלאת תמונה משלך: ", iconInput),
    el(
      "p",
      { class: "muted visual-privacy-note" },
      "צלמו את הדבר עצמו — כוס, תיק, חטיף, מקום. לא אנשים: תמונות של בני משפחה אינן נשמרות במערכת.",
    ),
    clearBtn,
  );
}
