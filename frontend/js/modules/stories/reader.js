// Social-story reader: one page at a time, image + text, read-aloud, page turns.
//
// `autoplay` is the caregiver preference (stories_autoplay). When true, a page
// is spoken automatically on open and on every page turn; when false the child
// taps "הקראה" (or the text) to hear it. The manual triggers always work.

import { playUrl, stopAudio } from "../../audio.js";
import { el, icon } from "../../ui.js";

export function renderReader(host, { story, autoplay = true, onBack }) {
  let page = 0;

  function speak() {
    playUrl(story.pages[page].audio_url);
  }

  function close() {
    stopAudio();
    onBack();
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
        el("button", { class: "btn-link", onclick: close }, icon("close"), " סגירה"),
        el("span", { class: "muted" }, `${page + 1} / ${story.pages.length}`),
      ),
      p.image_url
        ? el("img", { class: "story-image", src: p.image_url, alt: "" })
        : el("div", { class: "story-image story-image-blank" }, icon("menu_book", { size: 64 })),
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
          ? el("button", { class: "sb-btn", onclick: close }, icon("check"), " סיום")
          : el("button", { class: "sb-btn", onclick: () => go(1) }, "הבא ", icon("chevron_left")),
      ),
    );
  }

  function go(delta) {
    page = Math.max(0, Math.min(story.pages.length - 1, page + delta));
    render();
    if (autoplay) speak();
  }

  function render() {
    host.replaceChildren(view());
  }

  render();
  if (autoplay) speak();
}
