// Card audio playback. Audio is pre-generated (see backend tts/cache.py) and
// served from the stable /api/media/<id> URL, which the service worker caches —
// so this works offline. Priority: caregiver audio → pre-generated TTS.

import { symbolUrl } from "../../ui.js";

let current = null;

export function audioUrlFor(card) {
  const id = card.audio_asset_id || card.tts_asset_id;
  return id ? `/api/media/${id}` : null;
}

export async function speak(card) {
  const url = audioUrlFor(card);
  if (!url) return;
  try {
    current?.pause();
    current = new Audio(url);
    current.play().catch(() => {});
  } catch {
    /* autoplay policy or decode error — silently ignore */
  }
}

// Speak a list of cards in sequence (the sentence bar's "speak all").
export async function speakSequence(cards) {
  for (const card of cards) {
    const url = audioUrlFor(card);
    if (!url) continue;
    await new Promise((resolve) => {
      const a = new Audio(url);
      current = a;
      a.onended = a.onerror = resolve;
      a.play().catch(resolve);
    });
  }
}

// Warm the cache so the first tap after load is instant / offline-ready.
export function prefetch(cards) {
  for (const card of cards) {
    const url = audioUrlFor(card);
    if (url) fetch(url, { credentials: "include" }).catch(() => {});
  }
}

// Same, for the symbol images cards render (frontend/sw.js's SYMBOL_CACHE).
// Without this a symbol is only offline-safe by accident of having been
// rendered while online — the board otherwise never warms it up front.
export function prefetchSymbols(cards) {
  for (const card of cards) {
    if (card.symbol_id) fetch(symbolUrl(card.symbol_id), { credentials: "include" }).catch(() => {});
  }
}
