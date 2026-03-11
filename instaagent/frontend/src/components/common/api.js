// frontend/src/components/common/api.js
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch(path, opts = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.detail || json.message || "Request failed");
  return json;
}

export const api = {
  get:   (path, token)        => apiFetch(path, { method: "GET" }, token),
  patch: (path, body, token)  => apiFetch(path, { method: "PATCH",  body: JSON.stringify(body) }, token),
  post:  (path, body, token)  => apiFetch(path, { method: "POST",   body: JSON.stringify(body) }, token),
  del:   (path, token)        => apiFetch(path, { method: "DELETE" }, token),
};
