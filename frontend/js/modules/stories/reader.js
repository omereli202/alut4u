// Social-story reader: one page at a time, image + text, read-aloud, page turns.

import { el } from "../../ui.js";

export function renderReader(host, { story, onBack }) {
  let page = 0;
  let audio = null;

  function speak() {
    const url = story.pages[page].audio_url;
    audio?.pause();
    if (url) {
      audio = new Audio(url);
      audio.play().catch(() => {});
    }
  }

  function view() {
    const p = story.pages[page];
    const last = page === story.pages.length - 1;
    return el(
      "div",
      { class: "story-reader" },
      el(
        "div",
        { class: "story-topbar" },
        el("button", { class: "btn-link", onclick: () => { audio?.pause(); onBack(); } }, "✕ סגירה"),
        el("span", { class: "muted" }, `${page + 1} / ${story.pages.length}`),
      ),
      p.image_url
        ? el("img", { class: "story-image", src: p.image_url, alt: "" })
        : el("div", { class: "story-image story-image-blank" }, "📖"),
      el("p", { class: "story-text", onclick: speak }, p.text),
      el(
        "div",
        { class: "story-nav" },
        el(
          "button",
          { class: "sb-btn", disabled: page === 0, onclick: () => go(-1) },
          "→ הקודם",
        ),
        el("button", { class: "sb-btn speak", onclick: speak }, "🔊 הקראה"),
        last
          ? el("button", { class: "sb-btn", onclick: () => { audio?.pause(); onBack(); } }, "✓ סיום")
          : el("button", { class: "sb-btn", onclick: () => go(1) }, "הבא ←"),
      ),
    );
  }

  function go(delta) {
    page = Math.max(0, Math.min(story.pages.length - 1, page + delta));
    render();
    speak();
  }

  function render() {
    host.replaceChildren(view());
  }

  render();
  speak();
}
