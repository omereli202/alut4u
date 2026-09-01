// Minimal DOM helpers. No framework.

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === "dataset") Object.assign(node.dataset, v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";
const XLINK_NS = "http://www.w3.org/1999/xlink";

// Bump whenever scripts/build_icons.py regenerates the sprite (also update
// the matching entry in sw.js's SHELL list). frontend/Caddyfile caches
// /assets/* for 7 days (Cache-Control: max-age=604800), and Railway's CDN
// caches it *again* at the edge on top of that, independently per edge node
// — a plain unversioned URL can silently keep serving a week-old sprite to
// some visitors after a deploy, regardless of any client-side cache the
// service worker or browser manage. A version query string is a new URL,
// so every cache layer treats it as a fresh resource instead of revalidating
// a stale one.
const SPRITE_URL = "/assets/icons/sprite.svg?v=41";

// Control glyph from the bundled sprite (frontend/assets/icons/sprite.svg —
// Material Symbols Outlined, see scripts/build_icons.py). Decorative by
// default (aria-hidden) — the usual pattern is an aria-label on the enclosing
// button (see views/home.js's .lock-btn). Pass `label` only when the icon
// stands alone with no other accessible name nearby. Pass `flip: true` for a
// single-direction glyph (arrow_back, backspace) that needs mirroring in RTL —
// see .icon-flip in base.css.
export function icon(name, { label, size, flip } = {}) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", flip ? "icon icon-flip" : "icon");
  // Inline style, not width/height attributes — the [data-mode="user"] CSS
  // rule sets both via a class selector, which beats a presentation attribute.
  if (size) svg.setAttribute("style", `width:${size}px;height:${size}px`);
  if (label) {
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", label);
  } else {
    svg.setAttribute("aria-hidden", "true");
  }
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttributeNS(XLINK_NS, "href", `${SPRITE_URL}#${name}`);
  use.setAttribute("href", `${SPRITE_URL}#${name}`);
  svg.append(use);
  return svg;
}

export function mount(...nodes) {
  const main = document.getElementById("main");
  main.classList.remove("boot"); // shed the initial centering layout
  main.replaceChildren(...nodes.flat().filter(Boolean));
  main.scrollTo?.(0, 0);
  window.scrollTo(0, 0);
  main.focus?.();
}

export function toast(message, kind = "info") {
  const t = el(
    "div",
    { class: `toast toast-${kind}`, role: "status" },
    icon(kind === "error" ? "warning" : "check_circle"),
    el("span", {}, message),
  );
  document.body.append(t);
  setTimeout(() => t.remove(), 4000);
}

// Symbol/photo for a card-like item, with a plain-text fallback (first two
// characters of its label) when it has neither. `cls` sets sizing/shape via
// CSS — shared by the AAC board, schedule and rules cards, which each pass
// their own class rather than duplicating this lookup three times.
export function visual(item, cls) {
  if (item.symbol_id) {
    return el("img", { class: cls, src: `/assets/symbols/${item.symbol_id}.svg`, alt: "" });
  }
  if (item.icon_asset_id) {
    return el("img", { class: cls, src: `/api/media/${item.icon_asset_id}`, alt: "" });
  }
  const text = (item.label ?? item.title ?? "").slice(0, 2);
  return el("div", { class: `${cls} ${cls}-text` }, text);
}

// Offline banner (T3.13) — global, mounted once at startup (see app.js), not
// per-screen, so it survives route() swapping #main's content. navigator's
// online/offline events are the same signal outbox.js's flush-on-reconnect
// already relies on.
export function initOfflineBanner() {
  const banner = el(
    "div",
    { class: "offline-banner", role: "status" },
    icon("wifi_off"),
    el("span", {}, "אין חיבור — חלק מהתכונות לא זמינות"),
  );
  function sync() {
    banner.classList.toggle("visible", !navigator.onLine);
  }
  document.body.prepend(banner);
  window.addEventListener("online", sync);
  window.addEventListener("offline", sync);
  sync();
}

// Empty state (T3.13): centered muted icon + heading + optional line +
// optional back link. `iconName` defaults to "inbox".
export function emptyState({ iconName = "inbox", title, body, onBack, backLabel = "חזרה" } = {}) {
  return el(
    "div",
    { class: "empty-state" },
    icon(iconName, { size: 40 }),
    title && el("h3", {}, title),
    body && el("p", { class: "muted" }, body),
    onBack && el("button", { class: "btn-link", onclick: onBack }, backLabel),
  );
}

// Celebration state (T3.13): filled card, icon in a soft circle, big heading
// + muted line. Used by the schedule "all done today", memory-game win, and
// reading/writing success states so they share one look.
export function celebration({ iconName = "celebration", title, body } = {}) {
  return el(
    "div",
    { class: "celebration-state" },
    el("div", { class: "celebration-icon" }, icon(iconName, { size: 48 })),
    title && el("h2", {}, title),
    body && el("p", {}, body),
  );
}

export function errText(e) {
  const map = {
    invalid_credentials: "אימייל או סיסמה שגויים",
    email_in_use: "כתובת האימייל כבר רשומה",
    pin_incorrect: "קוד שגוי",
    pin_locked: "יותר מדי ניסיונות — נסו שוב בעוד רגע",
    weak_pin: "בחרו קוד פחות צפוי",
    caregiver_mode_required: "צריך להיכנס למצב מטפל",
    rate_limited: "יותר מדי בקשות — נסו שוב מאוחר יותר",
    network: "אין חיבור לרשת",
    validation_error: "הפרטים שהוזנו אינם תקינים",
  };
  return map[e?.code] || e?.body?.detail || "אירעה שגיאה, נסו שוב";
}
