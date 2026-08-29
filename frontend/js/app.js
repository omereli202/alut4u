// Entry point. Phase 0: register the service worker, boot the router, show a
// placeholder home view and a live health read so the deploy is visibly working.

import { api } from "./api.js";
import { route, startRouter } from "./router.js";
import { startOutbox } from "./outbox.js";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((e) => console.warn("SW failed", e));
  });
}

route("/", async () => {
  let status = "לא ידוע";
  try {
    const h = await api.health();
    status = `${h.status} · ${h.env} · ${h.version}`;
  } catch {
    status = "לא מקוון";
  }
  return `
    <section class="home">
      <h1>alut4u</h1>
      <p>שלד היישום (שלב 0). המודולים ייווספו בהמשך.</p>
      <p class="status" dir="ltr">API: ${status}</p>
    </section>
  `;
});

document.body.dataset.mode = "user";
startRouter();
startOutbox();
