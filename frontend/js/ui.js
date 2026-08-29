// Minimal DOM helpers. No framework.

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === "dataset") Object.assign(node.dataset, v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

export function mount(...nodes) {
  const main = document.getElementById("main");
  main.classList.remove("boot"); // shed the initial centering layout
  main.replaceChildren(...nodes.flat().filter(Boolean));
  main.scrollTo?.(0, 0);
  window.scrollTo(0, 0);
  main.focus?.();
}

export function toast(message, kind = "info") {
  const t = el("div", { class: `toast toast-${kind}`, role: "status" }, message);
  document.body.append(t);
  setTimeout(() => t.remove(), 4000);
}

export function errText(e) {
  const map = {
    invalid_credentials: "אימייל או סיסמה שגויים",
    email_in_use: "כתובת האימייל כבר רשומה",
    pin_incorrect: "קוד שגוי",
    pin_locked: "יותר מדי ניסיונות — נסו שוב בעוד רגע",
    weak_pin: "בחרו קוד פחות צפוי",
    caregiver_mode_required: "צריך להיכנס למצב מטפל",
    rate_limited: "יותר מדי בקשות — נסו שוב מאוחר יותר",
    network: "אין חיבור לרשת",
    validation_error: "הפרטים שהוזנו אינם תקינים",
  };
  return map[e?.code] || e?.body?.detail || "אירעה שגיאה, נסו שוב";
}
