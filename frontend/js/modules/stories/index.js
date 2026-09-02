// User Mode: list of finished social stories → reader.

import { api } from "../../api.js";
import { el, emptyState, mount, navBar, toast } from "../../ui.js";
import { renderReader } from "./reader.js";

export async function renderStories({ childId, childName, onExit, onHome }) {
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
        : emptyState({
            iconName: "auto_stories",
            title: "אין עדיין סיפורים.",
            body: "מטפל יכול ליצור סיפור במצב מטפל.",
          }),
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
      navBar({ onBack: onExit, onHome: onHome ?? onExit, title: `הסיפורים של ${childName || ""}` }),
      host,
    ),
  );
  list();
}
