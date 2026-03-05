/* ── Telegram WebApp SDK ── */
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor('#0e0e18');
  tg.setBackgroundColor('#0e0e18');
}

function _authHeaders() {
  const h = {};
  if (tg && tg.initData) h['X-Telegram-InitData'] = tg.initData;
  return h;
}

const API = {
  async get(u) {
    const r = await fetch(u, { headers: _authHeaders() });
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  },
  async post(u, b) {
    const h = { 'Content-Type': 'application/json', ..._authHeaders() };
    return (await fetch(u, { method: 'POST', headers: h, body: JSON.stringify(b) })).json();
  },
  async put(u, b) {
    const h = { 'Content-Type': 'application/json', ..._authHeaders() };
    return (await fetch(u, { method: 'PUT', headers: h, body: JSON.stringify(b) })).json();
  },
  async del(u) {
    return (await fetch(u, { method: 'DELETE', headers: _authHeaders() })).json();
  },
  async upload(u, formData) {
    const h = _authHeaders();
    return (await fetch(u, { method: 'POST', headers: h, body: formData })).json();
  },
};

function fmt(n) {
  if (n == null) return '—';
  return Math.round(n).toLocaleString('ru-RU');
}
function fmtDate(s) {
  if (!s) return '—';
  return s.replace('T', ' ').slice(0, 16);
}

const Q_NAME = { '-1': '???', 0: 'Обычный', 1: 'Необычный', 2: 'Особый', 3: 'Редкий', 4: 'Исключительный', 5: 'Легендарный' };
const Q_CSS = { '-1': 'q--1', 0: 'q-0', 1: 'q-1', 2: 'q-2', 3: 'q-3', 4: 'q-4', 5: 'q-5' };
function qb(q) { return `<span class="qb ${Q_CSS[q] || ''}">${Q_NAME[q] || '?'}</span>`; }
function upg(u) { return u > 0 ? `<span class="upg">+${u}</span>` : ''; }
function haptic(t) { if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(t || 'light'); }

/* ── Current user state ── */
let _me = null;
async function getMe() {
  if (_me) return _me;
  try {
    const d = await API.get('/api/me');
    if (d && d.id) _me = d;
  } catch (e) {}
  return _me;
}

