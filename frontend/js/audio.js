// A single shared <Audio> element, plus a one-time "unlock" so playback that
// doesn't start inside a click still works.
//
// The story reader speaks the first page right after `await api.get(...)`, i.e.
// off the user-gesture chain, so a fresh `new Audio().play()` there is blocked
// by the browser's autoplay policy (iOS Safari especially) and fails silently.
// Playing one silent clip from the first real gesture (wired up in app.js)
// marks this element "allowed", and every later playUrl() on it is permitted.
//
// AAC card audio (modules/aac/speech.js) always plays straight from a tap, so
// it doesn't need this and is left alone.

// ~8ms of silence (mono 16-bit PCM, 8kHz) — just enough for a valid decode.
const SILENCE =
  "data:audio/wav;base64,UklGRqQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==";

let element = null;
let unlocked = false;

function ensure() {
  if (!element) element = new Audio();
  return element;
}

// Call from the first pointerdown / keydown. Idempotent.
export function unlockAudio() {
  if (unlocked) return;
  unlocked = true;
  const a = ensure();
  try {
    a.src = SILENCE;
    const p = a.play();
    if (p) p.then(() => a.pause()).catch(() => {});
  } catch {
    /* ignore — a later real play() may still succeed */
  }
}

export function playUrl(url) {
  if (!url) return;
  const a = ensure();
  try {
    a.pause();
    a.src = url;
    a.currentTime = 0;
    a.play().catch(() => {});
  } catch {
    /* autoplay policy or decode error — silently ignore */
  }
}

export function stopAudio() {
  if (element) element.pause();
}
