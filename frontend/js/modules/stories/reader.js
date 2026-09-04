// Social-story reader: one page at a time, image + text, read-aloud, page turns.

import { el, icon } from "../../ui.js";

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
        el("button", { class: "btn-link", onclick: () => { audio?.pause(); onBack(); } }, icon("close"), " סגירה"),
        el("span", { class: "muted" }, `${page + 1} / ${story.pages.length}`),
      ),
      p.image_url
        ? el("img", { class: "story-image", src: p.image_url, alt: "" })
        : el("div", { class: "story-image story-image-blank" }, icon("menu_book", { size: 64 })),
      page === 0 && story.schedule && el("p", { class: "story-when" }, `מתי: ${story.schedule}`),
      el("p", { class: "story-text", onclick: speak }, p.text),
      el(
        "div",
        { class: "story-nav" },
        el(
          "button",
          { class: "sb-btn", disabled: page === 0, onclick: () => go(-1) },
          icon("chevron_right"),
          " הקודם",
        ),
        el("button", { class: "sb-btn speak", onclick: speak }, icon("volume_up"), " הקראה"),
        last
          ? el(
              "button",
              { class: "sb-btn", onclick: () => { audio?.pause(); onBack(); } },
              icon("check"),
              " סיום",
            )
          : el("button", { class: "sb-btn", onclick: () => go(1) }, "הבא ", icon("chevron_left")),
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
