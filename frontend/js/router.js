// Minimal hash router. Views register a render function; navigation swaps the
// #main contents and moves focus for screen-reader users.

const routes = new Map();
let notFound = () => "<p>לא נמצא</p>";

export function route(path, render) {
  routes.set(path, render);
}

export function setNotFound(render) {
  notFound = render;
}

export function navigate(path) {
  if (location.hash.slice(1) === path) render();
  else location.hash = path;
}

async function render() {
  const path = location.hash.slice(1) || "/";
  const [base] = path.split("?");
  const view = routes.get(base) ?? notFound;
  const main = document.getElementById("main");
  main.setAttribute("aria-busy", "true");
  try {
    const html = await view(new URLSearchParams(path.split("?")[1] ?? ""));
    if (typeof html === "string") main.innerHTML = html;
  } finally {
    main.removeAttribute("aria-busy");
    main.focus?.();
  }
}

export function startRouter() {
  window.addEventListener("hashchange", render);
  render();
}
