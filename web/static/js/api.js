/* ── Telegram WebApp SDK ── */
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor('#0d0d12');
  tg.setBackgroundColor('#0d0d12');
}

const API = {
  async get(u) {
    const r = await fetch(u);
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  },
  async post(u, b) {
    return (await fetch(u, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(b) })).json();
  },
  async del(u) {
    return (await fetch(u, { method:'DELETE' })).json();
  },
};

function fmt(n) {
  if (n == null) return '—';
  return Math.round(n).toLocaleString('ru-RU');
}
function fmtDate(s) {
  if (!s) return '—';
  return s.replace('T',' ').slice(0,16);
}

const Q_NAME = { '-1':'???', 0:'Обычный', 1:'Необычный', 2:'Особый', 3:'Редкий', 4:'Исключительный', 5:'Легендарный' };
const Q_CSS = { '-1':'q--1', 0:'q-0', 1:'q-1', 2:'q-2', 3:'q-3', 4:'q-4', 5:'q-5' };
function qb(q) { return `<span class="qb ${Q_CSS[q]||''}">${Q_NAME[q]||'?'}</span>`; }
function upg(u) { return u > 0 ? `<span class="upg">+${u}</span>` : ''; }
function haptic(t) { if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(t||'light'); }
