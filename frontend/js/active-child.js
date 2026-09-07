// Which child profile User Mode shows. A per-device preference, chosen by the
// caregiver behind the PIN (Caregiver Mode dashboard) — never by the child.
// localStorage can throw in private mode, so every access is guarded.

const KEY = "alut4u.activeChild";

export function getActiveChildId() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setActiveChildId(id) {
  try {
    localStorage.setItem(KEY, id);
  } catch {
    /* private mode — the choice just won't persist */
  }
}
