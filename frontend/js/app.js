// Entry point. Registers the service worker, resolves the session, and shows
// the right screen: auth → onboarding PIN → User Mode home ⇄ Caregiver Mode.

import { api } from "./api.js";
import { exitCaregiverMode, logout, refresh, state } from "./session.js";
import { startOutbox } from "./outbox.js";
import { el, errText, icon, initOfflineBanner, mount } from "./ui.js";
import { renderAuth } from "./views/auth.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderHome } from "./views/home.js";
import { renderPinpad } from "./views/pinpad.js";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((e) => console.warn("SW failed", e));
  });
}

initOfflineBanner();

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

// T3.3, docs/design/stitch-export-2/boot_screen/. Loading and error share one
// mount and cross-fade via opacity (not display toggling), so it degrades to
// an instant switch under prefers-reduced-motion rather than losing the
// error state's affordance.
function bootScreen() {
  const loading = el(
    "div",
    { class: "boot-state active" },
    el("div", { class: "spinner", "aria-hidden": "true" }),
    el("p", { class: "muted" }, "טוען…"),
  );
  const errorState = el(
    "div",
    { class: "boot-state" },
    el("p", { class: "err" }, "אין חיבור לשרת."),
    el("button", { class: "btn-link", onclick: boot }, icon("refresh"), " נסה שוב"),
  );
  mount(
    el(
      "div",
      { class: "boot-screen" },
      el("h1", { class: "boot-wordmark" }, "alut4u"),
      el("div", { class: "boot-states" }, loading, errorState),
    ),
  );
  return { loading, errorState };
}

async function boot() {
  const { loading, errorState } = bootScreen();
  try {
    await refresh();
  } catch {
    loading.classList.remove("active");
    errorState.classList.add("active");
    return;
  }
  route();
  startOutbox();
}

boot();
