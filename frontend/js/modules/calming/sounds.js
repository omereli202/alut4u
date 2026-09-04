// Calming sound player. Bundled loops, no autoplay, one at a time.

import { el, icon } from "../../ui.js";

// Bump when scripts/build_calming.py regenerates the .wav files: they change
// in place, and both the service worker's catch-all cache and Railway's
// per-node /assets/* edge cache would otherwise keep serving the old audio.
const ASSET_V = "20260904";

// Order + labels mirror scripts/build_calming.py's ORDER / index.json.
// rain/waves/wind/hum/tone432 are synthesized; fire/forest/brook/birds are
// real CC0 recordings (frontend/assets/calming/LICENSE.md). All are
// loudness-matched at build time, so `gain` is only for the odd manual trim.
const TRACKS = [
  { slug: "rain", label: "גשם", emoji: "🌧️" },
  { slug: "waves", label: "גלים", emoji: "🌊", gain: 1.0 },
  { slug: "wind", label: "רוח", emoji: "🍃" },
  { slug: "hum", label: "זמזום רגוע", emoji: "🎵", gain: 1.0 },
  { slug: "fire", label: "מדורה", emoji: "🔥" },
  { slug: "forest", label: "יער בגשם", emoji: "🌲" },
  { slug: "brook", label: "פכפוך נחל", emoji: "💧" },
  { slug: "birds", label: "ציפורים", emoji: "🐦" },
  { slug: "tone432", label: "תדר מרגיע", emoji: "〰️" },
];

export function renderSounds(host) {
  let audio = null;
  let playing = null;

  function toggle(track) {
    if (playing === track.slug) {
      audio.pause();
      playing = null;
    } else {
      audio?.pause();
      audio = new Audio(`/assets/calming/${track.slug}.wav?v=${ASSET_V}`);
      audio.loop = true;
      audio.volume = track.gain ?? 0.7;
      audio.play().catch(() => {});
      playing = track.slug;
    }
    render();
  }

  function render() {
    host.replaceChildren(
      el(
        "div",
        { class: "calm-sounds" },
        ...TRACKS.map((t) =>
          el(
            "button",
            {
              class: playing === t.slug ? "calm-sound active" : "calm-sound",
              "aria-pressed": playing === t.slug,
              onclick: () => toggle(t),
            },
            el("span", { class: "calm-emoji" }, t.emoji),
            el("span", {}, t.label),
            // Decorative — the button's aria-pressed + label already carry the
            // state for assistive tech.
            el("span", { class: "calm-state" }, playing === t.slug ? icon("pause") : icon("play_arrow")),
          ),
        ),
      ),
    );
  }

  render();
  return () => audio?.pause(); // cleanup
}
