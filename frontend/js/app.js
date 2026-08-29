// Entry point. Registers the service worker, resolves the session, and shows
// the right screen: auth → onboarding PIN → User Mode home ⇄ Caregiver Mode.

import { api } from "./api.js";
import { exitCaregiverMode, logout, refresh, state } from "./session.js";
import { startOutbox } from "./outbox.js";
import { el, errText, mount } from "./ui.js";
import { renderAuth } from "./views/auth.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderHome } from "./views/home.js";
import { renderPinpad } from "./views/pinpad.js";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((e) => console.warn("SW failed", e));
  });
}

async function route() {
  document.body.dataset.mode = state.mode;

  if (!state.authenticated) {
    return renderAuth(async () => {
      await refresh();
      route();
    });
  }

  if (state.onboarding?.needs_pin) {
    return renderPinpad({
      title: "בחירת קוד מטפל",
      hint: "קוד בן 4 ספרות שרק המטפל יודע. הוא נדרש כדי לשנות הגדרות.",
      onSubmit: async (pin) => {
        try {
          await api.put("/auth/pin", { pin });
        } catch (e) {
          throw errText(e);
        }
        await refresh();
        route();
      },
    });
  }

  if (state.mode === "caregiver") {
    return renderDashboard({
      onExit: async () => {
        await exitCaregiverMode();
        route();
      },
      onLogout: async () => {
        await logout();
        route();
      },
    });
  }

  return renderHome({ onEnterCaregiver: showPinVerify });
}

function showPinVerify() {
  renderPinpad({
    title: "כניסה למצב מטפל",
    hint: "הזינו את קוד המטפל",
    onCancel: () => route(),
    onSubmit: async (pin) => {
      try {
        await api.post("/auth/pin", { pin });
      } catch (e) {
        throw errText(e);
      }
      await refresh();
      route();
    },
  });
}

// A persistent sign-out affordance in Caregiver Mode / onboarding.
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && state.authenticated && state.mode === "caregiver") {
    exitCaregiverMode().then(route);
  }
});

async function boot() {
  mount(el("p", { class: "muted" }, "טוען…"));
  try {
    await refresh();
  } catch {
    mount(
      el("p", { class: "err" }, "אין חיבור לשרת."),
      el("button", { class: "btn-link", onclick: boot }, "נסה שוב"),
    );
    return;
  }
  route();
  startOutbox();
}

boot();
