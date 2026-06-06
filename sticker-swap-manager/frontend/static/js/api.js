const API_BASE = '/api';

const Api = {
  _token: null,

  setToken(t) {
    this._token = t;
    if (t) localStorage.setItem('token', t);
    else localStorage.removeItem('token');
  },

  loadToken() {
    this._token = localStorage.getItem('token');
    return this._token;
  },

  async _fetch(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (this._token) headers['Authorization'] = `Bearer ${this._token}`;
    const resp = await fetch(`${API_BASE}${path}`, { ...opts, headers });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || 'Erro desconhecido');
    }
    return resp.json();
  },

  register: (data) => Api._fetch('/users/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => Api._fetch('/users/login', { method: 'POST', body: JSON.stringify(data) }),
  getMe: () => Api._fetch('/users/me'),
  listUsers: () => Api._fetch('/users/'),
  getCatalog: () => Api._fetch('/stickers/catalog'),
  getSections: () => Api._fetch('/stickers/sections'),
  getMyDuplicates: () => Api._fetch('/stickers/my/duplicates'),
  getMyWanted: () => Api._fetch('/stickers/my/wanted'),
  addDuplicate: (number, qty = 1) =>
    Api._fetch('/stickers/my/duplicates', { method: 'POST', body: JSON.stringify({ sticker_number: number, quantity: qty }) }),
  removeDuplicate: (number) =>
    Api._fetch(`/stickers/my/duplicates/${number}`, { method: 'DELETE' }),
  addWanted: (number) =>
    Api._fetch('/stickers/my/wanted', { method: 'POST', body: JSON.stringify({ sticker_number: number }) }),
  removeWanted: (number) =>
    Api._fetch(`/stickers/my/wanted/${number}`, { method: 'DELETE' }),
  getGroupOverview: () => Api._fetch('/stickers/group-overview'),
  generateTrades: () => Api._fetch('/trades/generate', { method: 'POST' }),
};
