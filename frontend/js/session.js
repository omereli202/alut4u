// Session state — the single source of truth for "who is signed in and in
// which mode". Views read `state`; `refresh()` re-fetches after any auth action.

import { api, ApiError } from "./api.js";
import { kv } from "./db.js";

const SNAPSHOT_KEY = "session-snapshot";

export const state = {
  loaded: false,
  authenticated: false,
  caregiverId: null,
  mode: "user", // "user" | "caregiver"
  onboarding: null, // { needs_pin, needs_terms, voice_consent }
  offline: false, // true when hydrated from a cached snapshot, not the server
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
      offline: false,
    });
    // Caregiver Mode is a server-verified PIN elevation (CLAUDE.md #7) — never
    // persist it into the offline snapshot, only the user-mode facts.
    kv.set(SNAPSHOT_KEY, { caregiverId: s.caregiver_id, onboarding: s.onboarding }).catch(() => {});
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      Object.assign(state, {
        loaded: true,
        authenticated: false,
        caregiverId: null,
        mode: "user",
        onboarding: null,
        offline: false,
      });
      kv.del(SNAPSHOT_KEY).catch(() => {});
    } else if (e instanceof ApiError && e.status === 0) {
      // Network failure (offline) — fall back to the last-known session so
      // the app can still boot into User Mode. Caregiver Mode always needs a
      // live PIN check, so mode is forced to "user" regardless of what was
      // last recorded.
      const snapshot = await kv.get(SNAPSHOT_KEY).catch(() => null);
      if (!snapshot) throw e;
      Object.assign(state, {
        loaded: true,
        authenticated: true,
        caregiverId: snapshot.caregiverId,
        mode: "user",
        onboarding: snapshot.onboarding,
        offline: true,
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
    offline: false,
  });
  kv.set(SNAPSHOT_KEY, { caregiverId: s.caregiver_id, onboarding: s.onboarding }).catch(() => {});
}

export async function logout() {
  await api.post("/auth/logout").catch(() => {});
  Object.assign(state, {
    authenticated: false,
    caregiverId: null,
    mode: "user",
    onboarding: null,
    offline: false,
  });
  kv.del(SNAPSHOT_KEY).catch(() => {});
}

export async function exitCaregiverMode() {
  await api.del("/auth/pin/elevation").catch(() => {});
  state.mode = "user";
}
