/* ═══════════════════════════════════════════
   PerekupHelper SPA — v11
   Stalcraft Trading Hub
   Skeleton · Charts · Filters · Theme
   ═══════════════════════════════════════════ */
const A=document.getElementById('app');
function go(h){location.hash=h}
function _goBack(){history.back()}

/* ── State ── */
let S={lotPP:20,salePP:20,lotSort:'buyout_price',lotOrder:'asc',saleQlt:'all',saleUpg:'all',saleSort:'time_desc',lotQlt:'all',chatCh:'general',searchTab:'market',chartDays:30};
try{Object.assign(S,JSON.parse(localStorage.getItem('ph11')||'{}'))}catch(e){}
function saveS(){localStorage.setItem('ph11',JSON.stringify(S))}

/* ── Cache ── */
const _c=new Map();
function cG(k){const e=_c.get(k);return(e&&Date.now()-e.t<120000)?e.v:null}
function cS(k,v){_c.set(k,{v,t:Date.now()})}

/* ── Toast ── */
let _te;
function toast(m){if(!_te){_te=document.createElement('div');_te.className='toast';document.body.appendChild(_te)}_te.textContent=m;_te.classList.add('show');setTimeout(()=>_te.classList.remove('show'),2200)}

/* ── Unread badge ── */
async function _updateUnreadBadge(){
  try{
    const me=await getMe();if(!me)return;
    const cnt=me.unread_count||0;
    const chatTab=document.querySelector('#tab-bar .tab[data-route="#/chat"]');
    if(!chatTab)return;
    let badge=chatTab.querySelector('.tab-badge');
    if(cnt>0){
      if(!badge){badge=document.createElement('span');badge.className='tab-badge';chatTab.style.position='relative';chatTab.appendChild(badge)}
      badge.textContent=cnt>9?'9+':cnt;
    } else if(badge){badge.remove()}
  }catch(e){}
}

/* ── Render ── */
function render(h){A.innerHTML='<div class="page">'+h+'</div>';A.scrollTop=0}

/* ── Parse quality + potency ── */
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
  _updateUnreadBadge();
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
    else if(pg==='blocked')await P_blocked();
    else await P_home();
  }catch(e){render('<div class="empty"><div class="empty-i">⚠️</div><div class="empty-t">'+e.message+'</div></div>')}
  if(tg)tg.expand();
}
window.addEventListener('hashchange',route);
window.addEventListener('load',()=>{showOnboarding();route()});

/* ═══════════ HOME ═══════════ */
async function P_home(){
  render(skelBlock()+skelCards(3));
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
    for(const i of pop)h+='<div class="hcard rk-'+(i.color||'DEFAULT')+'" onclick="haptic();go(\'#/item/'+i.id+'\')"><div class="hcard-img">'+ICO(i.icon)+'</div><div class="hcard-name" style="color:var(--rk-'+colorCssVar(i.color)+')">'+i.name+'</div></div>';
    h+='</div>';
  }
  if(mkt.items&&mkt.items.length){
    h+='<div class="sec">🏪 Новые на маркете</div>';
    for(const l of mkt.items)h+=marketCard(l);
    h+='<button class="btn btn-o btn-sm" style="margin-top:8px" onclick="go(\'#/market\')">Все объявления →</button>';
  } else {
    h+='<div class="sec">🏪 Маркет</div>';
    h+='<div class="empty"><div class="empty-t" style="padding:18px 0">Пока нет объявлений.<br>Будьте первым!</div><button class="btn btn-g btn-sm" style="margin:10px auto 0" onclick="go(\'#/market-create\')">+ Создать</button></div>';
  }
  render(h);
}
function colorCssVar(c){
  const m={'DEFAULT':'def','RANK_NEWBIE':'new','RANK_STALKER':'stk','RANK_VETERAN':'vet','RANK_MASTER':'mas','RANK_LEGEND':'leg'};
  return m[c]||'def';
}

/* ═══════════ ITEM ═══════════ */
async function P_item(id){
  render(skelRows(4));
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
    h+=(isTr?'<button class="btn btn-r" onclick="haptic(\'medium\');UT(\''+id+'\')">✕ Убрать</button>':'<button class="btn btn-g" onclick="haptic(\'medium\');TK(\''+id+'\',event)">⭐ В избранное</button>');
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
async function TK(id,ev){
  if(ev){favAnim(ev.clientX||ev.pageX,ev.clientY||ev.pageY)}else{favAnim()}
  await API.post('/api/tracked',{item_id:id});toast('⭐ Добавлено');P_item(id);
}
async function UT(id){await API.del('/api/tracked/'+id);toast('✕ Убрано');P_item(id)}

/* ═══════════ AUCTION (completely reworked) ═══════════ */
let _aucState = {};

async function P_auc(id,lp,sp){
  lp=lp||1;sp=sp||1;
  // Show skeleton
  render(skelBlock()+'<div class="sec">Загрузка...</div>'+skelRows(5));

  const item=await API.get('/api/items/'+id);
  if(item.api_supported===false){render('<a class="back" href="#/item/'+id+'">← Назад</a>'+warnBox('Недоступно','API не поддерживает.'));return}
  const isA=!!item.is_artefact, nm=item.name||id;

  // Build lots URL with quality filter
  const lOff=(lp-1)*S.lotPP;
  let lotsUrl='/api/auction/'+id+'/lots?limit='+S.lotPP+'&offset='+lOff+'&sort='+S.lotSort+'&order='+S.lotOrder;
  if(isA&&S.lotQlt!=='all')lotsUrl+='&quality='+S.lotQlt;

  // Build history URL with quality + upgrade + sort
  const sOff=(sp-1)*S.salePP;
  let histUrl='/api/auction/'+id+'/history?limit='+S.salePP+'&offset='+sOff+'&sort='+S.saleSort;
  if(isA&&S.saleQlt!=='all')histUrl+='&quality='+S.saleQlt;
  if(isA&&S.saleUpg!=='all')histUrl+='&upgrade='+S.saleUpg;

  const [ld,hd,syncSt,chartD]=await Promise.all([
    API.get(lotsUrl),
    API.get(histUrl),
    API.get('/api/auction/'+id+'/sync-status').catch(()=>({})),
    API.get('/api/auction/'+id+'/chart-data?days='+S.chartDays+(isA&&S.saleQlt!=='all'?'&quality='+S.saleQlt:'')).catch(()=>({points:[]})),
  ]);

  const lots=ld.lots||[];
  const sales=hd.prices||[];
  const lTotal=ld.total||0, sTotal=hd.total||0;
  const lPages=Math.max(1,Math.ceil(lTotal/S.lotPP));
  const sPages=Math.max(1,Math.ceil(sTotal/S.salePP));
  _aucState={id,lp,sp};

  let h='<a class="back" href="#/item/'+id+'">← '+nm+'</a>';

  // Header with icon
  h+='<div class="auc-header"><div class="auc-header-icon">'+ICO(item.icon)+'</div><div class="auc-header-info"><div class="auc-header-name" style="color:var(--rk-'+colorCssVar(item.color)+')">'+nm+'</div><div class="auc-header-sub">📊 Аукцион</div></div></div>';

  // Sync status
  if(syncSt.total_api>0){
    const pct=syncSt.total_stored && syncSt.total_api ? Math.min(100,Math.round(syncSt.total_stored/syncSt.total_api*100)) : 0;
    if(!syncSt.synced){
      h+='<div class="sync-bar">📥 История: '+fmtK(syncSt.total_stored)+' / '+fmtK(syncSt.total_api)+' продаж загружено ('+pct+'%)<div class="sync-progress"><div class="sync-progress-fill" style="width:'+pct+'%"></div></div></div>';
    }
  }

  // ── Price Chart ──
  h+='<div class="chart-wrap"><div class="chart-header"><div class="chart-title">📈 График цен</div><div class="chart-period">';
  for(const[d,l] of[[7,'7д'],[30,'30д'],[90,'90д']]){
    h+='<button class="'+(S.chartDays===d?'act':'')+'" onclick="setChartDays('+d+')">'+l+'</button>';
  }
  h+='</div></div><div id="price-chart"></div></div>';

  // ── Active Lots ──
  h+='<div class="sec">Активные лоты · '+fmtK(lTotal)+'</div>';

  // Filters row
  h+='<div class="filter-row">';
  h+='<select onchange="setLotSort(this.value)">';
  for(const[v,l] of[['buyout_price|asc','Цена ↑'],['buyout_price|desc','Цена ↓'],['time_created|desc','Новые']]){
    h+='<option value="'+v+'"'+(S.lotSort+'|'+S.lotOrder===v?' selected':'')+'>'+l+'</option>';
  }
  h+='</select>';
  if(isA){
    h+='<select onchange="setLotQlt(this.value)">';
    h+='<option value="all"'+(S.lotQlt==='all'?' selected':'')+'>Все качества</option>';
    for(const[v,l] of[['0','Обычный'],['1','Необычный'],['2','Особый'],['3','Редкий'],['4','Исключ.'],['5','Легенд.']]){
      h+='<option value="'+v+'"'+(S.lotQlt===v?' selected':'')+'>'+l+'</option>';
    }
    h+='</select>';
  }
  h+=ppSel(S.lotPP,[10,20,50],'lot');
  h+='</div>';

  if(lots.length){
    h+='<div class="card">';
    for(const l of lots){
      const pr=l.buyoutPrice||l.currentPrice||l.startPrice||0;
      const isBuyout=l.buyoutPrice>0;
      let meta='<span class="lot-type '+(isBuyout?'buyout':'bid')+'">'+(isBuyout?'Выкуп':'Ставка')+'</span>';
      if(isA){const{q,u}=parseQU(l.additional);meta+=qb(q)+(u>0?' '+upg(u):'');}
      h+='<div class="lot-card"><div class="lot-price">'+fmt(pr)+' ₽</div><div class="lot-meta">'+meta+'</div><div class="lot-expire">'+fmtRemain(l.endTime)+'</div></div>';
    }
    h+='</div>';
    if(lPages>1)h+=pgBar(lp,lPages,"P_auc('"+id+"',{p},"+sp+")");
  } else h+=emptyMsg('Нет активных лотов');

  // ── Sales History ──
  h+='<div class="sec">История продаж · '+fmtK(sTotal)+'</div>';

  // History filters
  h+='<div class="filter-row">';
  h+='<select onchange="setSaleSort(this.value)">';
  for(const[v,l] of[['time_desc','Новые ↓'],['time_asc','Старые ↑'],['price_desc','Дорогие ↓'],['price_asc','Дешёвые ↑']]){
    h+='<option value="'+v+'"'+(S.saleSort===v?' selected':'')+'>'+l+'</option>';
  }
  h+='</select>';
  if(isA){
    h+='<select onchange="setSaleQlt(this.value)">';
    h+='<option value="all"'+(S.saleQlt==='all'?' selected':'')+'>Все качества</option>';
    for(const[v,l] of[['0','Обычный'],['1','Необычный'],['2','Особый'],['3','Редкий'],['4','Исключ.'],['5','Легенд.']]){
      h+='<option value="'+v+'"'+(S.saleQlt===v?' selected':'')+'>'+l+'</option>';
    }
    h+='</select>';
    h+='<select onchange="setSaleUpg(this.value)">';
    h+='<option value="all"'+(S.saleUpg==='all'?' selected':'')+'>Любая заточка</option>';
    for(let i=0;i<=15;i++){
      h+='<option value="'+i+'"'+(S.saleUpg===String(i)?' selected':'')+'>+'+i+'</option>';
    }
    h+='</select>';
  }
  h+=ppSel(S.salePP,[10,20,50],'sale');
  h+='</div>';

  if(sales.length){
    h+='<div class="card">';
    for(const s of sales){
      let meta='';
      if(isA){const{q,u}=parseQU(s.additional);meta=qb(q)+(u>0?' '+upg(u):'');}
      if(s.amount>1)meta+='<span class="sale-amount">×'+s.amount+'</span>';
      h+='<div class="sale-row"><div class="sale-price">'+fmt(s.price)+' ₽</div><div class="sale-meta">'+meta+'</div><div class="sale-date">'+fmtSaleDate(s.time)+'</div></div>';
    }
    h+='</div>';
    if(sPages>1)h+=pgBar(sp,sPages,"P_auc('"+id+"',"+lp+",{p})");
  } else h+=emptyMsg('Нет данных о продажах');

  render(h);

  // Render chart after DOM is ready
  _renderPriceChart(chartD.points || []);
}

/* ── Auction filter setters ── */
function setLotSort(v){const[s,o]=v.split('|');S.lotSort=s;S.lotOrder=o;saveS();if(_aucState.id)P_auc(_aucState.id,1,_aucState.sp||1)}
function setLotQlt(v){S.lotQlt=v;saveS();if(_aucState.id)P_auc(_aucState.id,1,_aucState.sp||1)}
function setSaleQlt(v){S.saleQlt=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,1)}
function setSaleUpg(v){S.saleUpg=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,1)}
function setSaleSort(v){S.saleSort=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,_aucState.sp||1)}
function setChartDays(d){S.chartDays=d;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,_aucState.sp||1)}

/* ── Price Chart (lightweight-charts) ── */
function _renderPriceChart(points){
  const el=document.getElementById('price-chart');
  if(!el)return;
  if(!points||!points.length){
    el.innerHTML='<div class="chart-empty">📊 Нет данных для графика</div>';
    return;
  }
  if(typeof LightweightCharts==='undefined'){
    el.innerHTML='<div class="chart-empty">Загрузка графика...</div>';
    return;
  }
  const dark=isDark();
  const chart=LightweightCharts.createChart(el,{
    width:el.clientWidth,
    height:200,
    layout:{background:{type:'solid',color:'transparent'},textColor:dark?'#9090a8':'#555570',fontSize:10},
    grid:{vertLines:{color:dark?'rgba(255,255,255,.04)':'rgba(0,0,0,.06)'},horzLines:{color:dark?'rgba(255,255,255,.04)':'rgba(0,0,0,.06)'}},
    rightPriceScale:{borderColor:'transparent'},
    timeScale:{borderColor:'transparent',timeVisible:false},
    crosshair:{mode:0},
  });
  const areaSeries=chart.addAreaSeries({
    topColor:dark?'rgba(212,164,58,.3)':'rgba(184,134,30,.25)',
    bottomColor:dark?'rgba(212,164,58,.02)':'rgba(184,134,30,.02)',
    lineColor:dark?'#d4a43a':'#b8861e',
    lineWidth:2,
    priceFormat:{type:'custom',formatter:v=>fmt(v)+' ₽'},
  });
  const data=points.map(p=>({time:p.date,value:p.avg}));
  areaSeries.setData(data);

  // Min line
  const minSeries=chart.addLineSeries({color:dark?'#22c55e':'#16a34a',lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false});
  minSeries.setData(points.map(p=>({time:p.date,value:p.min})));

  chart.timeScale().fitContent();
  new ResizeObserver(()=>{chart.applyOptions({width:el.clientWidth})}).observe(el);
}

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
  b.innerHTML=skelRows(3);
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
  render(skelRows(4));
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
  render(skelRows(5));
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
  render(skelRows(3));
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
  render(skelCards(4));
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
    const needQuality=d.is_artefact||(d.category&&(d.category.startsWith('weapon/')||d.category.includes('module')));
    _showQualityBlock(!!needQuality);
  }catch(e){
    document.getElementById('mc-selected').innerHTML='<div class="card" style="padding:10px 12px;margin:8px 0"><div style="font-weight:800">✅ '+id+'</div></div>';
    _showQualityBlock(false);
  }
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
  render(skelCards(3));
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
let _chatPoll=null,_stickers=null,_replyTo=null,_stickerPanelOpen=false;
const REACTIONS_LIST=['👍','❤️','🔥','😂','😢','💀','🎉','💎','☢️','👎'];

function userColor(u){
  if(u&&u.chat_color)return u.chat_color;
  const colors=['#e57373','#f06292','#ba68c8','#9575cd','#7986cb','#64b5f6','#4fc3f7','#4dd0e1','#4db6ac','#81c784','#aed581','#dce775','#fff176','#ffd54f','#ffb74d','#ff8a65'];
  const id=u?u.id:0;
  return colors[id%colors.length];
}
function repBadge(r){
  if(!r)return'';
  if(r>0)return'<span class="rep pos">+'+r+'</span>';
  if(r<0)return'<span class="rep neg">'+r+'</span>';
  return'';
}
function _chatAvatar(u,size){
  if(!u)return'<div class="ch-av'+(size?' ch-av-'+size:'')+'">👤</div>';
  const cls='ch-av'+(size?' ch-av-'+size:'');
  const onlineDot=(u.is_online)?'<div class="online-dot'+(size==='sm'?' online-dot-sm':'')+(size==='lg'?' online-dot-lg':'')+'"></div>':'';
  if(u.avatar_url)return'<div class="'+cls+'"><img src="'+u.avatar_url+'" alt="">'+onlineDot+'</div>';
  const initial=(u.display_name||'?').charAt(0).toUpperCase();
  const bg=userColor(u);
  return'<div class="'+cls+'" style="background:'+bg+';color:#fff;font-weight:800">'+initial+onlineDot+'</div>';
}

async function P_chat(channel){
  channel=channel||S.chatCh||'general';
  S.chatCh=channel;saveS();
  if(_chatPoll){clearTimeout(_chatPoll);_chatPoll=null}
  _replyTo=null;_stickerPanelOpen=false;
  const isDM=channel.startsWith('dm:');

  // Load stickers once
  if(!_stickers){try{_stickers=await API.get('/api/chat/stickers')}catch(e){_stickers=[]}}

  render(skelRows(5));

  let h='';

  if(isDM){
    const dmUser=await _getDMPartner(channel);
    const av=_chatAvatar(dmUser,'sm');
    const name=dmUser?dmUser.display_name:'Пользователь';
    const dmUserId=dmUser?dmUser.id:0;
    const onlineText=dmUser&&dmUser.is_online?'<span style="font-size:10px;color:var(--grn);margin-left:6px">● онлайн</span>':'';
    h+='<div class="ch-header">';
    h+='<div class="ch-header-back" onclick="go(\'#/chat/dm-list\')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18"><path d="M15 18l-6-6 6-6"/></svg></div>';
    h+='<div class="ch-header-user" onclick="'+(dmUser?'go(\'#/user/'+dmUser.id+'\')':'')+'" style="flex:1">';
    h+=av;
    h+='<div class="ch-header-name">'+name+onlineText+'</div>';
    h+='</div>';
    // DM actions menu
    h+='<div class="ch-header-actions">';
    h+='<button class="ch-header-btn" onclick="deleteDMChat(\''+channel+'\')" title="Удалить чат">🗑</button>';
    if(dmUserId)h+='<button class="ch-header-btn" onclick="blockUserFromChat('+dmUserId+',\''+esc(name)+'\')" title="Заблокировать">🚫</button>';
    h+='</div>';
    h+='</div>';
  } else {
    h+='<div class="ch-tabs">';
    h+='<div class="ch-tab'+(channel==='general'?' act':'')+'" onclick="go(\'#/chat/general\')"><span class="ch-tab-icon">💬</span>Общий</div>';
    h+='<div class="ch-tab'+(channel==='trading'?' act':'')+'" onclick="go(\'#/chat/trading\')"><span class="ch-tab-icon">💰</span>Торговый</div>';
    h+='<div class="ch-tab'+(channel==='dm-list'?' act':'')+'" onclick="go(\'#/chat/dm-list\')"><span class="ch-tab-icon">✉️</span>Личные</div>';
    h+='</div>';
  }

  if(channel==='dm-list'){
    // Mark notifications as read when viewing DM list
    try{await API.post('/api/notifications/read',{})}catch(e){}
    _updateUnreadBadge();
    try{
      const dms=await API.get('/api/chat/dm-list');
      if(!dms.length){
        h+='<div class="ch-empty"><div class="ch-empty-icon">✉️</div><div class="ch-empty-text">Нет личных сообщений</div><div class="ch-empty-sub">Напишите кому-нибудь из профиля</div></div>';
      } else {
        h+='<div class="dm-list">';
        for(const d of dms){
          const u=d.user||{};
          const av=_chatAvatar(u,'md');
          const name=u.display_name||'Пользователь';
          const last=(d.last_message||'').substring(0,50);
          const time=fmtSaleDate(d.last_at);
          h+='<div class="dm-row" onclick="go(\'#/chat/'+d.channel+'\')">';
          h+=av;
          h+='<div class="dm-row-body"><div class="dm-row-top"><span class="dm-row-name">'+name+'</span><span class="dm-row-time">'+time+'</span></div><div class="dm-row-preview">'+escHtml(last)+'</div></div>';
          h+='</div>';
        }
        h+='</div>';
      }
    }catch(e){
      h+='<div class="ch-empty"><div class="ch-empty-icon">🔐</div><div class="ch-empty-text">Авторизуйтесь через Telegram</div></div>';
    }
    render(h);
    return;
  }

  const msgs=await API.get('/api/chat/'+channel+'/messages?limit=50');
  h+='<div class="ch-messages" id="chat-msgs">';
  if(!msgs.length){
    h+='<div class="ch-empty" style="margin:40px 0"><div class="ch-empty-icon">💬</div><div class="ch-empty-text">Пока пусто</div><div class="ch-empty-sub">Напишите первое сообщение!</div></div>';
  }
  for(const m of msgs)h+=chatMsg(m);
  h+='</div>';

  // Input area (with sticker toggle and reply bar placeholder)
  h+='<div class="ch-input-wrap" id="chat-input-wrap">';
  h+='<div id="reply-bar"></div>';
  h+='<div style="position:relative" id="sticker-anchor"></div>';
  h+='<div class="ch-input">';
  h+='<button class="sticker-toggle" onclick="toggleStickerPanel(\''+channel+'\')" title="Стикеры">😀</button>';
  h+='<input id="chat-in" placeholder="Сообщение..." onkeypress="if(event.key===\'Enter\')sendChat(\''+channel+'\')">';
  h+='<button onclick="sendChat(\''+channel+'\')"><svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>';
  h+='</div></div>';

  render(h);
  const box=document.getElementById('chat-msgs');
  if(box)box.scrollTop=box.scrollHeight;
  _ctx.chatLastId=msgs.length?msgs[msgs.length-1].id:0;
  _initChatGestures();
  startChatPoll(channel);
  _startHeartbeat();
}

async function _getDMPartner(channel){
  try{
    const me=await getMe();
    if(!me)return null;
    const parts=channel.replace('dm:','').split('_');
    const otherId=parts.find(id=>parseInt(id)!==me.id);
    if(!otherId)return null;
    return await API.get('/api/users/'+otherId);
  }catch(e){return null}
}

function chatMsg(m){
  const u=m.user||{id:0,display_name:'Аноним'};
  const av=_chatAvatar(u);
  const color=userColor(u);
  const rep=repBadge(u.reputation);

  // Reply quote
  let replyHtml='';
  if(m.reply_to){
    const r=m.reply_to;
    const rColor=r.user_color||'var(--acc)';
    const rText=r.sticker?'['+r.sticker.label+']':escHtml(r.text||'');
    replyHtml='<div class="ch-reply" onclick="scrollToMsg('+r.id+')"><span class="ch-reply-name" style="color:'+rColor+'">'+r.user_name+'</span><span class="ch-reply-text">'+rText+'</span></div>';
  }

  // Sticker content
  let contentHtml='';
  if(m.sticker){
    contentHtml='<div class="ch-sticker">'+m.sticker.emoji+'</div><div class="ch-sticker-label">'+m.sticker.label+'</div>';
    if(m.text)contentHtml+='<div class="ch-msg-text">'+escHtml(m.text)+'</div>';
  } else {
    contentHtml='<div class="ch-msg-text">'+escHtml(m.text)+'</div>';
  }

  // Reactions (compact — only show if they exist)
  let reactHtml='';
  if(m.reactions&&m.reactions.length){
    reactHtml='<div class="ch-reactions">';
    for(const r of m.reactions){
      const myId=_me?_me.id:0;
      const isMine=r.user_ids.includes(myId);
      const safeEmoji=escHtml(r.emoji);
      reactHtml+='<button class="ch-react-btn'+(isMine?' mine':'')+'" data-mid="'+m.id+'" data-emoji="'+safeEmoji+'">'+safeEmoji+'<span class="rc">'+r.count+'</span></button>';
    }
    reactHtml+='</div>';
  }

  // Store reply data as data-attributes for swipe
  const replyName=esc(u.display_name);
  const replyText=esc((m.sticker?'['+m.sticker.label+']':m.text||'').substring(0,60));

  return'<div class="ch-msg" id="msg-'+m.id+'" data-id="'+m.id+'" data-own="'+(m.is_own?'1':'0')+'" data-user-id="'+u.id+'" data-reply-name="'+replyName+'" data-reply-text="'+replyText+'">'
    +'<div class="ch-msg-av" onclick="go(\'#/user/'+u.id+'\')">'+av+'</div>'
    +'<div class="ch-msg-body">'
    +'<div class="ch-msg-head"><span class="ch-msg-name" style="color:'+color+'" onclick="go(\'#/user/'+u.id+'\')">'+u.display_name+'</span>'+rep+'<span class="ch-msg-time">'+fmtChatTime(m.created_at)+'</span></div>'
    +replyHtml
    +contentHtml
    +reactHtml
    +'</div></div>';
}

function fmtChatTime(s){
  if(!s)return'';
  try{const d=new Date(s);return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}catch(e){return''}
}

// ── Reply ──
function setReply(msgId,userName,text){
  _replyTo={id:msgId,name:userName,text:text};
  const bar=document.getElementById('reply-bar');
  if(bar){
    bar.innerHTML='<div class="ch-reply-bar"><span class="ch-reply-bar-name">↩️ '+userName+'</span><span class="ch-reply-bar-text">'+escHtml(text)+'</span><span class="ch-reply-bar-close" onclick="clearReply()">✕</span></div>';
  }
  const inp=document.getElementById('chat-in');
  if(inp)inp.focus();
  haptic('light');
}
function clearReply(){
  _replyTo=null;
  const bar=document.getElementById('reply-bar');
  if(bar)bar.innerHTML='';
}

// ── Reactions ──
async function toggleReact(msgId,emoji){
  haptic('light');
  try{
    const r=await API.post('/api/chat/messages/'+msgId+'/reactions',{emoji:emoji});
    if(r.error){toast('❌ '+r.error);return}
    const el=document.getElementById('msg-'+msgId);
    if(el){
      const existing=el.querySelector('.ch-reactions');
      const newHtml=_buildReactionsHtml(msgId,r.reactions);
      if(existing){
        if(newHtml)existing.outerHTML=newHtml;
        else existing.remove();
      } else if(newHtml){
        const body=el.querySelector('.ch-msg-body');
        if(body)body.insertAdjacentHTML('beforeend',newHtml);
      }
    }
  }catch(e){toast('❌ Авторизуйтесь')}
}
function _buildReactionsHtml(msgId,reactions){
  if(!reactions||!reactions.length)return'';
  let h='<div class="ch-reactions">';
  for(const r of reactions){
    const myId=_me?_me.id:0;
    const isMine=r.user_ids.includes(myId);
    const safeEmoji=escHtml(r.emoji);
    h+='<button class="ch-react-btn'+(isMine?' mine':'')+'" data-mid="'+msgId+'" data-emoji="'+safeEmoji+'">'+safeEmoji+'<span class="rc">'+r.count+'</span></button>';
  }
  h+='</div>';
  return h;
}

function scrollToMsg(id){
  const el=document.getElementById('msg-'+id);
  if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.style.background='var(--acc-bg)';setTimeout(()=>el.style.background='',1500)}
}

// ── Long-press → reaction picker (overlay) ──
let _lpTimer=null,_lpMsgId=null;
function _initChatGestures(){
  const box=document.getElementById('chat-msgs');
  if(!box)return;

  // Long-press for reactions
  box.addEventListener('touchstart',function(e){
    const msg=e.target.closest('.ch-msg[data-id]');
    if(!msg)return;
    _lpMsgId=parseInt(msg.dataset.id);
    _lpTimer=setTimeout(()=>{
      _lpTimer=null;
      haptic('medium');
      _showReactOverlay(_lpMsgId,msg);
    },500);
  },{passive:true});

  box.addEventListener('touchmove',function(){
    if(_lpTimer){clearTimeout(_lpTimer);_lpTimer=null}
  },{passive:true});

  box.addEventListener('touchend',function(){
    if(_lpTimer){clearTimeout(_lpTimer);_lpTimer=null}
  },{passive:true});

  // Desktop: right-click for reactions
  box.addEventListener('contextmenu',function(e){
    const msg=e.target.closest('.ch-msg[data-id]');
    if(!msg)return;
    e.preventDefault();
    const msgId=parseInt(msg.dataset.id);
    haptic('light');
    _showReactOverlay(msgId,msg);
  });

  // Swipe left → reply
  let _swStartX=0,_swStartY=0,_swMsg=null,_swActive=false;
  box.addEventListener('touchstart',function(e){
    const msg=e.target.closest('.ch-msg[data-id]');
    if(!msg)return;
    _swMsg=msg;_swStartX=e.touches[0].clientX;_swStartY=e.touches[0].clientY;_swActive=false;
    msg.style.transition='none';
  },{passive:true});

  box.addEventListener('touchmove',function(e){
    if(!_swMsg)return;
    const dx=e.touches[0].clientX-_swStartX;
    const dy=e.touches[0].clientY-_swStartY;
    // Only horizontal swipe left
    if(!_swActive && Math.abs(dx)>10 && Math.abs(dx)>Math.abs(dy) && dx<0){
      _swActive=true;
    }
    if(_swActive){
      const shift=Math.max(-80,Math.min(0,dx));
      _swMsg.style.transform='translateX('+shift+'px)';
      // Show reply hint when pulled enough
      if(shift<=-50){
        if(!_swMsg.querySelector('.swipe-hint')){
          _swMsg.insertAdjacentHTML('beforeend','<div class="swipe-hint">↩️</div>');
        }
      } else {
        const hint=_swMsg.querySelector('.swipe-hint');
        if(hint)hint.remove();
      }
    }
  },{passive:true});

  box.addEventListener('touchend',function(e){
    if(!_swMsg)return;
    const msg=_swMsg;_swMsg=null;
    msg.style.transition='transform .2s ease';
    msg.style.transform='';
    const hint=msg.querySelector('.swipe-hint');
    if(hint)hint.remove();
    if(_swActive){
      const dx=e.changedTouches[0].clientX-_swStartX;
      if(dx<=-50){
        // Trigger reply
        const msgId=parseInt(msg.dataset.id);
        const name=msg.dataset.replyName||'';
        const text=msg.dataset.replyText||'';
        haptic('light');
        setReply(msgId,name,text);
      }
    }
    _swActive=false;
  },{passive:true});
}

function _showReactOverlay(msgId,msgEl){
  _closeReactOverlay();
  const overlay=document.createElement('div');
  overlay.className='react-overlay';
  overlay.id='react-overlay';

  const rect=msgEl.getBoundingClientRect();
  const picker=document.createElement('div');
  picker.className='react-picker-float';

  // Reactions row
  const REACT=['👍','❤️','🔥','😂','😢','💀','🎉','💎','☢️','👎'];
  for(const emoji of REACT){
    const btn=document.createElement('button');
    btn.textContent=emoji;
    btn.onclick=(ev)=>{ev.stopPropagation();toggleReact(msgId,emoji);_closeReactOverlay()};
    picker.appendChild(btn);
  }

  overlay.appendChild(picker);

  // Action buttons row (delete own / reply / block)
  const actions=document.createElement('div');
  actions.className='react-actions';

  const isOwn=msgEl.dataset.own==='1';
  const userId=msgEl.dataset.userId;

  // Reply
  const replyBtn=document.createElement('button');
  replyBtn.className='react-action-btn';
  replyBtn.innerHTML='↩️ Ответить';
  replyBtn.onclick=(ev)=>{
    ev.stopPropagation();
    const name=msgEl.dataset.replyName||'';
    const text=msgEl.dataset.replyText||'';
    setReply(msgId,name,text);
    _closeReactOverlay();
  };
  actions.appendChild(replyBtn);

  // Delete own message
  if(isOwn){
    const delBtn=document.createElement('button');
    delBtn.className='react-action-btn react-action-danger';
    delBtn.innerHTML='🗑 Удалить';
    delBtn.onclick=async(ev)=>{
      ev.stopPropagation();
      _closeReactOverlay();
      if(!confirm('Удалить сообщение?'))return;
      try{
        const r=await API.del('/api/chat/messages/'+msgId);
        if(r.ok){
          const el=document.getElementById('msg-'+msgId);
          if(el)el.remove();
          toast('🗑 Удалено');
        } else {
          toast('❌ '+(r.error||'Ошибка'));
        }
      }catch(e){toast('❌ Ошибка')}
    };
    actions.appendChild(delBtn);
  }

  overlay.appendChild(actions);
  overlay.onclick=()=>_closeReactOverlay();
  document.body.appendChild(overlay);

  requestAnimationFrame(()=>{
    const ph=picker.offsetHeight+actions.offsetHeight+8;
    let top=rect.top-ph-8;
    if(top<10)top=rect.bottom+8;
    picker.style.top=top+'px';
    picker.style.left=Math.max(10,Math.min(rect.left,window.innerWidth-picker.offsetWidth-10))+'px';
    actions.style.top=(top+picker.offsetHeight+4)+'px';
    actions.style.left=picker.style.left;
  });
}

function _closeReactOverlay(){
  const o=document.getElementById('react-overlay');
  if(o)o.remove();
}

// Event delegation for existing reaction badges (click to toggle)
document.addEventListener('click',function(ev){
  const btn=ev.target.closest('.ch-react-btn[data-mid][data-emoji]');
  if(!btn)return;
  const mid=parseInt(btn.dataset.mid);
  const emoji=btn.dataset.emoji;
  if(mid&&emoji)toggleReact(mid,emoji);
});
function toggleStickerPanel(ch){
  _stickerPanelOpen=!_stickerPanelOpen;
  const anchor=document.getElementById('sticker-anchor');
  if(!anchor)return;
  if(!_stickerPanelOpen){anchor.innerHTML='';return}
  const stickers=_stickers||[];
  let h='<div class="sticker-panel">';
  for(const s of stickers){
    h+='<div class="sticker-item" onclick="sendSticker(\''+ch+'\',\''+s.code+'\')"><div class="sticker-emoji">'+s.emoji+'</div><div class="sticker-label">'+s.label+'</div></div>';
  }
  h+='</div>';
  anchor.innerHTML=h;
}
async function sendSticker(ch,code){
  _stickerPanelOpen=false;
  const anchor=document.getElementById('sticker-anchor');
  if(anchor)anchor.innerHTML='';
  haptic('medium');
  try{
    const body={text:'',sticker:code,reply_to_id:_replyTo?_replyTo.id:0};
    const r=await API.post('/api/chat/'+ch+'/messages',body);
    if(r.error){toast('❌ '+r.error);return}
    clearReply();
    const box=document.getElementById('chat-msgs');
    if(box){
      const emp=box.querySelector('.ch-empty');if(emp)emp.remove();
      box.insertAdjacentHTML('beforeend',chatMsg(r));
      box.scrollTop=box.scrollHeight;
      _ctx.chatLastId=r.id;
    }
  }catch(e){toast('❌ Авторизуйтесь')}
}

async function sendChat(ch){
  const inp=document.getElementById('chat-in');
  if(!inp||!inp.value.trim())return;
  const text=inp.value.trim();
  inp.value='';
  _stickerPanelOpen=false;
  const anchor=document.getElementById('sticker-anchor');
  if(anchor)anchor.innerHTML='';
  try{
    const body={text:text,reply_to_id:_replyTo?_replyTo.id:0};
    const r=await API.post('/api/chat/'+ch+'/messages',body);
    if(r.error){toast('❌ '+r.error);inp.value=text;return}
    clearReply();
    const box=document.getElementById('chat-msgs');
    if(box){
      const emp=box.querySelector('.ch-empty');if(emp)emp.remove();
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

// ── Heartbeat for online status ──
let _hbInterval=null;
function _startHeartbeat(){
  if(_hbInterval)return;
  async function beat(){try{await API.post('/api/heartbeat',{})}catch(e){}}
  beat();
  _hbInterval=setInterval(beat,60000);
}

// ── DM actions ──
async function deleteDMChat(channel){
  if(!confirm('Удалить всю переписку?'))return;
  try{
    const r=await API.del('/api/chat/dm-channel/'+encodeURIComponent(channel));
    if(r.ok){toast('🗑 Чат удалён');go('#/chat/dm-list')}
    else toast('❌ '+(r.error||'Ошибка'));
  }catch(e){toast('❌ Ошибка')}
}
async function blockUserFromChat(userId,name){
  if(!confirm('Заблокировать '+name+'? Вы не будете видеть сообщения друг друга.'))return;
  try{
    const r=await API.post('/api/users/'+userId+'/block',{});
    if(r.ok||r.blocked){toast('🚫 '+name+' заблокирован');go('#/chat/dm-list')}
    else toast('❌ '+(r.error||'Ошибка'));
  }catch(e){toast('❌ Ошибка')}
}

// ── Blocked users page ──
async function P_blocked(){
  render(skelRows(3));
  try{
    const list=await API.get('/api/blocked-users');
    let h='<a class="back" href="#/profile">← Профиль</a>';
    h+='<div class="hdr">🚫 Заблокированные</div>';
    if(!list.length){
      h+='<div class="ch-empty"><div class="ch-empty-icon">✅</div><div class="ch-empty-text">Нет заблокированных</div></div>';
    } else {
      for(const u of list){
        h+='<div class="card" style="display:flex;align-items:center;gap:12px;padding:12px;margin-bottom:6px">';
        h+=_chatAvatar(u,'md');
        h+='<div style="flex:1;min-width:0"><div style="font-weight:700;font-size:13px">'+escHtml(u.display_name)+'</div>';
        h+='<div style="font-size:10px;color:var(--t3)">Заблокирован '+fmtSaleDate(u.blocked_at)+'</div></div>';
        h+='<button class="btn btn-sm btn-r" onclick="unblockUser('+u.id+')">Разблокировать</button>';
        h+='</div>';
      }
    }
    render(h);
  }catch(e){render(emptyMsg('Авторизуйтесь через Telegram'))}
}
async function unblockUser(userId){
  try{
    const r=await API.del('/api/users/'+userId+'/block');
    toast('✅ Разблокирован');
    P_blocked();
  }catch(e){toast('❌ Ошибка')}
}


/* ═══════════ PROFILE ═══════════ */
async function P_profile(sub){
  if(sub==='edit'){await P_profile_edit();return}
  render(skelRows(3));
  let me,emiS;
  try{[me,emiS]=await Promise.all([API.get('/api/me'),API.get('/api/emission/settings').catch(()=>({enabled:false}))])}catch(e){}
  if(!me||!me.id){
    render('<div class="hdr">👤 Профиль</div><div class="empty"><div class="empty-i">🔐</div><div class="empty-t">Откройте через Telegram Mini App для авторизации</div></div>');
    return;
  }
  _me=me;
  const av=me.avatar_url?'<img src="'+me.avatar_url+'" alt="">':'👤';
  const rep=me.reputation>0?'<span class="rep pos">+'+me.reputation+'</span>':(me.reputation<0?'<span class="rep neg">'+me.reputation+'</span>':'');
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
  h+='<div style="margin-top:8px"><button class="btn btn-o" onclick="go(\'#/blocked\')">🚫 Заблокированные</button></div>';

  // Settings
  h+='<div class="sec" style="margin-top:18px">⚙️ Настройки</div>';

  // Theme toggle
  const isLight=(document.documentElement.dataset.theme||'dark')==='light';
  h+='<div class="theme-toggle" onclick="toggleTheme();P_profile()"><div><div class="theme-toggle-label">'+(isLight?'☀️ Светлая тема':'🌙 Тёмная тема')+'</div><div class="theme-toggle-sub">Переключить оформление</div></div><div class="theme-switch'+(isLight?' on':'')+'"></div></div>';

  // Emission
  const emiOn=emiS&&emiS.enabled;
  h+='<div class="card" style="padding:12px;display:flex;align-items:center;justify-content:space-between">';
  h+='<div><div style="font-weight:700;font-size:13px">☢️ Уведомления о выбросе</div><div style="font-size:11px;color:var(--t3)">При начале и конце выброса</div></div>';
  h+='<button class="btn btn-sm '+(emiOn?'btn-r':'btn-g')+'" onclick="toggleEmission()" style="flex-shrink:0">'+(emiOn?'🔕 Выкл':'🔔 Вкл')+'</button>';
  h+='</div>';
  render(h);
}
async function toggleEmission(){
  try{
    const r=await API.post('/api/emission/settings',{});
    toast(r.enabled?'🔔 Уведомления включены':'🔕 Уведомления выключены');
    P_profile();
  }catch(e){toast('❌ Ошибка')}
}
async function P_profile_edit(){
  render(skelRows(4));
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
    display_name:document.getElementById('pe-name').value.trim()||null,
    game_nickname:document.getElementById('pe-game').value.trim()||null,
    discord:document.getElementById('pe-disc').value.trim()||null,
    bio:document.getElementById('pe-bio').value.trim()||null,
  };
  try{
    const r=await API.put('/api/me',d);
    if(r&&r.error){toast('❌ '+r.error);return}
    toast('✅ Сохранено');_me=null;go('#/profile');
  }catch(e){toast('❌ Ошибка: '+e.message)}
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
  render(skelRows(3));
  const u=await API.get('/api/users/'+uid);
  if(u.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Не найден'));return}
  const av=u.avatar_url?'<img src="'+u.avatar_url+'" alt="">':'👤';
  const onlineHtml=u.is_online?'<span style="font-size:11px;color:var(--grn);margin-left:6px">● онлайн</span>':'';
  const rep=u.reputation>0?'<span class="rep pos">+'+u.reputation+'</span>':(u.reputation<0?'<span class="rep neg">'+u.reputation+'</span>':'');
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="profile-header">';
  h+='<div class="profile-avatar" style="cursor:default;border-color:var(--brd)">'+av+(u.is_online?'<div class="online-dot online-dot-lg"></div>':'')+'</div>';
  h+='<div class="profile-info"><div class="profile-name">'+u.display_name+' '+rep+onlineHtml+'</div>';
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
  let h='<span style="font-size:10px;color:var(--t3);margin-left:auto">На стр:</span>';
  for(const v of opts)h+='<button class="'+(v===cur?'act':'')+'" style="background:var(--surf);border:1px solid var(--brd);color:'+(v===cur?'var(--acc)':'var(--t2)')+';border-radius:var(--r-xs);padding:3px 8px;font-size:9px;cursor:pointer;font-family:var(--font)"'+(v===cur?' style="border-color:var(--acc)"':'')+ ' onclick="setPP(\''+key+'\','+v+')">'+v+'</button>';
  return h;
}
function pgBar(cur,tot,tpl){
  return'<div class="pgr"><button '+(cur<=1?'disabled':'')+' onclick="'+tpl.replace('{p}',cur-1)+'">‹</button><span class="pi">'+cur+' / '+tot+'</span><button '+(cur>=tot?'disabled':'')+' onclick="'+tpl.replace('{p}',cur+1)+'">›</button></div>';
}
function emptyMsg(t){return'<div class="empty"><div class="empty-t" style="padding:18px 0">'+t+'</div></div>'}
function warnBox(t,d){return'<div class="warn-box"><span class="warn-icon">⚠️</span><div class="warn-text"><b>'+t+'</b><br>'+d+'</div></div>'}
let _ctx={};
function setPP(key,val){
  if(key==='lot'){S.lotPP=val;saveS();if(_aucState.id)P_auc(_aucState.id,1,_aucState.sp||1)}
  else if(key==='sale'){S.salePP=val;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,1)}
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
