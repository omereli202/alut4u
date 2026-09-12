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

async function toResult(res) {
  const payload = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(res.status, payload?.error ?? "http_error", payload);
  }
  return payload;
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
  return toResult(res);
}

// Multipart upload — request() is JSON-only (it always sets Content-Type and
// JSON.stringifies the body), so media uploads (a file plus a few plain
// fields) go through here instead. No Content-Type header: the browser sets
// the multipart boundary itself.
async function upload(path, fields, file) {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.append(k, v);
  fd.append("file", file);

  let res;
  try {
    res = await fetch(BASE + path, { method: "POST", credentials: "include", body: fd });
  } catch (e) {
    throw new ApiError(0, "network", { detail: String(e) });
  }
  return toResult(res);
}

export const api = {
  health: () => request("GET", "/health"),
  get: (p, opts) => request("GET", p, opts),
  post: (p, body, opts) => request("POST", p, { ...opts, body }),
  put: (p, body, opts) => request("PUT", p, { ...opts, body }),
  patch: (p, body, opts) => request("PATCH", p, { ...opts, body }),
  del: (p, body, opts) => request("DELETE", p, { ...opts, body }),
  upload,
};

export { ApiError };
