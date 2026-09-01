// User Mode: list of finished social stories → reader.

import { api } from "../../api.js";
import { el, icon, mount, toast } from "../../ui.js";
import { renderReader } from "./reader.js";

export async function renderStories({ childId, childName, onExit }) {
  let stories = [];
  try {
    stories = (await api.get(`/stories?child_id=${encodeURIComponent(childId)}`)).stories;
  } catch {
    toast("לא ניתן לטעון", "error");
  }

  const host = el("div", { class: "stories-host" });

  function list() {
    host.replaceChildren(
      stories.length
        ? el(
            "div",
            { class: "story-list" },
            ...stories.map((s) =>
              el(
                "button",
                { class: "story-card", onclick: () => open(s.id) },
                el("span", { class: "story-emoji" }, "📖"),
                el("span", {}, s.title),
              ),
            ),
          )
        : el("p", { class: "muted" }, "אין עדיין סיפורים. מטפל יכול ליצור סיפור במצב מטפל."),
    );
  }

  async function open(id) {
    try {
      const story = await api.get(`/stories/${id}`);
      renderReader(host, { story, onBack: list });
    } catch {
      toast("לא ניתן לפתוח את הסיפור", "error");
    }
  }

  mount(
    el(
      "section",
      { class: "stories", "data-mode": "user" },
      el(
        "div",
        { class: "aac-topbar" },
        el("button", { class: "lock-btn", "aria-label": "יציאה", onclick: onExit }, icon("close")),
        el("h1", { class: "aac-title" }, `הסיפורים של ${childName || ""}`),
      ),
      host,
    ),
  );
  list();
}
