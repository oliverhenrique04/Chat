// ===== API fixa no seu IP =====
const API_ROOT = 'http://10.9.1.53:3001';
const API_BASE = `${API_ROOT}/api`;

export function getToken() { return localStorage.getItem('token'); }
export function setToken(t) { if (t) localStorage.setItem('token', t); else localStorage.removeItem('token'); }

export async function request(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!options.noJson) headers['Content-Type'] = 'application/json';

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await res.text().catch(() => '');
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = text; }

  if (!res.ok) {
    const msg = payload?.detail || payload?.error || (typeof payload === 'string' ? payload : `HTTP ${res.status}`);
    throw new Error(msg);
  }
  return typeof payload === 'string' ? payload : (payload ?? {});
}

export async function uploadImage(file) {
  const token = getToken();
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers: { 'Authorization': token ? `Bearer ${token}` : '' },
    body: fd,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { url, type, mime }
}

export const api = {
  register: (n,e,p) => request('/register', { method:'POST', body: JSON.stringify({ name:n, email:e, password:p }) }),
  login: (e,p) => request('/login', { method:'POST', body: JSON.stringify({ email:e, password:p }) }),
  me: () => request('/me'),
  rooms: () => request('/rooms'),
  createRoom: (name) => request('/rooms', { method:'POST', body: JSON.stringify({ name }) }),
  joinRoom: (roomId) => request(`/rooms/${roomId}/join`, { method:'POST' }),
  leaveRoom: (roomId) => request(`/rooms/${roomId}/leave`, { method:'POST' }),
  roomMessages: (roomId) => request(`/messages/room/${roomId}`),
  dmMessages: (userId) => request(`/messages/dm/${userId}`),
  findUserByEmail: (email) => request(`/users/find?email=${encodeURIComponent(email)}`),
  activeCount: () => request('/active-count'),
  // DMs salvas:
  dmList: () => request('/dm/list'),
  dmAdd: (email) => request(`/dm/add?email=${encodeURIComponent(email)}`, { method:'POST' }),
  dmRemove: (id) => request(`/dm/remove/${id}`, { method:'POST' }),
};

// Exporto a raiz para o chat.js (socket + imagens)
export const API_ROOT_URL = API_ROOT;
