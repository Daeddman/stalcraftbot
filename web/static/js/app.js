/* ═══════════════════════════════════════════
   PerekupHelper SPA — v3 fixed
   ═══════════════════════════════════════════ */
const A = document.getElementById('app');
function go(h) { location.hash = h; }

/* ── State ── */
let S = { catPP: 20, lotPP: 15, salePP: 15 };
try { const s = JSON.parse(localStorage.getItem('ph_s') || '{}'); Object.assign(S, s); } catch (e) {}
function saveS() { localStorage.setItem('ph_s', JSON.stringify(S)); }

/* ── Cache (5min TTL) ── */
const _cache = new Map();
function cGet(k) { const e = _cache.get(k); if (e && Date.now() - e.t < 300000) return e.v; return null; }
function cSet(k, v) { _cache.set(k, { v, t: Date.now() }); }

/* ── Toast ── */
let _toastEl;
function toast(msg) {
  if (!_toastEl) { _toastEl = document.createElement('div'); _toastEl.className = 'toast'; document.body.appendChild(_toastEl); }
  _toastEl.textContent = msg; _toastEl.classList.add('show');
  setTimeout(() => _toastEl.classList.remove('show'), 2200);
}

/* ── Render wrapper ── */
function render(html) { A.innerHTML = '<div class="page">' + html + '</div>'; A.scrollTop = 0; }

/* ── Router ── */
async function route() {
  const h = location.hash || '#/', p = h.replace('#', '').split('/').filter(Boolean), pg = p[0] || '';
  document.querySelectorAll('.tab').forEach(t => {
    const r = t.dataset.route;
    t.classList.toggle('active', r === h || (r === '#/' && h === '#/') || (r === '#/catalog' && pg === 'catalog'));
  });
  if (tg && pg) { tg.BackButton.show(); tg.BackButton.onClick(() => history.back()); }
  else if (tg) { tg.BackButton.hide(); }
  try {
    if (!pg || h === '#/') await P_home();
    else if (pg === 'catalog' && p.length === 1) await P_catalog();
    else if (pg === 'catalog') await P_cat(p.slice(1).join('/'));
    else if (pg === 'item') await P_item(p[1]);
    else if (pg === 'auction') await P_auc(p[1]);
    else if (pg === 'search') P_search();
    else if (pg === 'tracked') await P_tracked();
    else await P_home();
  } catch (e) {
    render('<div class="empty"><div class="empty-i">⚠️</div><div class="empty-t">' + e.message + '</div></div>');
  }
  if (tg) tg.expand();
}
window.addEventListener('hashchange', route);
window.addEventListener('load', route);

/* ═══════════ HOME ═══════════ */
async function P_home() {
  render('<div class="ld">Загрузка</div>');
  const ck = cGet('cats');
  const [cats, tr] = await Promise.all([ck ? Promise.resolve(ck) : API.get('/api/categories'), API.get('/api/tracked')]);
  if (!ck) cSet('cats', cats);
  const tot = cats.reduce((s, c) => s + c.count, 0);
  let h = '';
  h += '<div class="banner"><div class="banner-title">⚡ PerekupHelper</div><div class="banner-sub">Мониторинг аукциона Stalcraft</div></div>';
  h += '<div class="sgrid"><div class="sbox"><div class="sv">' + fmtK(tot) + '</div><div class="sl">Предметов</div></div>';
  h += '<div class="sbox"><div class="sv">' + tr.length + '</div><div class="sl">Отслеживается</div></div></div>';
  if (tr.length) {
    h += '<div class="sec">Отслеживаемые</div><div class="hscroll">';
    for (const t of tr) {
      h += '<div class="hcard" onclick="haptic();go(\'#/item/' + t.item_id + '\')">';
      h += '<div class="hcard-img">' + ICO(t.icon) + '</div>';
      h += '<div class="hcard-name">' + t.name + '</div>';
      h += '<div class="hcard-price">' + (t.avg_24h ? fmt(t.avg_24h) + ' ₽' : '—') + '</div></div>';
    }
    h += '</div>';
    if (tr.length > 4) h += '<div style="text-align:center;margin:4px 0 8px"><a class="back" href="#/tracked" style="color:var(--acc)">Все ' + tr.length + ' предметов →</a></div>';
  }
  h += '<div class="sec">Каталог</div><div class="cgrid">';
  for (const c of cats.slice(0, 8)) {
    h += '<div class="cbtn" onclick="haptic();go(\'#/catalog/' + c.id + '\')"><div class="ce">' + CE(c.id) + '</div><div class="cl">' + CN(c.name) + '</div><div class="cc">' + c.count + ' шт.</div></div>';
  }
  if (cats.length > 8) h += '<div class="cbtn" onclick="go(\'#/catalog\')"><div class="ce">📂</div><div class="cl">Все категории</div><div class="cc">' + cats.length + '</div></div>';
  h += '</div>';
  render(h);
}

/* ═══════════ CATALOG ═══════════ */
async function P_catalog() {
  render('<div class="ld">Загрузка</div>');
  const ck = cGet('cats');
  const cats = ck || await API.get('/api/categories');
  if (!ck) cSet('cats', cats);
  let h = '<div class="hdr">📦 Каталог</div><div class="sub">' + cats.reduce((s, c) => s + c.count, 0) + ' предметов в ' + cats.length + ' категориях</div><div class="cgrid">';
  for (const c of cats) {
    h += '<div class="cbtn" onclick="haptic();go(\'#/catalog/' + c.id + '\')"><div class="ce">' + CE(c.id) + '</div><div class="cl">' + CN(c.name) + '</div><div class="cc">' + c.count + ' шт.</div></div>';
  }
  h += '</div>';
  render(h);
}

/* ═══════════ CATEGORY ═══════════ */
async function P_cat(cat, pg) {
  pg = pg || 1;
  render('<div class="ld">Загрузка</div>');
  const ck = cGet('cats');
  const allC = ck || await API.get('/api/categories');
  if (!ck) cSet('cats', allC);
  const par = allC.find(c => c.id === cat);
  if (par && par.children && par.children.length) {
    let h = '<a class="back" href="#/catalog">← Каталог</a>';
    h += '<div class="hdr">' + CE(cat) + ' ' + CN(par.name) + '</div><div class="sub">' + par.count + ' предметов</div><div class="cgrid">';
    for (const s of par.children) h += '<div class="cbtn" onclick="haptic();go(\'#/catalog/' + s.id + '\')"><div class="ce">' + CE(s.id) + '</div><div class="cl">' + CN(s.name) + '</div><div class="cc">' + s.count + ' шт.</div></div>';
    h += '</div>';
    render(h); return;
  }
  const pp = S.catPP, d = await API.get('/api/categories/' + cat + '/items?page=' + pg + '&per_page=' + pp);
  const bk = cat.includes('/') ? cat.split('/').slice(0, -1).join('/') : '';
  _ppCtx.cat = cat;
  let h = '<a class="back" href="' + (bk ? '#/catalog/' + bk : '#/catalog') + '">← Назад</a>';
  h += '<div class="hdr">' + (d.items[0] ? d.items[0].category_name : cat) + '</div><div class="sub">' + d.total + ' предметов</div>';
  h += PP(S.catPP, [10, 20, 50, 100], 'cat');
  h += '<div class="card">';
  for (const i of d.items) h += R(i.id, i.icon, i.name, '', i.color, null, i.api_supported);
  h += '</div>';
  if (d.pages > 1) h += PG(pg, d.pages, function(p) { return "P_cat('" + cat + "'," + p + ")"; });
  render(h);
}

/* ═══════════ ITEM ═══════════ */
async function P_item(id) {
  render('<div class="ld">Загрузка</div>');
  const [item, tr] = await Promise.all([API.get('/api/items/' + id), API.get('/api/tracked')]);
  if (item.error) { render('<div class="empty"><div class="empty-i">❌</div><div class="empty-t">Предмет не найден</div></div>'); return; }
  const isTr = tr.some(t => t.item_id === id);
  const apiOk = item.api_supported !== false;
  let h = '<a class="back" onclick="history.back()">← Назад</a>';
  h += '<div class="hero"><div class="hero-img">' + ICO(item.icon) + '</div><div class="hero-r"><div class="hero-t rk-' + item.color + '"><span class="in">' + item.name + '</span></div><div class="hero-s">' + item.category_name + '</div></div></div>';

  if (apiOk) {
    h += '<div class="pblk"><div class="pt">💰 Цены</div>';
    if (item.is_artefact && item.quality_breakdown.length) {
      for (const b of item.quality_breakdown) h += '<div class="pr"><span class="pl">' + qb(b.quality) + upg(b.upgrade_level) + '</span><span class="pv">' + fmt(b.avg_price) + ' ₽ <small style="color:var(--t3)">(' + b.count + ')</small></span></div>';
    } else if (item.prices.avg_24h || item.prices.avg_7d) {
      if (item.prices.avg_24h) h += '<div class="pr"><span class="pl">Средняя 24ч</span><span class="pv">' + fmt(item.prices.avg_24h) + ' ₽</span></div>';
      if (item.prices.avg_7d) h += '<div class="pr"><span class="pl">Средняя 7д</span><span class="pv">' + fmt(item.prices.avg_7d) + ' ₽</span></div>';
    } else { h += '<div class="pr"><span class="pl" style="opacity:.5">Добавь в отслеживание для сбора цен</span></div>'; }
    h += '</div>';
  } else {
    h += '<div class="warn-box"><span class="warn-icon">⚠️</span><div class="warn-text"><b>Аукцион недоступен</b><br>Этот предмет не поддерживается официальным API Stalcraft. Данные по ценам и лотам отсутствуют.</div></div>';
  }

  h += '<div class="bgrp">';
  if (apiOk) {
    if (isTr) h += '<button class="btn btn-r" onclick="haptic(\'medium\');UT(\'' + id + '\')">✕ Убрать</button>';
    else h += '<button class="btn btn-g" onclick="haptic(\'medium\');TK(\'' + id + '\')">📌 Отслеживать</button>';
    h += '<a class="btn btn-o" href="#/auction/' + id + '" onclick="haptic()">📊 Лоты</a>';
  }
  h += '</div>';

  if (item.stats && item.stats.length) {
    h += '<div class="sec">Характеристики</div><div class="card" style="padding:10px 12px"><div class="stl">';
    for (const s of item.stats) { let c = ''; if (s.color === '53C353') c = 'sg'; else if (s.color === 'C15252') c = 'sr'; h += '<div class="str"><span class="stk">' + s.key + '</span><span class="stv ' + c + '">' + s.value + '</span></div>'; }
    h += '</div></div>';
  }
  render(h);
}
async function TK(id) { await API.post('/api/tracked', { item_id: id }); toast('📌 Добавлено'); P_item(id); }
async function UT(id) { await API.del('/api/tracked/' + id); toast('✕ Убрано'); P_item(id); }

/* ═══════════ AUCTION ═══════════ */
async function P_auc(id, lp, sp) {
  lp = lp || 1; sp = sp || 1;
  render('<div class="ld">Загрузка лотов</div>');

  const item = await API.get('/api/items/' + id);
  if (item.api_supported === false) {
    let h = '<a class="back" href="#/item/' + id + '">← ' + (item.name || id) + '</a>';
    h += '<div class="hdr">📊 Аукцион</div>';
    h += '<div class="warn-box"><span class="warn-icon">⚠️</span><div class="warn-text"><b>Аукцион недоступен</b><br>Этот предмет не поддерживается официальным API Stalcraft.<br>Данные по ценам и лотам отсутствуют.</div></div>';
    render(h);
    return;
  }

  const lOff = (lp - 1) * S.lotPP, sOff = (sp - 1) * S.salePP;
  const [ld, hd, pd] = await Promise.all([
    API.get('/api/auction/' + id + '/lots?limit=' + S.lotPP + '&offset=' + lOff),
    API.get('/api/auction/' + id + '/history?limit=' + S.salePP + '&offset=' + sOff),
    API.get('/api/auction/' + id + '/prices'),
  ]);
  const lots = ld.lots || [], sales = hd.prices || [], isA = item.is_artefact, nm = item.name || id;
  const lTotal = ld.total || 0, sTotal = hd.total || 0;
  const lPages = Math.ceil(lTotal / S.lotPP) || 1, sPages = Math.ceil(sTotal / S.salePP) || 1;
  _ppCtx.aucId = id; _ppCtx.lp = lp; _ppCtx.sp = sp;
  let h = '<a class="back" href="#/item/' + id + '">← ' + nm + '</a>';
  h += '<div class="hdr">📊 Аукцион</div><div class="sub">' + nm + '</div>';
  if (pd.breakdown && pd.breakdown.length) {
    h += '<div class="pblk"><div class="pt">Средние цены (7д)</div>';
    for (const b of pd.breakdown) h += '<div class="pr"><span class="pl">' + qb(b.quality) + upg(b.upgrade_level) + '</span><span class="pv">' + fmt(b.avg_price) + ' / ' + fmt(b.min_price) + ' ₽</span></div>';
    h += '</div>';
  }
  h += '<div class="sec">Активные лоты (' + lTotal + ')</div>';
  h += PP(S.lotPP, [10, 15, 25, 50], 'lot');
  if (lots.length) {
    h += '<div class="card"><div class="tw"><table class="lt"><thead><tr><th>Цена</th><th>Тип</th>' + (isA ? '<th>Качество</th>' : '') + '<th>До</th></tr></thead><tbody>';
    for (const l of lots) {
      const pr = l.buyoutPrice || l.currentPrice || l.startPrice || 0;
      const tp = l.buyoutPrice > 0 ? 'Выкуп' : 'Ставка';
      const tm = fmtDate(l.endTime);
      let qc = '';
      if (isA && l.additional) { const q = l.additional.qlt != null ? l.additional.qlt : -1, u = Math.round((l.additional.upgrade_bonus || 0) * 20); qc = '<td>' + qb(q) + upg(u) + '</td>'; }
      h += '<tr><td class="lp">' + fmt(pr) + ' ₽</td><td>' + tp + '</td>' + (isA ? (qc || '<td>—</td>') : '') + '<td class="ld">' + tm + '</td></tr>';
    }
    h += '</tbody></table></div></div>';
    if (lPages > 1) h += PG(lp, lPages, function(p) { return "P_auc('" + id + "'," + p + "," + sp + ")"; });
  } else { h += '<div class="empty"><div class="empty-i">📭</div><div class="empty-t">Нет активных лотов</div></div>'; }
  h += '<div class="sec">Последние продажи (' + sTotal + ')</div>';
  h += PP(S.salePP, [10, 15, 25, 50], 'sale');
  if (sales.length) {
    h += '<div class="card"><div class="tw"><table class="lt"><thead><tr><th>Цена</th>' + (isA ? '<th>Качество</th>' : '') + '<th>Дата</th></tr></thead><tbody>';
    for (const s of sales) {
      const tm = fmtDate(s.time);
      let qc = '';
      if (isA && s.additional) { const q = s.additional.qlt != null ? s.additional.qlt : -1, u = Math.round((s.additional.upgrade_bonus || 0) * 20); qc = '<td>' + qb(q) + upg(u) + '</td>'; }
      h += '<tr><td class="lp">' + fmt(s.price) + ' ₽</td>' + (isA ? (qc || '<td>—</td>') : '') + '<td class="ld">' + tm + '</td></tr>';
    }
    h += '</tbody></table></div></div>';
    if (sPages > 1) h += PG(sp, sPages, function(p) { return "P_auc('" + id + "'," + lp + "," + p + ")"; });
  } else { h += '<div class="empty"><div class="empty-i">📭</div><div class="empty-t">Нет данных о продажах</div></div>'; }
  h += '<button class="btn btn-o" style="margin-top:10px" onclick="P_auc(\'' + id + '\',' + lp + ',' + sp + ')">🔄 Обновить</button>';
  render(h);
}

/* ═══════════ SEARCH ═══════════ */
let _st;
function P_search() {
  render('<div class="hdr">🔍 Поиск</div><div class="sub">Поиск предметов по названию</div><div class="srch"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><input id="si" placeholder="Введите название..." autofocus></div><div id="sr"></div>');
  const si = document.getElementById('si');
  if (si) si.addEventListener('input', function(e) { clearTimeout(_st); _st = setTimeout(function() { DS(e.target.value); }, 200); });
}
async function DS(q) {
  const b = document.getElementById('sr'); if (!b) return;
  if (q.trim().length < 1) { b.innerHTML = ''; return; }
  b.innerHTML = '<div class="ld">Поиск...</div>';
  try {
    const it = await API.get('/api/search?q=' + encodeURIComponent(q) + '&limit=30');
    if (!it.length) { b.innerHTML = '<div class="empty"><div class="empty-i">🤷</div><div class="empty-t">Ничего не найдено</div></div>'; return; }
    let h = '<div class="card">'; for (const i of it) h += R(i.id, i.icon, i.name, i.category_name, i.color, null, i.api_supported); h += '</div>'; b.innerHTML = h;
  } catch (e) { b.innerHTML = '<div class="empty"><div class="empty-i">⚠️</div><div class="empty-t">Ошибка поиска</div></div>'; }
}

/* ═══════════ TRACKED ═══════════ */
async function P_tracked() {
  render('<div class="ld">Загрузка</div>');
  const tr = await API.get('/api/tracked');
  let h = '<div class="hdr">⭐ Избранное</div><div class="sub">' + tr.length + ' предметов отслеживается</div>';
  if (!tr.length) {
    h += '<div class="empty"><div class="empty-i">📭</div><div class="empty-t">Пока ничего не отслеживается</div><button class="btn btn-g" style="margin:16px auto 0;width:auto;padding:12px 28px" onclick="go(\'#/catalog\')">Перейти в каталог</button></div>';
  } else {
    h += '<div class="card">'; for (const t of tr) h += R(t.item_id, t.icon, t.name, '', t.color, t.avg_24h, t.api_supported); h += '</div>';
  }
  render(h);
}

/* ═══════════ HELPERS ═══════════ */
function ICO(src) {
  if (!src || src === '/icons/' || src === '') return '<div class="no-icon">📦</div>';
  return '<img src="' + src + '" onerror="this.parentElement.innerHTML=\'<div class=\\\'no-icon\\\'>📦</div>\'" loading="lazy">';
}
function R(id, icon, name, tag, color, price, apiSupported) {
  const p = price ? '<div class="ip">' + fmt(price) + ' ₽</div>' : '';
  const noApi = (apiSupported === false) ? '<span class="badge-wiki" title="Не поддерживается API">wiki</span>' : '';
  return '<div class="irow rk-' + (color || 'DEFAULT') + '" onclick="haptic();go(\'#/item/' + id + '\')"><div class="irow-icon">' + ICO(icon) + '</div><div class="ib"><div class="in">' + name + noApi + '</div>' + (tag ? '<div class="it">' + tag + '</div>' : '') + '</div>' + p + '</div>';
}
function PG(cur, tot, fn) {
  return '<div class="pgr"><button ' + (cur <= 1 ? 'disabled' : '') + ' onclick="' + fn(cur - 1) + '">‹</button><span class="pi">' + cur + ' / ' + tot + '</span><button ' + (cur >= tot ? 'disabled' : '') + ' onclick="' + fn(cur + 1) + '">›</button></div>';
}
function PP(cur, opts, key) {
  let h = '<div class="pps"><span>На странице:</span>';
  for (let i = 0; i < opts.length; i++) { const v = opts[i]; const a = v === cur ? 'act' : ''; h += '<button class="' + a + '" onclick="setPP(\'' + key + '\',' + v + ')">' + v + '</button>'; }
  return h + '</div>';
}
let _ppCtx = {};
function setPP(key, val) {
  if (key === 'cat') { S.catPP = val; saveS(); if (_ppCtx.cat) P_cat(_ppCtx.cat, 1); }
  else if (key === 'lot') { S.lotPP = val; saveS(); if (_ppCtx.aucId) P_auc(_ppCtx.aucId, 1, _ppCtx.sp || 1); }
  else if (key === 'sale') { S.salePP = val; saveS(); if (_ppCtx.aucId) P_auc(_ppCtx.aucId, _ppCtx.lp || 1, 1); }
}
const CE_MAP = { weapon: '⚔️', armor: '🛡', artefact: '💎', attachment: '🔧', bullet: '🔫', containers: '📦', medicine: '💊', food: '🍖', drink: '🥤', other: '📦', grenade: '💣', backpacks: '🎒', misc: '🔮', weapon_modules: '⚙️', weapon_style: '🎨', armor_style: '🎨', device: '📡', consumables: '💉' };
function CE(id) { return CE_MAP[id.split('/')[0]] || '📁'; }
function CN(n) { return n.replace(/[\p{Emoji}\uFE0F\u200D]+\s*/gu, '').trim() || n; }
function fmtK(n) { if (n >= 1000) return (n / 1000).toFixed(1).replace('.0', '') + 'к'; return String(n); }
