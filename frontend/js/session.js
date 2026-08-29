// Session state — the single source of truth for "who is signed in and in
// which mode". Views read `state`; `refresh()` re-fetches after any auth action.

import { api, ApiError } from "./api.js";

export const state = {
  loaded: false,
  authenticated: false,
  caregiverId: null,
  mode: "user", // "user" | "caregiver"
  onboarding: null, // { needs_pin, needs_terms, voice_consent }
};

export async function refresh() {
  try {
    const s = await api.get("/auth/session");
    Object.assign(state, {
      loaded: true,
      authenticated: true,
      caregiverId: s.caregiver_id,
      mode: s.mode,
      onboarding: s.onboarding,
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      Object.assign(state, {
        loaded: true,
        authenticated: false,
        caregiverId: null,
        mode: "user",
        onboarding: null,
      });
    } else {
      throw e;
    }
  }
  return state;
}

export function applySessionPayload(s) {
  Object.assign(state, {
    loaded: true,
    authenticated: true,
    caregiverId: s.caregiver_id,
    mode: s.mode,
    onboarding: s.onboarding,
  });
}

export async function logout() {
  await api.post("/auth/logout").catch(() => {});
  Object.assign(state, {
    authenticated: false,
    caregiverId: null,
    mode: "user",
    onboarding: null,
  });
}

export async function exitCaregiverMode() {
  await api.del("/auth/pin/elevation").catch(() => {});
  state.mode = "user";
}
