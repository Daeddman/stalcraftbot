/* ── Telegram WebApp SDK ── */
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

/* ── Theme ── */
function _applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('ph_theme', theme);
  if (tg) {
    const bg = theme === 'light' ? '#f2f2f7' : '#0f0f1a';
    try { tg.setHeaderColor(bg); tg.setBackgroundColor(bg); } catch(e) {}
  }
}
(function initTheme() {
  const saved = localStorage.getItem('ph_theme');
  if (saved) _applyTheme(saved);
  else _applyTheme('dark');
})();
function toggleTheme() {
  const cur = document.documentElement.dataset.theme || 'dark';
  _applyTheme(cur === 'dark' ? 'light' : 'dark');
}
function isDark() { return (document.documentElement.dataset.theme || 'dark') === 'dark'; }

/* ── Auth ── */
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

const Q_NAME = { 0: 'Обычный', 1: 'Необычный', 2: 'Особый', 3: 'Редкий', 4: 'Исключительный', 5: 'Легендарный' };
const Q_CSS = { 0: 'q-0', 1: 'q-1', 2: 'q-2', 3: 'q-3', 4: 'q-4', 5: 'q-5' };
function qb(q) { if (q < 0 || q == null) return '<span class="qb q--1">—</span>'; return `<span class="qb ${Q_CSS[q] || ''}">${Q_NAME[q] || '—'}</span>`; }
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

/* ── Pull-to-Refresh ── */
(function initPTR() {
  let startY = 0, pulling = false;
  const app = document.getElementById('app');
  if (!app) return;
  app.addEventListener('touchstart', e => {
    if (app.scrollTop === 0) { startY = e.touches[0].clientY; pulling = true; }
  }, { passive: true });
  app.addEventListener('touchmove', e => {
    if (!pulling) return;
    const diff = e.touches[0].clientY - startY;
    if (diff > 80 && app.scrollTop === 0) {
      pulling = false;
      if (typeof route === 'function') route();
    }
  }, { passive: true });
  app.addEventListener('touchend', () => { pulling = false; }, { passive: true });
})();

/* ── Swipe between tabs ── */
(function initSwipe() {
  let startX = 0, startY = 0;
  const tabs = ['#/', '#/search', '#/market', '#/chat', '#/profile'];
  const app = document.getElementById('app');
  if (!app) return;
  app.addEventListener('touchstart', e => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
  }, { passive: true });
  app.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - startX;
    const dy = e.changedTouches[0].clientY - startY;
    if (Math.abs(dx) < 60 || Math.abs(dy) > Math.abs(dx)) return;
    const cur = location.hash || '#/';
    // Only swipe on main tabs
    const idx = tabs.findIndex(t => cur === t || (t === '#/' && (cur === '' || cur === '#/')));
    if (idx < 0) return;
    if (dx < -60 && idx < tabs.length - 1) { location.hash = tabs[idx + 1]; }
    else if (dx > 60 && idx > 0) { location.hash = tabs[idx - 1]; }
  }, { passive: true });
})();

/* ── Onboarding ── */
function showOnboarding() {
  if (localStorage.getItem('ph_onboard_done')) return;
  const slides = [
    { emoji: '🔍', title: 'Находите предметы', desc: 'Ищите любые предметы из Stalcraft по названию. Проверяйте цены на аукционе в реальном времени.' },
    { emoji: '📊', title: 'Отслеживайте цены', desc: 'Добавляйте предметы в избранное, смотрите графики цен и историю продаж с фильтрами по качеству.' },
    { emoji: '🏪', title: 'Торгуйте', desc: 'Создавайте объявления на маркете, общайтесь с другими игроками в чате.' },
    { emoji: '🚀', title: 'Начните прямо сейчас', desc: 'Всё готово! Используйте поиск чтобы найти свой первый предмет.' },
  ];
  let idx = 0;
  const ov = document.createElement('div');
  ov.className = 'onboard-overlay';
  function renderSlide() {
    const s = slides[idx];
    const isLast = idx === slides.length - 1;
    ov.innerHTML = `
      <div class="onboard-slide">
        <div class="onboard-emoji">${s.emoji}</div>
        <div class="onboard-title">${s.title}</div>
        <div class="onboard-desc">${s.desc}</div>
        <div class="onboard-dots">${slides.map((_, i) => `<div class="onboard-dot${i === idx ? ' act' : ''}"></div>`).join('')}</div>
        <button class="onboard-btn" id="ob-next">${isLast ? '🚀 Начать' : 'Далее →'}</button>
        ${!isLast ? '<button class="onboard-skip" id="ob-skip">Пропустить</button>' : ''}
      </div>
    `;
    ov.querySelector('#ob-next').onclick = () => {
      if (isLast) { localStorage.setItem('ph_onboard_done', '1'); ov.remove(); }
      else { idx++; renderSlide(); }
    };
    const skip = ov.querySelector('#ob-skip');
    if (skip) skip.onclick = () => { localStorage.setItem('ph_onboard_done', '1'); ov.remove(); };
  }
  renderSlide();
  document.body.appendChild(ov);
}

/* ── Skeleton generators ── */
function skelRows(n) {
  let h = '<div class="skel card">';
  for (let i = 0; i < n; i++) {
    h += '<div class="skel-row"><div class="skel-circle"></div><div class="skel-lines"><div class="skel-line"></div><div class="skel-line skel-line-short"></div></div></div>';
  }
  return h + '</div>';
}
function skelCards(n) {
  let h = '';
  for (let i = 0; i < n; i++) {
    h += '<div class="skel skel-card"><div class="skel-line" style="height:14px;width:70%;margin-bottom:8px"></div><div class="skel-line" style="height:20px;width:40%"></div></div>';
  }
  return h;
}
function skelBlock() {
  return '<div class="skel"><div class="skel-block"></div></div>';
}

/* ── Fav animation ── */
function favAnim(x, y) {
  const el = document.createElement('div');
  el.className = 'fav-anim';
  el.textContent = '⭐';
  el.style.left = (x || window.innerWidth / 2 - 16) + 'px';
  el.style.top = (y || window.innerHeight / 2 - 16) + 'px';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 700);
}
