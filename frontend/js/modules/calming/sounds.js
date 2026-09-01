// Calming sound player. Bundled loops, no autoplay, one at a time.

import { el, icon } from "../../ui.js";

const TRACKS = [
  { slug: "rain", label: "גשם", emoji: "🌧️" },
  { slug: "waves", label: "גלים", emoji: "🌊" },
  { slug: "wind", label: "רוח", emoji: "🍃" },
  { slug: "hum", label: "זמזום רגוע", emoji: "🎵" },
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
      audio = new Audio(`/assets/calming/${track.slug}.wav`);
      audio.loop = true;
      audio.volume = 0.7;
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
