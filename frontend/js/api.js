// Single choke point for all network calls. Nothing else in the app calls
// fetch() directly. The session is a HttpOnly cookie, so requests just need
// credentials: "include" — no tokens in JS.

const BASE = "/api";

class ApiError extends Error {
  constructor(status, code, body) {
    super(`${status} ${code}`);
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

async function request(method, path, { body, signal } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      credentials: "include",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e) {
    throw new ApiError(0, "network", { detail: String(e) });
  }

  const payload = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(res.status, payload?.error ?? "http_error", payload);
  }
  return payload;
}

export const api = {
  health: () => request("GET", "/health"),
  get: (p, opts) => request("GET", p, opts),
  post: (p, body, opts) => request("POST", p, { ...opts, body }),
  patch: (p, body, opts) => request("PATCH", p, { ...opts, body }),
  del: (p, opts) => request("DELETE", p, opts),
};

export { ApiError };
