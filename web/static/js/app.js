/* ═══════════════════════════════════════════
   PerekupHelper SPA — v9
   Stalcraft Trading Hub
   ═══════════════════════════════════════════ */
const A=document.getElementById('app');
function go(h){location.hash=h}
function _goBack(){history.back()}

/* ── State ── */
let S={lotPP:20,salePP:20,lotSort:'buyout_price',lotOrder:'asc',saleQlt:'all',chatCh:'general',searchTab:'market'};
try{Object.assign(S,JSON.parse(localStorage.getItem('ph9')||'{}'))}catch(e){}
function saveS(){localStorage.setItem('ph9',JSON.stringify(S))}

/* ── Cache ── */
const _c=new Map();
function cG(k){const e=_c.get(k);return(e&&Date.now()-e.t<120000)?e.v:null}
function cS(k,v){_c.set(k,{v,t:Date.now()})}

/* ── Toast ── */
let _te;
function toast(m){if(!_te){_te=document.createElement('div');_te.className='toast';document.body.appendChild(_te)}_te.textContent=m;_te.classList.add('show');setTimeout(()=>_te.classList.remove('show'),2200)}

/* ── Render ── */
function render(h){A.innerHTML='<div class="page">'+h+'</div>';A.scrollTop=0}

/* ── Parse quality + potency from API additional ── */
function parseQU(add){
  if(!add)return{q:-1,u:0};
  return{q:(add.qlt!=null)?Number(add.qlt):-1, u:Math.max(0,Math.min(15,Math.round(add.ptn||0)))};
}

/* ── Emission ── */
let _emi=null,_emiTs=0;
async function getEmi(){
  if(_emi&&Date.now()-_emiTs<30000)return _emi;
  try{_emi=await API.get('/api/emission');_emiTs=Date.now()}catch(e){}
  return _emi;
}
function emiHTML(d){
  if(!d)return'';
  const now=Date.now();
  const cs=d.currentStart?new Date(d.currentStart).getTime():0;
  const ce=d.currentEnd?new Date(d.currentEnd).getTime():0;
  if(cs>0&&ce>0&&now>=cs&&now<ce){
    return'<div class="emi emi-on"><div class="emi-dot on"></div><div class="emi-info"><div class="emi-label">☢️ Выброс идёт!</div><div class="emi-sub">Укройтесь немедленно</div></div><div class="emi-timer" id="emi-timer">'+fmtMs(ce-now)+'</div></div>';
  }
  const pe=d.previousEnd?new Date(d.previousEnd).getTime():0;
  const ago=pe>0?fmtAgo(now-pe)+' назад':'—';
  return'<div class="emi"><div class="emi-dot off"></div><div class="emi-info"><div class="emi-label">Зона чиста</div><div class="emi-sub">Посл. выброс: '+ago+'</div></div></div>';
}
function fmtMs(ms){if(ms<=0)return'0:00';const m=Math.floor(ms/60000),s=Math.floor((ms%60000)/1000);return m+':'+String(s).padStart(2,'0')}
function fmtAgo(ms){if(ms<60000)return'<1 мин';if(ms<3600000)return Math.floor(ms/60000)+' мин';if(ms<86400000)return Math.floor(ms/3600000)+' ч';return Math.floor(ms/86400000)+' д'}

/* ── Router ── */
async function route(){
  const h=location.hash||'#/',p=h.replace('#','').split('/').filter(Boolean),pg=p[0]||'';
  document.querySelectorAll('#tab-bar .tab').forEach(t=>{
    const r=t.dataset.route;
    t.classList.toggle('active',r===h||(r==='#/'&&(h==='#/'||!pg)));
  });
  if(tg&&pg){tg.BackButton.show();tg.BackButton.offClick(_goBack);tg.BackButton.onClick(_goBack)}
  else if(tg){tg.BackButton.hide()}
  try{
    if(!pg||h==='#/')await P_home();
    else if(pg==='item')await P_item(p[1]);
    else if(pg==='auction')await P_auc(p[1]);
    else if(pg==='search')await P_search();
    else if(pg==='tracked')await P_tracked();
    else if(pg==='clan')await P_clan(p[1]);
    else if(pg==='player')await P_player(p.slice(1).join('/'));
    else if(pg==='market')await P_market(p[1]);
    else if(pg==='market-create')P_market_create();
    else if(pg==='market-my')await P_market_my();
    else if(pg==='chat')await P_chat(p[1]);
    else if(pg==='profile')await P_profile(p[1]);
    else if(pg==='user')await P_user(p[1]);
    else await P_home();
  }catch(e){render('<div class="empty"><div class="empty-i">⚠️</div><div class="empty-t">'+e.message+'</div></div>')}
  if(tg)tg.expand();
}
window.addEventListener('hashchange',route);
window.addEventListener('load',route);

/* ═══════════ HOME ═══════════ */
async function P_home(){
  render('<div class="ld">Загрузка</div>');
  const [emi,mkt,pop]=await Promise.all([
    getEmi(),
    API.get('/api/market?status=active&per_page=6').catch(()=>({items:[]})),
    API.get('/api/popular?limit=8').catch(()=>[]),
  ]);
  let h='';
  h+=emiHTML(emi);
  h+='<div class="quick-row">';
  h+='<div class="quick-card" onclick="go(\'#/search\')"><div class="quick-icon">🔍</div><div class="quick-label">Поиск</div></div>';
  h+='<div class="quick-card" onclick="go(\'#/tracked\')"><div class="quick-icon">⭐</div><div class="quick-label">Избранное</div></div>';
  h+='<div class="quick-card" onclick="go(\'#/market\')"><div class="quick-icon">🏪</div><div class="quick-label">Маркет</div></div>';
  h+='</div>';
  if(pop&&pop.length){
    h+='<div class="sec">🔥 Популярные предметы</div><div class="hscroll">';
    for(const i of pop){h+='<div class="hcard rk-'+(i.color||'DEFAULT')+'" onclick="haptic();go(\'#/item/'+i.id+'\')"><div class="hcard-img">'+ICO(i.icon)+'</div><div class="hcard-name" style="color:var(--rk-'+colorCssVar(i.color)+')">'+i.name+'</div></div>'}
    h+='</div>';
  }
  if(mkt.items&&mkt.items.length){
    h+='<div class="sec">🏪 Новые на маркете</div>';
    for(const l of mkt.items)h+=marketCard(l);
    h+='<button class="btn btn-o btn-sm" style="margin-top:8px" onclick="go(\'#/market\')">Все объявления →</button>';
  } else {
    h+='<div class="sec">🏪 Маркет</div>';
    h+='<div class="empty"><div class="empty-t" style="padding:18px 0">Пока нет объявлений.<br>Будьте первым!</div><button class="btn btn-g btn-sm" style="margin:10px auto 0" onclick="go(\'#/market-create\')">+ Создать объявление</button></div>';
  }
  render(h);
}
/* Map rank color to CSS var name */
function colorCssVar(c){
  const m={'DEFAULT':'def','RANK_NEWBIE':'new','RANK_STALKER':'stk','RANK_VETERAN':'vet','RANK_MASTER':'mas','RANK_LEGEND':'leg'};
  return m[c]||'def';
}

/* ═══════════ ITEM ═══════════ */
async function P_item(id){
  render('<div class="ld">Загрузка</div>');
  const [item,tr,mkt]=await Promise.all([
    API.get('/api/items/'+id),
    API.get('/api/tracked'),
    API.get('/api/market?item_id='+id+'&status=active&per_page=10').catch(()=>({items:[]})),
  ]);
  if(item.error){render('<div class="empty"><div class="empty-i">❌</div><div class="empty-t">Не найден</div></div>');return}
  const isTr=tr.some(t=>t.item_id===id);
  const ok=item.api_supported!==false;
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hero rk-'+item.color+'"><div class="hero-img">'+ICO(item.icon)+'</div><div class="hero-r"><div class="hero-t">'+item.name+'</div><div class="hero-s">'+item.category_name;
  if(item.rank_name)h+=' · <span class="rk-tag rk-tag-'+item.color+'">'+item.rank_name+'</span>';
  h+='</div></div></div>';
  if(mkt.items&&mkt.items.length){
    h+='<div class="sec">🏪 На маркете</div>';
    for(const l of mkt.items)h+=marketCard(l);
  }
  h+='<div class="bgrp">';
  if(ok){
    h+=(isTr?'<button class="btn btn-r" onclick="haptic(\'medium\');UT(\''+id+'\')">✕ Убрать</button>':'<button class="btn btn-g" onclick="haptic(\'medium\');TK(\''+id+'\')">⭐ В избранное</button>');
    h+='<a class="btn btn-o" href="#/auction/'+id+'">📊 Аукцион</a>';
  } else {
    h+=warnBox('Аукцион недоступен','Предмет не поддерживается API.');
  }
  h+='</div>';
  if(ok)h+='<button class="btn btn-b btn-sm" style="margin-top:6px" onclick="go(\'#/market-create\');setTimeout(()=>selectMcItem(\''+id+'\'),200)">🏪 Продать на маркете</button>';
  if(item.stats&&item.stats.length){
    h+='<div class="sec">Характеристики</div><div class="card" style="padding:10px 12px"><div class="stl">';
    for(const s of item.stats){let c='';if(s.color==='53C353')c='sg';else if(s.color==='C15252')c='sr';h+='<div class="str"><span class="stk">'+s.key+'</span><span class="stv '+c+'">'+s.value+'</span></div>'}
    h+='</div></div>';
  }
  render(h);
}
async function TK(id){await API.post('/api/tracked',{item_id:id});toast('⭐ Добавлено');P_item(id)}
async function UT(id){await API.del('/api/tracked/'+id);toast('✕ Убрано');P_item(id)}

/* ═══════════ AUCTION ═══════════ */
async function P_auc(id,lp,sp){
  lp=lp||1;sp=sp||1;
  render('<div class="ld">'+(S.saleQlt!=='all'?'Фильтрация по качеству...':'Загрузка')+'</div>');
  const item=await API.get('/api/items/'+id);
  if(item.api_supported===false){render('<a class="back" href="#/item/'+id+'">← Назад</a>'+warnBox('Недоступно','API не поддерживает.'));return}
  const isA=!!item.is_artefact,nm=item.name||id;
  const lOff=(lp-1)*S.lotPP,sOff=(sp-1)*S.salePP;
  let histUrl='/api/auction/'+id+'/history?limit='+S.salePP+'&offset='+sOff;
  if(isA&&S.saleQlt!=='all')histUrl+='&quality='+S.saleQlt;
  const [ld,hd]=await Promise.all([
    API.get('/api/auction/'+id+'/lots?limit='+S.lotPP+'&offset='+lOff+'&sort='+S.lotSort+'&order='+S.lotOrder),
    API.get(histUrl)]);
  const lots=(ld.lots||[]).slice(0,S.lotPP),sales=(hd.prices||[]).slice(0,S.salePP);
  const lTotal=ld.total||lots.length,sTotal=hd.total||sales.length;
  const lPages=Math.max(1,Math.ceil(lTotal/S.lotPP));
  const sPages=Math.max(1,Math.ceil(sTotal/S.salePP));
  _ctx.aucId=id;_ctx.lp=lp;_ctx.sp=sp;
  let h='<a class="back" href="#/item/'+id+'">← '+nm+'</a>';
  h+='<div class="hdr">📊 Аукцион</div>';
  h+='<div class="sec">Активные лоты · '+fmtK(lTotal)+'</div>';
  h+=sortBar([['buyout_price|asc','Цена ↑'],['buyout_price|desc','Цена ↓'],['time_created|desc','Новые']],S.lotSort+'|'+S.lotOrder,'setLS');
  h+=ppSel(S.lotPP,[10,20,50],'lot');
  if(lots.length){
    h+='<div class="card"><div class="tw"><table class="lt"><thead><tr><th>Цена</th>'+(isA?'<th>Качество</th>':'')+'<th>Тип</th><th>Истекает</th></tr></thead><tbody>';
    for(const l of lots){
      const pr=l.buyoutPrice||l.currentPrice||l.startPrice||0;
      const tp=l.buyoutPrice>0?'Выкуп':'Ставка';
      let qc='';if(isA){const{q,u}=parseQU(l.additional);qc='<td>'+qb(q)+(u>0?' '+upg(u):'')+'</td>'}
      h+='<tr><td class="lp">'+fmt(pr)+' ₽</td>'+(isA?qc:'')+'<td>'+tp+'</td><td class="td-date">'+fmtRemain(l.endTime)+'</td></tr>';
    }
    h+='</tbody></table></div></div>';
    if(lPages>1)h+=pgBar(lp,lPages,"P_auc('"+id+"',{p},"+sp+")");
  } else h+=emptyMsg('Нет активных лотов');
  h+='<div class="sec">История продаж · '+fmtK(sTotal)+'</div>';
  if(isA){
    h+='<div class="sort-bar">';
    for(const[v,l]of[['all','Все'],['0','Обычный'],['1','Необычн.'],['2','Особый'],['3','Редкий'],['4','Исключ.'],['5','Легенд.']]){
      h+='<button class="'+(S.saleQlt===v?'act':'')+'" onclick="setSaleQlt(\''+v+'\')">'+l+'</button>';
    }
    h+='</div>';
  }
  h+=ppSel(S.salePP,[10,20,50],'sale');
  if(sales.length){
    h+='<div class="card"><div class="tw"><table class="lt"><thead><tr><th>Цена</th>'+(isA?'<th>Качество</th>':'')+'<th>Кол</th><th>Дата</th></tr></thead><tbody>';
    for(const s of sales){
      let qc='';if(isA){const{q,u}=parseQU(s.additional);qc='<td>'+qb(q)+(u>0?' '+upg(u):'')+'</td>'}
      h+='<tr><td class="lp">'+fmt(s.price)+' ₽</td>'+(isA?qc:'')+'<td>'+(s.amount||1)+'</td><td class="td-date">'+fmtSaleDate(s.time)+'</td></tr>';
    }
    h+='</tbody></table></div></div>';
    if(sPages>1)h+=pgBar(sp,sPages,"P_auc('"+id+"',"+lp+",{p})");
  } else h+=emptyMsg('Нет данных о продажах');
  render(h);
}
function setLS(v){const[s,o]=v.split('|');S.lotSort=s;S.lotOrder=o;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,1,_ctx.sp||1)}
function setSaleQlt(v){S.saleQlt=v;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,_ctx.lp||1,1)}

/* ═══════════ SEARCH (2 tabs) ═══════════ */
let _st,_sSort='relevance',_lastQ='';
async function P_search(){
  let h='<div class="hdr">🔍 Поиск</div>';
  h+='<div class="tabs">';
  h+='<button class="tab-btn'+(S.searchTab==='market'?' act':'')+'" onclick="switchSearchTab(\'market\')">🏪 Маркет</button>';
  h+='<button class="tab-btn'+(S.searchTab==='auction'?' act':'')+'" onclick="switchSearchTab(\'auction\')">📊 Аукцион</button>';
  h+='</div>';
  h+='<div class="srch"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><input id="si" placeholder="'+(S.searchTab==='market'?'Поиск объявлений...':'Название предмета...')+'"></div>';
  if(S.searchTab==='auction'){
    h+=sortBar([['relevance','Релевантность'],['name','Имя'],['color','Редкость']],_sSort,'setSS');
  }
  h+='<div id="sr"></div>';
  render(h);
  const si=document.getElementById('si');
  if(si){
    si.value=_lastQ;
    si.addEventListener('input',e=>{clearTimeout(_st);_lastQ=e.target.value;_st=setTimeout(()=>doSearch(e.target.value),250)});
    if(_lastQ)doSearch(_lastQ);
    si.focus();
  }
}
function switchSearchTab(tab){S.searchTab=tab;saveS();_lastQ='';P_search()}
function setSS(v){_sSort=v;if(_lastQ)doSearch(_lastQ);else P_search()}

async function doSearch(q){
  const b=document.getElementById('sr');if(!b)return;
  if(q.trim().length<2){b.innerHTML='';return}
  b.innerHTML='<div class="ld">Поиск...</div>';
  try{
    if(S.searchTab==='market'){
      const d=await API.get('/api/market?status=active&search='+encodeURIComponent(q)+'&per_page=20');
      if(!d.items||!d.items.length){b.innerHTML=emptyMsg('Нет объявлений');return}
      let h='';for(const l of d.items)h+=marketCard(l);
      b.innerHTML=h;
    } else {
      const it=await API.get('/api/search?q='+encodeURIComponent(q)+'&limit=50&sort='+_sSort);
      if(!it.length){b.innerHTML=emptyMsg('Ничего не найдено');return}
      let h='<div class="card">';for(const i of it)h+=R(i.id,i.icon,i.name,i.rank_name||i.category_name,i.color,null,i.api_supported);h+='</div>';
      b.innerHTML=h;
    }
  }catch(e){b.innerHTML=emptyMsg('Ошибка поиска')}
}

/* ═══════════ TRACKED ═══════════ */
async function P_tracked(){
  render('<div class="ld">Загрузка</div>');
  const tr=await API.get('/api/tracked');
  let h='<div class="hdr">⭐ Избранное</div><div class="sub">'+tr.length+' предметов</div>';
  if(!tr.length){
    h+='<div class="empty"><div class="empty-i">📭</div><div class="empty-t">Ничего не добавлено</div><button class="btn btn-g btn-sm" style="margin:14px auto 0" onclick="go(\'#/search\')">🔍 Найти предметы</button></div>';
  } else {
    h+='<div class="card">';for(const t of tr)h+=R(t.item_id,t.icon,t.name,'',t.color,null,t.api_supported);h+='</div>';
  }
  render(h);
}

/* ═══════════ CLAN ═══════════ */
async function P_clan(id){
  if(!id){render(emptyMsg('Укажите ID клана'));return}
  render('<div class="ld">Загрузка</div>');
  const [info,members]=await Promise.all([API.get('/api/clan/'+id),API.get('/api/clan/'+id+'/members')]);
  if(info.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Клан не найден'));return}
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hdr">🏰 '+(info.name||id)+'</div>';
  if(info.tag)h+='<div class="sub">['+info.tag+'] · '+(info.memberCount||0)+' участников · Уровень '+(info.level||'?')+'</div>';
  if(info.description)h+='<div class="card" style="padding:12px"><div style="font-size:12px;color:var(--t2)">'+info.description+'</div></div>';
  const ml=members.members||members||[];
  if(ml.length){
    h+='<div class="sec">Участники · '+ml.length+'</div><div class="card"><div class="tw"><table class="lt"><thead><tr><th>Имя</th><th>Ранг</th></tr></thead><tbody>';
    for(const m of ml){
      const name=m.name||m.username||'—';
      h+='<tr><td><a style="color:var(--acc);cursor:pointer;text-decoration:none" onclick="go(\'#/player/'+encodeURIComponent(name)+'\')">'+name+'</a></td><td class="td-date">'+(m.rank||m.role||'—')+'</td></tr>';
    }
    h+='</tbody></table></div></div>';
  }
  render(h);
}

/* ═══════════ PLAYER ═══════════ */
async function P_player(name){
  if(!name){render(emptyMsg('Укажите имя'));return}
  render('<div class="ld">Загрузка</div>');
  const d=await API.get('/api/character/'+encodeURIComponent(name)+'/profile');
  if(d.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Профиль не найден'));return}
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hdr">👤 '+name+'</div>';
  if(d.clanInfo)h+='<div class="sub">Клан: <a style="color:var(--acc);cursor:pointer" onclick="go(\'#/clan/'+d.clanInfo.id+'\')">'+(d.clanInfo.name||d.clanInfo.id)+'</a></div>';
  const skip=new Set(['clanInfo','username','id']);
  const entries=Object.entries(d).filter(([k])=>!skip.has(k));
  if(entries.length){
    h+='<div class="card" style="padding:10px 12px"><div class="stl">';
    for(const[k,v]of entries){if(typeof v==='object')continue;h+='<div class="str"><span class="stk">'+k+'</span><span class="stv">'+v+'</span></div>'}
    h+='</div></div>';
  }
  render(h);
}

/* ═══════════ MARKETPLACE ═══════════ */
async function P_market(sub){
  if(sub==='create'){P_market_create();return}
  if(sub==='my'){await P_market_my();return}
  render('<div class="ld">Загрузка</div>');
  const d=await API.get('/api/market?status=active&per_page=30');
  let h='<div class="hdr">🏪 Торговая площадка</div>';
  h+='<div class="tabs">';
  h+='<button class="tab-btn act" onclick="go(\'#/market\')">Все</button>';
  h+='<button class="tab-btn" onclick="go(\'#/market-create\')">+ Создать</button>';
  h+='<button class="tab-btn" onclick="go(\'#/market-my\')">Мои</button>';
  h+='</div>';
  if(!d.items||!d.items.length){
    h+=emptyMsg('Пока нет объявлений. Будь первым! 🎯');
  } else {
    for(const l of d.items)h+=marketCard(l);
    if(d.pages>1)h+='<div class="sub" style="text-align:center">Всего: '+d.total+' объявлений</div>';
  }
  render(h);
}

function marketCard(l){
  const av=l.user&&l.user.avatar_url?'<img src="'+l.user.avatar_url+'" alt="">':'👤';
  const uname=l.user?l.user.display_name:'Аноним';
  const urep=l.user&&l.user.reputation?repBadge(l.user.reputation):'';
  const ico=l.icon?'<img src="'+l.icon+'" alt="" onerror="this.parentElement.innerHTML=\'📦\'">':'📦';
  const tp=l.listing_type==='buy'?'<span class="mcard-type buy">Покупка</span>':'<span class="mcard-type sell">Продажа</span>';
  let meta=tp;
  // Quality only for artefacts
  if(l.is_artefact && l.quality>=0)meta+=qb(l.quality);
  if(l.is_artefact && l.upgrade_level>0)meta+=upg(l.upgrade_level);
  const nameColor=l.color?'style="color:var(--rk-'+colorCssVar(l.color)+')"':'';
  return'<div class="mcard" onclick="go(\'#/user/'+((l.user&&l.user.id)||0)+'\')">'
    +'<div class="mcard-head"><div class="mcard-icon">'+ico+'</div><div class="mcard-info"><div class="mcard-name" '+nameColor+'>'+l.item_name+'</div><div class="mcard-meta">'+meta+'</div></div></div>'
    +'<div class="mcard-price">'+fmt(l.price)+' ₽'+(l.amount>1?' × '+l.amount:'')+'</div>'
    +(l.description?'<div style="font-size:11px;color:var(--t2);margin-top:6px">'+l.description+'</div>':'')
    +'<div class="mcard-bottom"><div class="mcard-user"><div class="mcard-avatar">'+av+'</div><span>'+uname+urep+'</span></div><div class="mcard-time">'+fmtSaleDate(l.created_at)+'</div></div>'
    +'</div>';
}

/* ═══════════ MARKET CREATE ═══════════ */
let _mcItemData=null;
function P_market_create(){
  _mcItemData=null;
  let h='<a class="back" href="#/market">← Маркет</a>';
  h+='<div class="hdr">📝 Новое объявление</div><div class="sub">Объявление действует 2 дня</div>';
  h+='<div class="form-group"><label>Предмет</label><input id="mc-search" placeholder="Поиск предмета..."></div>';
  h+='<div id="mc-results"></div>';
  h+='<input type="hidden" id="mc-item-id" value="">';
  h+='<div id="mc-selected"></div>';
  h+='<div class="form-group"><label>Тип</label><select id="mc-type"><option value="sell">Продажа</option><option value="buy">Покупка</option></select></div>';
  h+='<div class="form-group"><label>Цена (₽)</label><input id="mc-price" type="number" placeholder="100000"></div>';
  h+='<div class="form-group"><label>Количество</label><input id="mc-amount" type="number" value="1" min="1"></div>';
  h+='<div id="mc-quality-block" style="display:none">';
  h+='<div class="form-group"><label>Качество</label><select id="mc-qlt"><option value="-1">Без качества</option><option value="0">Обычный</option><option value="1">Необычный</option><option value="2">Особый</option><option value="3">Редкий</option><option value="4">Исключительный</option><option value="5">Легендарный</option></select></div>';
  h+='<div class="form-group"><label>Заточка</label><input id="mc-upg" type="number" value="0" min="0" max="15"></div>';
  h+='</div>';
  h+='<div class="form-group"><label>Описание</label><textarea id="mc-desc" rows="3" placeholder="Дополнительная информация..."></textarea></div>';
  h+='<button class="btn btn-g" onclick="submitListing()">🏪 Опубликовать</button>';
  render(h);
  const si=document.getElementById('mc-search');
  let st;
  si.addEventListener('input',e=>{clearTimeout(st);st=setTimeout(()=>mcSearch(e.target.value),250)});
}
function _showQualityBlock(show){
  const b=document.getElementById('mc-quality-block');
  if(b)b.style.display=show?'block':'none';
}
async function mcSearch(q){
  const b=document.getElementById('mc-results');
  if(!b||q.length<2){if(b)b.innerHTML='';return}
  try{
    const it=await API.get('/api/search?q='+encodeURIComponent(q)+'&limit=10');
    if(!it.length){b.innerHTML='<div style="font-size:11px;color:var(--t3);padding:8px 0">Ничего не найдено</div>';return}
    b.innerHTML=it.map(i=>'<div class="irow" onclick="selectMcItem(\''+i.id+'\')"><div class="irow-icon">'+ICO(i.icon)+'</div><div class="ib"><div class="in">'+i.name+'</div></div></div>').join('');
  }catch(e){b.innerHTML=''}
}
async function selectMcItem(id){
  document.getElementById('mc-item-id').value=id;
  document.getElementById('mc-results').innerHTML='';
  document.getElementById('mc-search').value='';
  try{
    const d=await API.get('/api/items/'+id);
    _mcItemData=d;
    const nameColor=d.color?'style="color:var(--rk-'+colorCssVar(d.color)+')"':'';
    document.getElementById('mc-selected').innerHTML='<div class="card" style="padding:10px 12px;margin:8px 0"><div style="font-weight:800" '+nameColor+'>✅ '+d.name+'</div><div style="font-size:10px;color:var(--t3)">'+d.category_name+'</div></div>';
    // Show quality block only for artefacts and weapon modules
    const needQuality=d.is_artefact||(d.category&&(d.category.startsWith('weapon/')||d.category.includes('module')));
    _showQualityBlock(!!needQuality);
  }catch(e){
    document.getElementById('mc-selected').innerHTML='<div class="card" style="padding:10px 12px;margin:8px 0"><div style="font-weight:800">✅ '+id+'</div></div>';
    _showQualityBlock(false);
  }
}
async function loadPreItem(id){
  try{await selectMcItem(id)}catch(e){}
}
async function submitListing(){
  const id=document.getElementById('mc-item-id').value;
  if(!id){toast('Выберите предмет');return}
  const price=parseInt(document.getElementById('mc-price').value);
  if(!price||price<=0){toast('Укажите цену');return}
  const qBlock=document.getElementById('mc-quality-block');
  const showQ=qBlock&&qBlock.style.display!=='none';
  const d={
    item_id:id,
    listing_type:document.getElementById('mc-type').value,
    price:price,
    amount:parseInt(document.getElementById('mc-amount').value)||1,
    quality:showQ?parseInt(document.getElementById('mc-qlt').value):-1,
    upgrade_level:showQ?(parseInt(document.getElementById('mc-upg').value)||0):0,
    description:document.getElementById('mc-desc').value.trim(),
  };
  try{
    const r=await API.post('/api/market',d);
    if(r.error){toast('❌ '+r.error);return}
    toast('✅ Объявление создано!');go('#/market-my');
  }catch(e){toast('❌ Ошибка: требуется авторизация через Telegram')}
}

/* ═══════════ MY LISTINGS ═══════════ */
async function P_market_my(){
  render('<div class="ld">Загрузка</div>');
  let items;
  try{items=await API.get('/api/market/my')}catch(e){render(emptyMsg('Войдите через Telegram'));return}
  let h='<a class="back" href="#/market">← Маркет</a>';
  h+='<div class="hdr">📋 Мои объявления</div>';
  if(!items||!items.length){
    h+=emptyMsg('У вас пока нет объявлений');
  } else {
    for(const l of items){
      const ico=l.icon?'<img src="'+l.icon+'" alt="" onerror="this.parentElement.innerHTML=\'📦\'">':'📦';
      const st=l.status;
      h+='<div class="mcard">';
      h+='<div class="mcard-head"><div class="mcard-icon">'+ico+'</div><div class="mcard-info"><div class="mcard-name">'+l.item_name+'</div><div class="mcard-meta"><span class="mcard-status '+st+'">'+statusRu(st)+'</span></div></div></div>';
      h+='<div class="mcard-price">'+fmt(l.price)+' ₽'+(l.amount>1?' × '+l.amount:'')+'</div>';
      if(l.sold_price)h+='<div style="font-size:11px;color:var(--grn);margin-top:4px">Продано за '+fmt(l.sold_price)+' ₽</div>';
      if(st==='active'){
        h+='<div class="bgrp" style="margin-top:8px">';
        h+='<button class="btn btn-g btn-sm" onclick="event.stopPropagation();markSold('+l.id+')">✅ Продано</button>';
        h+='<button class="btn btn-r btn-sm" onclick="event.stopPropagation();cancelListing('+l.id+')">✕ Отменить</button>';
        h+='</div>';
      }
      h+='<div class="mcard-time" style="margin-top:6px">Создано: '+fmtSaleDate(l.created_at)+'</div>';
      h+='</div>';
    }
  }
  render(h);
}
async function markSold(id){
  const price=prompt('За какую цену продано? (₽)');
  if(price===null)return;
  const p=parseInt(price)||0;
  try{
    await API.put('/api/market/'+id+'/status',{status:'sold',sold_price:p||null});
    toast('✅ Помечено как продано');P_market_my();
  }catch(e){toast('❌ Ошибка')}
}
async function cancelListing(id){
  if(!confirm('Отменить объявление?'))return;
  try{
    await API.put('/api/market/'+id+'/status',{status:'cancelled'});
    toast('✕ Отменено');P_market_my();
  }catch(e){toast('❌ Ошибка')}
}
function statusRu(s){return{active:'Активно',sold:'Продано',expired:'Истекло',cancelled:'Отменено'}[s]||s}

/* ═══════════ CHAT ═══════════ */
let _chatPoll=null;
// Generate deterministic color from user ID
function userColor(u){
  if(u&&u.chat_color)return u.chat_color;
  const colors=['#e57373','#f06292','#ba68c8','#9575cd','#7986cb','#64b5f6','#4fc3f7','#4dd0e1','#4db6ac','#81c784','#aed581','#dce775','#fff176','#ffd54f','#ffb74d','#ff8a65'];
  const id=u?u.id:0;
  return colors[id%colors.length];
}
function repBadge(r){
  if(!r&&r!==0)return'';
  if(r>0)return'<span class="rep pos">+'+r+'</span>';
  if(r<0)return'<span class="rep neg">'+r+'</span>';
  return'<span class="rep zero">0</span>';
}
async function P_chat(channel){
  channel=channel||S.chatCh||'general';
  S.chatCh=channel;saveS();
  if(_chatPoll){clearTimeout(_chatPoll);_chatPoll=null}
  const isDM=channel.startsWith('dm:');
  render('<div class="ld">Загрузка</div>');

  let h='<div class="hdr">💬 Чат</div>';

  // Tabs: Общий, Торговый, Личные
  h+='<div class="chat-channels">';
  h+='<div class="chat-ch'+(channel==='general'?' act':'')+'" onclick="go(\'#/chat/general\')">💬 Общий</div>';
  h+='<div class="chat-ch'+(channel==='trading'?' act':'')+'" onclick="go(\'#/chat/trading\')">💰 Торговый</div>';
  h+='<div class="chat-ch'+(channel==='dm-list'?' act':'')+'" onclick="go(\'#/chat/dm-list\')">✉️ Личные</div>';
  h+='</div>';

  if(channel==='dm-list'){
    // DM list
    try{
      const dms=await API.get('/api/chat/dm-list');
      if(!dms.length){h+=emptyMsg('Нет личных сообщений');} else {
        for(const d of dms){
          const av=d.user&&d.user.avatar_url?'<img src="'+d.user.avatar_url+'" alt="">':'✉️';
          const name=d.user?d.user.display_name:'Пользователь';
          h+='<div class="dm-item" onclick="go(\'#/chat/'+d.channel+'\')"><div class="dm-item-av">'+av+'</div><div class="dm-item-info"><div class="dm-item-name">'+name+'</div><div class="dm-item-last">'+d.last_message+'</div></div><div class="dm-item-time">'+fmtSaleDate(d.last_at)+'</div></div>';
        }
      }
    }catch(e){h+=emptyMsg('Авторизуйтесь через Telegram')}
    render(h);
    return;
  }

  const msgs=await API.get('/api/chat/'+channel+'/messages?limit=50');
  h+='<div class="chat-msgs" id="chat-msgs">';
  if(!msgs.length)h+='<div class="empty"><div class="empty-t">Пока нет сообщений. Напишите первым! 💬</div></div>';
  for(const m of msgs)h+=chatMsg(m);
  h+='</div>';
  h+='<div class="chat-input"><input id="chat-in" placeholder="Сообщение..." onkeypress="if(event.key===\'Enter\')sendChat(\''+channel+'\')"><button onclick="sendChat(\''+channel+'\')">→</button></div>';
  render(h);
  const box=document.getElementById('chat-msgs');
  if(box)box.scrollTop=box.scrollHeight;
  _ctx.chatLastId=msgs.length?msgs[msgs.length-1].id:0;
  startChatPoll(channel);
}
function chatMsg(m){
  const u=m.user||{id:0,display_name:'Аноним'};
  const av=u.avatar_url?'<img src="'+u.avatar_url+'" alt="">':'👤';
  const color=userColor(u);
  const rep=repBadge(u.reputation);
  return'<div class="chat-msg"><div class="chat-msg-av" onclick="go(\'#/user/'+u.id+'\')">'+av+'</div><div class="chat-msg-body"><div class="chat-msg-head"><span class="chat-msg-name" style="color:'+color+'" onclick="go(\'#/user/'+u.id+'\')">'+u.display_name+'</span>'+rep+'<span class="chat-msg-time">'+fmtChatTime(m.created_at)+'</span></div><div class="chat-msg-text">'+escHtml(m.text)+'</div></div></div>';
}
function fmtChatTime(s){
  if(!s)return'';
  try{const d=new Date(s);return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}catch(e){return''}
}
async function sendChat(ch){
  const inp=document.getElementById('chat-in');
  if(!inp||!inp.value.trim())return;
  const text=inp.value.trim();
  inp.value='';
  try{
    const r=await API.post('/api/chat/'+ch+'/messages',{text:text});
    if(r.error){toast('❌ '+r.error);inp.value=text;return}
    const box=document.getElementById('chat-msgs');
    if(box){
      const emp=box.querySelector('.empty');if(emp)emp.remove();
      box.insertAdjacentHTML('beforeend',chatMsg(r));
      box.scrollTop=box.scrollHeight;
      _ctx.chatLastId=r.id;
    }
  }catch(e){toast('❌ Авторизуйтесь через Telegram');inp.value=text}
}
function startChatPoll(ch){
  async function poll(){
    try{
      const msgs=await API.get('/api/chat/'+ch+'/messages?since_id='+(_ctx.chatLastId||0)+'&limit=20');
      if(msgs.length){
        const box=document.getElementById('chat-msgs');
        if(box){
          for(const m of msgs){
            if(m.id>(_ctx.chatLastId||0)){
              box.insertAdjacentHTML('beforeend',chatMsg(m));
              _ctx.chatLastId=m.id;
            }
          }
          box.scrollTop=box.scrollHeight;
        }
      }
    }catch(e){}
    if(location.hash.startsWith('#/chat'))_chatPoll=setTimeout(poll,3000);
  }
  _chatPoll=setTimeout(poll,3000);
}

/* ═══════════ PROFILE ═══════════ */
async function P_profile(sub){
  if(sub==='edit'){await P_profile_edit();return}
  render('<div class="ld">Загрузка</div>');
  let me;
  try{me=await API.get('/api/me')}catch(e){}
  if(!me||!me.id){
    render('<div class="hdr">👤 Профиль</div><div class="empty"><div class="empty-i">🔐</div><div class="empty-t">Откройте через Telegram Mini App для авторизации</div></div>');
    return;
  }
  _me=me;
  const av=me.avatar_url?'<img src="'+me.avatar_url+'" alt="">':'👤';
  const rep=me.reputation>0?'<span class="rep pos">+'+me.reputation+'</span>':(me.reputation<0?'<span class="rep neg">'+me.reputation+'</span>':'<span class="rep zero">0</span>');
  let h='<div class="profile-header">';
  h+='<div class="profile-avatar" onclick="document.getElementById(\'av-upload\').click()">'+av+'<input type="file" id="av-upload" accept="image/*" style="display:none" onchange="uploadAvatar(this)"></div>';
  h+='<div class="profile-info"><div class="profile-name">'+me.display_name+' '+rep+'</div>';
  h+='<div class="profile-sub">';
  if(me.game_nickname)h+='🎮 '+me.game_nickname+'<br>';
  if(me.discord)h+='💬 '+me.discord;
  h+='</div></div></div>';
  if(me.bio)h+='<div class="card" style="padding:12px"><div style="font-size:12px;color:var(--t2)">'+me.bio+'</div></div>';
  h+='<button class="btn btn-o" onclick="go(\'#/profile/edit\')">✏️ Редактировать</button>';
  h+='<div style="margin-top:14px"><button class="btn btn-o" onclick="go(\'#/tracked\')">⭐ Избранное</button></div>';
  h+='<div style="margin-top:8px"><button class="btn btn-o" onclick="go(\'#/market-my\')">📋 Мои объявления</button></div>';
  render(h);
}
async function P_profile_edit(){
  render('<div class="ld">Загрузка</div>');
  let me;
  try{me=await API.get('/api/me')}catch(e){}
  if(!me||!me.id){render(emptyMsg('Авторизуйтесь через Telegram'));return}
  let h='<a class="back" href="#/profile">← Профиль</a>';
  h+='<div class="hdr">✏️ Редактирование</div>';
  h+='<div class="profile-field"><label>Отображаемое имя</label><input id="pe-name" value="'+(me.display_name||'')+'"></div>';
  h+='<div class="profile-field"><label>Ник в игре</label><input id="pe-game" value="'+(me.game_nickname||'')+'" placeholder="Например: Player-1"></div>';
  h+='<div class="profile-field"><label>Discord</label><input id="pe-disc" value="'+(me.discord||'')+'" placeholder="username#1234"></div>';
  h+='<div class="profile-field"><label>О себе</label><textarea id="pe-bio" rows="3" placeholder="Расскажите о себе...">'+(me.bio||'')+'</textarea></div>';
  h+='<button class="btn btn-g" onclick="saveProfile()">💾 Сохранить</button>';
  render(h);
}
async function saveProfile(){
  const d={
    display_name:document.getElementById('pe-name').value.trim(),
    game_nickname:document.getElementById('pe-game').value.trim(),
    discord:document.getElementById('pe-disc').value.trim(),
    bio:document.getElementById('pe-bio').value.trim(),
  };
  try{
    await API.put('/api/me',d);
    toast('✅ Сохранено');_me=null;go('#/profile');
  }catch(e){toast('❌ Ошибка')}
}
async function uploadAvatar(input){
  if(!input.files[0])return;
  const fd=new FormData();
  fd.append('file',input.files[0]);
  try{
    const r=await API.upload('/api/me/avatar',fd);
    if(r.error){toast('❌ '+r.error);return}
    toast('✅ Аватар обновлён');_me=null;go('#/profile');
  }catch(e){toast('❌ Ошибка загрузки')}
}

/* ═══════════ USER (public profile) ═══════════ */
async function P_user(uid){
  if(!uid||uid==='0'){render(emptyMsg('Пользователь не найден'));return}
  render('<div class="ld">Загрузка</div>');
  const u=await API.get('/api/users/'+uid);
  if(u.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Не найден'));return}
  const av=u.avatar_url?'<img src="'+u.avatar_url+'" alt="">':'👤';
  const rep=u.reputation>0?'<span class="rep pos">+'+u.reputation+'</span>':(u.reputation<0?'<span class="rep neg">'+u.reputation+'</span>':'<span class="rep zero">0</span>');
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="profile-header">';
  h+='<div class="profile-avatar" style="cursor:default;border-color:var(--brd)">'+av+'</div>';
  h+='<div class="profile-info"><div class="profile-name">'+u.display_name+' '+rep+'</div>';
  h+='<div class="profile-sub">';
  if(u.game_nickname)h+='🎮 '+u.game_nickname+'<br>';
  if(u.discord)h+='💬 '+u.discord;
  if(u.followers_count)h+='<br>👥 '+u.followers_count+' подписчиков';
  h+='</div></div></div>';
  if(u.bio)h+='<div class="card" style="padding:12px"><div style="font-size:12px;color:var(--t2)">'+u.bio+'</div></div>';
  h+='<div class="bgrp">';
  if(!u.is_self){
    h+='<button class="btn btn-o btn-sm" onclick="initDM('+uid+')">💬 Написать</button>';
    if(u.is_following){
      h+='<button class="btn btn-r btn-sm" onclick="unfollowUser('+uid+')">✕ Отписаться</button>';
    } else {
      h+='<button class="btn btn-b btn-sm" onclick="followUser('+uid+')">👤 Подписаться</button>';
    }
  }
  h+='</div>';
  // User's marketplace listings
  const mkt=await API.get('/api/market?status=active&per_page=10');
  const userListings=(mkt.items||[]).filter(l=>l.user&&l.user.id===parseInt(uid));
  if(userListings.length){
    h+='<div class="sec">Объявления</div>';
    for(const l of userListings)h+=marketCard(l);
  }
  render(h);
}
async function initDM(uid){
  try{
    const r=await API.get('/api/chat/dm/'+uid);
    if(r.error){toast('❌ '+r.error);return}
    if(r.channel)go('#/chat/'+r.channel);
  }catch(e){toast('❌ Авторизуйтесь через Telegram')}
}
async function followUser(uid){
  try{await API.post('/api/users/'+uid+'/follow',{});toast('👤 Подписка');P_user(uid)}catch(e){toast('❌ Ошибка')}
}
async function unfollowUser(uid){
  try{await API.del('/api/users/'+uid+'/follow');toast('✕ Отписка');P_user(uid)}catch(e){toast('❌ Ошибка')}
}

/* ═══════════ HELPERS ═══════════ */
function ICO(s){
  if(!s||s==='/icons/'||s==='')return'<div class="no-icon">📦</div>';
  return'<img src="'+s+'" alt="" onerror="this.parentElement.innerHTML=\'<div class=\\\'no-icon\\\'>📦</div>\'" loading="lazy">';
}
function R(id,icon,name,tag,color,price,apiOk){
  const p=price?'<div class="ip">'+fmt(price)+' ₽</div>':'';
  const w=(apiOk===false)?'<span class="badge-wiki">wiki</span>':'';
  let tH='';if(tag)tH='<div class="it"><span class="rk-tag rk-tag-'+(color||'DEFAULT')+'">'+tag+'</span></div>';
  return'<div class="irow rk-'+(color||'DEFAULT')+'" onclick="haptic();go(\'#/item/'+id+'\')"><div class="irow-icon">'+ICO(icon)+'</div><div class="ib"><div class="in">'+name+w+'</div>'+tH+'</div>'+p+'</div>';
}
function sortBar(opts,cur,fn){
  let h='<div class="sort-bar">';
  for(const[v,l]of opts)h+='<button class="'+(cur===v?'act':'')+'" onclick="'+fn+"('"+v+"')"+'">'+(l||v)+'</button>';
  return h+'</div>';
}
function ppSel(cur,opts,key){
  let h='<div class="pps"><span>Показать:</span>';
  for(const v of opts)h+='<button class="'+(v===cur?'act':'')+'" onclick="setPP(\''+key+'\','+v+')">'+v+'</button>';
  return h+'</div>';
}
function pgBar(cur,tot,tpl){
  return'<div class="pgr"><button '+(cur<=1?'disabled':'')+' onclick="'+tpl.replace('{p}',cur-1)+'">‹</button><span class="pi">'+cur+' / '+tot+'</span><button '+(cur>=tot?'disabled':'')+' onclick="'+tpl.replace('{p}',cur+1)+'">›</button></div>';
}
function emptyMsg(t){return'<div class="empty"><div class="empty-t" style="padding:18px 0">'+t+'</div></div>'}
function warnBox(t,d){return'<div class="warn-box"><span class="warn-icon">⚠️</span><div class="warn-text"><b>'+t+'</b><br>'+d+'</div></div>'}
let _ctx={};
function setPP(key,val){
  if(key==='lot'){S.lotPP=val;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,1,_ctx.sp||1)}
  else if(key==='sale'){S.salePP=val;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,_ctx.lp||1,1)}
}
function fmtRemain(s){
  if(!s)return'—';
  try{const d=new Date(s),now=Date.now(),diff=d.getTime()-now;if(isNaN(d))return'—';if(diff<=0)return'Истёк';if(diff<3600000)return Math.floor(diff/60000)+'м';if(diff<86400000)return Math.floor(diff/3600000)+'ч '+Math.floor((diff%3600000)/60000)+'м';return Math.floor(diff/86400000)+'д '+Math.floor((diff%86400000)/3600000)+'ч'}catch(e){return'—'}
}
function fmtSaleDate(s){
  if(!s)return'—';
  try{const d=new Date(s);if(isNaN(d))return'—';const now=Date.now(),diff=now-d.getTime();if(diff<0)return fmtFullDate(d);if(diff<60000)return'только что';if(diff<3600000)return Math.floor(diff/60000)+' мин назад';if(diff<86400000)return Math.floor(diff/3600000)+' ч назад';return fmtFullDate(d)}catch(e){return'—'}
}
function fmtFullDate(d){
  const dd=String(d.getDate()).padStart(2,'0');const mm=String(d.getMonth()+1).padStart(2,'0');
  const yy=d.getFullYear();const hh=String(d.getHours()).padStart(2,'0');const mi=String(d.getMinutes()).padStart(2,'0');
  return dd+'.'+mm+'.'+yy+' '+hh+':'+mi;
}
function esc(s){return(s||'').replace(/'/g,"\\'")}
function escHtml(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function fmtK(n){if(n>=1000000)return(n/1000000).toFixed(1).replace('.0','')+'М';if(n>=1000)return(n/1000).toFixed(1).replace('.0','')+'к';return String(n)}
