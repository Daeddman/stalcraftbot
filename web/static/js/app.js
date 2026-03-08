/* ═══════════════════════════════════════════
   PerekupHelper SPA — v11
   Stalcraft Trading Hub
   Skeleton · Charts · Filters · Theme
   ═══════════════════════════════════════════ */
const A=document.getElementById('app');
function go(h){location.hash=h}
function _goBack(){history.back()}

/* ── State ── */
let S={lotPP:20,salePP:20,lotSort:'buyout_price',lotOrder:'asc',saleQlt:'all',saleUpg:'all',saleSort:'time_desc',lotQlt:'all',chartQlt:'all',chatCh:'general',searchTab:'market',chartDays:30,mktCat:'all',mktType:'',mktSort:'newest',mktSearch:'',lotView:'list'};
try{Object.assign(S,JSON.parse(localStorage.getItem('ph11')||'{}'))}catch(e){}
function saveS(){localStorage.setItem('ph11',JSON.stringify(S))}

/* ── Cache ── */
const _c=new Map();
function cG(k){const e=_c.get(k);return(e&&Date.now()-e.t<300000)?e.v:null}
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
function render(h){A.innerHTML='<div class="page">'+h+'</div>';A.scrollTop=0;requestAnimationFrame(()=>initRevealAnim())}

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
let _routeId=0;
async function route(){
  const rid=++_routeId;
  const h=location.hash||'#/',p=h.replace('#','').split('/').filter(Boolean),pg=p[0]||'';
  document.querySelectorAll('#tab-bar .tab').forEach(t=>{
    const r=t.dataset.route;
    t.classList.toggle('active',r===h||(r==='#/'&&(h==='#/'||!pg)));
  });
  if(tg&&pg){tg.BackButton.show();tg.BackButton.offClick(_goBack);tg.BackButton.onClick(_goBack)}
  else if(tg){tg.BackButton.hide()}
  _updateUnreadBadge();
  try{
    if(!pg||h==='#/')await P_home(rid);
    else if(pg==='item')await P_item(p[1]);
    else if(pg==='auction')await P_auc(p[1]);
    else if(pg==='search')await P_search();
    else if(pg==='tracked')await P_tracked();
    else if(pg==='clan')await P_clan(p[1]);
    else if(pg==='clans')await P_clans();
    else if(pg==='leaderboard')await P_leaderboard();
    else if(pg==='player')await P_player(decodeURIComponent(p.slice(1).join('/')));
    else if(pg==='market')await P_market(p[1]);
    else if(pg==='market-create')P_market_create();
    else if(pg==='market-my')await P_market_my();
    else if(pg==='chat')await P_chat(p[1]);
    else if(pg==='profile')await P_profile(p[1]);
    else if(pg==='user')await P_user(p[1]);
    else if(pg==='blocked')await P_blocked();
    else if(pg==='compare')await P_compare();
    else await P_home(rid);
  }catch(e){render('<div class="empty"><div class="empty-i">⚠️</div><div class="empty-t">'+e.message+'</div></div>')}
  if(tg)tg.expand();
}
window.addEventListener('hashchange',route);
window.addEventListener('load',()=>{showOnboarding();route()});

/* ═══════════ HOME ═══════════ */
async function P_home(rid){
  // Show cached home instantly if available
  const ck='home_data';
  const cached=cG(ck);
  if(cached){
    _renderHome(cached.emi,cached.mkt,cached.pop);
  } else {
    render(skelBlock()+skelCards(3));
  }
  // Fetch fresh data — single combined endpoint
  try{
    const data=await API.get('/api/home');
    if(rid!==undefined && rid!==_routeId)return;
    const emi=data.emission||{};
    const mkt=data.market||{items:[]};
    const pop=data.popular||[];
    cS(ck,{emi,mkt,pop});
    _emi=emi;_emiTs=Date.now();
    _renderHome(emi,mkt,pop);
  }catch(e){
    // Fallback: 3 parallel calls if combined endpoint fails
    const [emi,mkt,pop]=await Promise.all([
      getEmi(),
      API.get('/api/market?status=active&per_page=6').catch(()=>({items:[]})),
      API.get('/api/popular?limit=8').catch(()=>[]),
    ]);
    if(rid!==undefined && rid!==_routeId)return;
    cS(ck,{emi,mkt,pop});
    _renderHome(emi,mkt,pop);
  }
}
function _renderHome(emi,mkt,pop){
  let h='';
  h+=emiHTML(emi);
  h+='<div class="quick-row">';
  h+='<div class="quick-card" onclick="go(\'#/search\')"><div class="quick-icon">🔍</div><div class="quick-label">Поиск</div></div>';
  h+='<div class="quick-card" onclick="go(\'#/tracked\')"><div class="quick-icon">⭐</div><div class="quick-label">Избранное</div></div>';
  h+='<div class="quick-card" onclick="go(\'#/market\')"><div class="quick-icon">🏪</div><div class="quick-label">Маркет</div></div>';
  h+='<div class="quick-card" onclick="go(\'#/leaderboard\')"><div class="quick-icon">🏆</div><div class="quick-label">Лидерборд</div></div>';
  h+='<div class="quick-card" onclick="go(\'#/clans\')"><div class="quick-icon">🏰</div><div class="quick-label">Кланы</div></div>';
  h+='</div>';
  if(pop&&pop.length){
    h+='<div class="sec">🔥 Популярные предметы</div><div class="hscroll">';
    for(const i of pop){
      let trendH='';
      if(i.trend!=null){
        if(i.trend>0)trendH='<div class="trend up">▲ +'+i.trend+'%</div>';
        else if(i.trend<0)trendH='<div class="trend down">▼ '+i.trend+'%</div>';
        else trendH='<div class="trend flat">— 0%</div>';
      }
      h+='<div class="hcard rk-'+(i.color||'DEFAULT')+'" onclick="haptic();go(\'#/item/'+i.id+'\')"><div class="hcard-img">'+ICO(i.icon)+'</div><div class="hcard-name" style="color:var(--rk-'+colorCssVar(i.color)+')">'+i.name+'</div>'+trendH+'</div>';
    }
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
  render(skelBlock()+'<div style="height:12px"></div>'+skelRows(3));
  const [item,tr,mkt]=await Promise.all([
    API.get('/api/items/'+id),
    API.get('/api/tracked'),
    API.get('/api/market?item_id='+id+'&status=active&per_page=10').catch(()=>({items:[]})),
  ]);
  if(item.error){render('<div class="empty"><div class="empty-i">❌</div><div class="empty-t">Не найден</div></div>');return}
  const isTr=tr.some(t=>t.item_id===id);
  const ok=item.api_supported!==false;
  const rkCls=item.color||'DEFAULT';
  const rkVar=colorCssVar(rkCls);

  let h='<a class="back" onclick="history.back()">← Назад</a>';

  // ── Hero Card ──
  h+='<div class="item-hero rk-'+rkCls+'">';
  h+='<div class="item-hero-glow"></div>';
  h+='<div class="item-hero-icon">'+ICO(item.icon)+'</div>';
  h+='<div class="item-hero-name" style="color:var(--rk-'+rkVar+')">'+item.name+'</div>';
  h+='<div class="item-hero-cat">'+item.category_name;
  if(item.rank_name)h+=' · <span class="rk-pill rk-pill-'+rkCls+'">'+item.rank_name+'</span>';
  h+='</div>';

  // ── Action pills inside hero ──
  h+='<div class="item-actions">';
  if(isTr){
    h+='<button class="item-act-pill act-remove" onclick="event.stopPropagation();haptic(\'medium\');UT(\''+id+'\')"><span class="pill-icon">✕</span>Убрать</button>';
  } else {
    h+='<button class="item-act-pill act-fav" onclick="event.stopPropagation();haptic(\'medium\');TK(\''+id+'\',event)"><span class="pill-icon">⭐</span>В избранное</button>';
  }
  if(ok){
    h+='<a class="item-act-pill act-auc" href="#/auction/'+id+'"><span class="pill-icon">📊</span>Аукцион</a>';
    h+='<button class="item-act-pill act-sell" onclick="event.stopPropagation();go(\'#/market-create\');setTimeout(()=>selectMcItem(\''+id+'\'),200)"><span class="pill-icon">🏪</span>Продать</button>';
  }
  // Compare button — check category compatibility
  const canCmp=_compareIds.length===0||_compareCatMatch(item.category);
  if(canCmp){
    const inCmp=_compareIds.includes(id);
    if(inCmp){
      h+='<button class="item-act-pill act-remove" onclick="event.stopPropagation();removeFromCompare(\''+id+'\');P_item(\''+id+'\')"><span class="pill-icon">✕</span>Убрать из сравнения</button>';
    } else {
      h+='<button class="item-act-pill act-cmp" onclick="event.stopPropagation();_addCompareWithCat(\''+id+'\',\''+item.category+'\');P_item(\''+id+'\')"><span class="pill-icon">⚖️</span>Сравнить</button>';
    }
  }
  if(_compareIds.length>1){
    h+='<a class="item-act-pill act-auc" href="#/compare"><span class="pill-icon">📊</span>К сравнению ('+_compareIds.length+')</a>';
  }
  h+='</div>';
  h+='</div>';

  if(!ok){
    h+='<div class="item-notice">⚠️ Аукцион для этого предмета недоступен через API</div>';
  }

  // ── Market listings ──
  if(mkt.items&&mkt.items.length){
    h+='<div class="item-section-title">🏪 Объявления игроков</div>';
    for(const l of mkt.items)h+=marketCard(l);
  }

  // ── Stats ──
  if(item.stats&&item.stats.length){
    h+='<div class="item-section-title">📋 Характеристики</div>';
    h+='<div class="item-stats-card">';
    for(const s of item.stats){
      let c='';if(s.color==='53C353')c='sg';else if(s.color==='C15252')c='sr';
      h+='<div class="item-stat"><span class="item-stat-k">'+s.key+'</span><span class="item-stat-v '+c+'">'+s.value+'</span></div>';
    }
    h+='</div>';
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
    API.get('/api/auction/'+id+'/chart-data?days='+S.chartDays+(S.chartQlt!=='all'?'&quality='+S.chartQlt:'')).catch(()=>({points:[]})),
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
  h+='<div class="chart-wrap"><div class="chart-header"><div class="chart-title">📈 График цен'+(chartD.expanded?' <span style="font-size:10px;color:var(--t3);font-weight:400">(за всё время)</span>':'')+'</div><div class="chart-controls">';
  // Quality filter for chart (only for artefacts)
  if(isA){
    h+='<select class="chart-qlt-sel" onchange="setChartQlt(this.value)">';
    h+='<option value="all"'+(S.chartQlt==='all'?' selected':'')+'>Все</option>';
    for(const[v,l] of[['0','Обычный'],['1','Необычный'],['2','Особый'],['3','Редкий'],['4','Исключ.'],['5','Легенд.']]){
      h+='<option value="'+v+'"'+(S.chartQlt===v?' selected':'')+'>'+l+'</option>';
    }
    h+='</select>';
  }
  h+='<div class="chart-period">';
  for(const[d,l] of[[7,'7д'],[30,'30д'],[90,'90д'],[0,'Всё']]){
    h+='<button class="'+(S.chartDays===d?'act':'')+'" onclick="setChartDays('+d+')">'+l+'</button>';
  }
  h+='</div></div></div><div id="price-chart"></div></div>';

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
  h+=viewToggle(S.lotView);
  h+='</div>';

  const isGrid=S.lotView==='grid';
  if(lots.length){
    h+='<div class="'+(isGrid?'lot-grid':'card')+'">';
    for(const l of lots){
      const pr=l.buyoutPrice||l.currentPrice||l.startPrice||0;
      const isBuyout=l.buyoutPrice>0;
      let meta='<span class="lot-type '+(isBuyout?'buyout':'bid')+'">'+(isBuyout?'Выкуп':'Ставка')+'</span>';
      if(isA){const{q,u}=parseQU(l.additional);if(q>=0)meta+=qb(q);if(u>0)meta+=' '+upg(u);}
      if(isGrid){
        h+='<div class="lot-grid-card reveal-on-scroll"><div class="lot-price">'+fmt(pr)+' ₽</div><div class="lot-meta">'+meta+'</div><div class="lot-expire">'+fmtRemain(l.endTime)+'</div></div>';
      } else {
        h+='<div class="lot-card reveal-on-scroll"><div class="lot-price">'+fmt(pr)+' ₽</div><div class="lot-meta">'+meta+'</div><div class="lot-expire">'+fmtRemain(l.endTime)+'</div></div>';
      }
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
      if(isA){const{q,u}=parseQU(s.additional);if(q>=0)meta=qb(q);if(u>0)meta+=' '+upg(u);}
      if(s.amount>1)meta+='<span class="sale-amount">×'+s.amount+'</span>';
      h+='<div class="sale-row"><div class="sale-price">'+fmt(s.price)+' ₽</div><div class="sale-meta">'+meta+'</div><div class="sale-date">'+fmtSaleDate(s.time)+'</div></div>';
    }
    h+='</div>';
    if(sPages>1)h+=pgBar(sp,sPages,"P_auc('"+id+"',"+lp+",{p})");
  } else h+=emptyMsg('Нет данных о продажах');

  render(h);

  // Render chart after DOM is ready
  _renderPriceChart(chartD.points || []);

  // First-visit tooltips
  const vtBtn=document.querySelector('.vt-btn');
  if(vtBtn)showTip('lot_view','Переключайте между списком и сеткой',vtBtn);
  const chartEl=document.querySelector('.chart-wrap');
  if(chartEl&&chartD.points&&chartD.points.length)showTip('chart_interact','Нажмите на график чтобы увидеть цену в конкретный день',chartEl);
}

/* ── Auction filter setters ── */
function setLotSort(v){const[s,o]=v.split('|');S.lotSort=s;S.lotOrder=o;saveS();if(_aucState.id)P_auc(_aucState.id,1,_aucState.sp||1)}
function setLotQlt(v){S.lotQlt=v;saveS();if(_aucState.id)P_auc(_aucState.id,1,_aucState.sp||1)}
function setSaleQlt(v){S.saleQlt=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,1)}
function setSaleUpg(v){S.saleUpg=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,1)}
function setSaleSort(v){S.saleSort=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,_aucState.sp||1)}
function setChartDays(d){S.chartDays=d;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,_aucState.sp||1)}
function setChartQlt(v){S.chartQlt=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,1)}
function setLotView(v){S.lotView=v;saveS();if(_aucState.id)P_auc(_aucState.id,_aucState.lp||1,_aucState.sp||1)}

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

/* ═══════════ COMPARE ═══════════ */
let _compareIds=[];
let _compareCat='';  // stored category for compatibility check

function _getCompareGroup(cat){
  // Group categories for comparison: same subcategory must match
  if(!cat)return'';
  // For artefacts: artefact/electrophysical, artefact/gravitational, etc. → compare within subcat
  // For armor: armor/combined, etc. → compare within subcat
  // For weapons: weapon/pistol, etc. → compare within subcat
  // For attachments: attachment/muzzle, etc. → compare within subcat
  return cat;  // exact category match
}

function _compareCatMatch(cat){
  if(!_compareIds.length||!_compareCat)return true;
  return _getCompareGroup(cat)===_compareCat;
}

function _addCompareWithCat(id,cat){
  if(_compareIds.length>=5){toast('Максимум 5 предметов');return}
  if(_compareIds.includes(id))return;
  if(_compareIds.length===0)_compareCat=_getCompareGroup(cat);
  if(!_compareCatMatch(cat)){toast('⚠️ Можно сравнивать только предметы одной категории');return}
  _compareIds.push(id);
  localStorage.setItem('ph_compare',JSON.stringify(_compareIds));
  localStorage.setItem('ph_compare_cat',_compareCat);
  toast('⚖️ Добавлено к сравнению ('+_compareIds.length+')');
}

function addToCompare(id){_addCompareWithCat(id,'')}
function removeFromCompare(id){
  _compareIds=_compareIds.filter(x=>x!==id);
  localStorage.setItem('ph_compare',JSON.stringify(_compareIds));
  if(!_compareIds.length){_compareCat='';localStorage.removeItem('ph_compare_cat')}
}
(function(){try{_compareIds=JSON.parse(localStorage.getItem('ph_compare'))||[];_compareCat=localStorage.getItem('ph_compare_cat')||''}catch(e){_compareIds=[];_compareCat=''}})();

async function P_compare(){
  if(!_compareIds.length){
    render('<a class="back" onclick="history.back()">← Назад</a><div class="empty"><div class="empty-i">📊</div><div class="empty-t">Нет предметов для сравнения</div><div class="empty-sub">Добавьте предметы через кнопку «📊 Сравнить» на странице предмета</div></div>');
    return;
  }
  render(skelRows(4));
  let data;
  try{data=await API.get('/api/compare?ids='+_compareIds.join(','))}catch(e){render(emptyMsg('Ошибка загрузки'));return}
  const items=data.items||[];
  if(!items.length){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Предметы не найдены'));return}

  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hdr">📊 Сравнение</div>';

  // Item cards row
  h+='<div class="cmp-cards">';
  for(const it of items){
    const rkVar=colorCssVar(it.color);
    let trendH='';
    if(it.trend!=null){
      if(it.trend>0)trendH='<div class="trend up">▲ +'+it.trend+'%</div>';
      else if(it.trend<0)trendH='<div class="trend down">▼ '+it.trend+'%</div>';
    }
    h+='<div class="cmp-card rk-'+(it.color||'DEFAULT')+'">';
    h+='<button class="cmp-remove" onclick="removeFromCompare(\''+it.id+'\');P_compare()">✕</button>';
    h+='<div class="cmp-icon">'+ICO(it.icon)+'</div>';
    h+='<div class="cmp-name" style="color:var(--rk-'+rkVar+')">'+it.name+'</div>';
    if(it.rank_name)h+='<div class="rk-pill rk-pill-'+it.color+'">'+it.rank_name+'</div>';
    h+=trendH;
    h+='</div>';
  }
  h+='</div>';

  // Stats comparison table
  // Collect all stat keys
  const allKeys=[];const keySet=new Set();
  for(const it of items){
    for(const s of(it.stats||[])){
      if(!keySet.has(s.key)){keySet.add(s.key);allKeys.push(s.key)}
    }
  }
  if(allKeys.length){
    h+='<div class="item-section-title">📋 Характеристики</div>';
    h+='<div class="cmp-table-wrap"><table class="cmp-table"><thead><tr><th></th>';
    for(const it of items)h+='<th style="color:var(--rk-'+colorCssVar(it.color)+')">'+it.name.split(' ')[0]+'</th>';
    h+='</tr></thead><tbody>';
    for(const key of allKeys){
      h+='<tr><td class="cmp-key">'+key+'</td>';
      for(const it of items){
        const st=(it.stats||[]).find(s=>s.key===key);
        if(st){
          let c='';if(st.color==='53C353')c='sg';else if(st.color==='C15252')c='sr';
          h+='<td class="cmp-val '+c+'">'+st.value+'</td>';
        }else{
          h+='<td class="cmp-val" style="color:var(--t3)">—</td>';
        }
      }
      h+='</tr>';
    }
    h+='</tbody></table></div>';
  }

  h+='<button class="btn btn-r btn-sm" style="margin-top:16px" onclick="_compareIds=[];localStorage.removeItem(\'ph_compare\');P_compare()">🗑 Очистить список</button>';
  render(h);
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
    showTip('search_tabs','Переключайтесь между маркетом (объявления игроков) и аукционом (игровые лоты)',document.querySelector('.tabs'));
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
    h+='<div class="card drag-container" id="tracked-list">';
    for(const t of tr){
      h+='<div class="drag-item irow rk-'+(t.color||'DEFAULT')+'" data-id="'+t.item_id+'" onclick="haptic();go(\'#/item/'+t.item_id+'\')">';
      h+='<div class="drag-handle" onclick="event.stopPropagation()">⠿</div>';
      h+='<div class="irow-icon">'+ICO(t.icon)+'</div>';
      h+='<div class="ib"><div class="in">'+t.name+'</div></div>';
      h+='</div>';
    }
    h+='</div>';
  }
  render(h);
  if(tr.length){
    initDragReorder('#tracked-list',ids=>{
      // Save new order
      API.post('/api/tracked/reorder',{ids}).catch(()=>{});
      H.success();
    });
    // First-visit tooltip
    const handle=document.querySelector('.drag-handle');
    if(handle)showTip('drag_reorder','Зажмите ⠿ и перетащите для изменения порядка',handle);
  }
}

/* ═══════════ CLAN (detail) ═══════════ */
const CLAN_RANK_NAMES={RECRUIT:'Рекрут',PLAYER:'Игрок',OFFICER:'Офицер',LEADER:'Лидер'};
async function P_clan(id){
  if(!id){render(emptyMsg('Укажите ID клана'));return}
  render(skelRows(5));
  const [info,members]=await Promise.all([API.get('/api/clan/'+id),API.get('/api/clan/'+id+'/members')]);
  if(info.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Клан не найден: '+info.error));return}
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  // Header
  h+='<div class="clan-detail-hdr">';
  h+='<div class="clan-detail-name">🏰 '+(info.name||id)+'</div>';
  if(info.tag)h+='<div class="clan-detail-tag">['+info.tag+']</div>';
  if(info.alliance)h+='<div style="font-size:11px;color:var(--t3);margin-top:2px">Альянс: '+info.alliance+'</div>';
  h+='</div>';
  if(info.description)h+='<div class="clan-detail-desc">'+escHtml(info.description)+'</div>';
  // Stats
  h+='<div class="clan-stats-row">';
  h+='<div class="clan-stat"><div class="clan-stat-val">'+(info.level||'?')+'</div><div class="clan-stat-lbl">Уровень</div></div>';
  h+='<div class="clan-stat"><div class="clan-stat-val">'+(info.memberCount||0)+'</div><div class="clan-stat-lbl">Участники</div></div>';
  h+='<div class="clan-stat"><div class="clan-stat-val">'+fmtK(info.levelPoints||0)+'</div><div class="clan-stat-lbl">Очки</div></div>';
  h+='</div>';
  if(info.leader)h+='<div style="text-align:center;margin:8px 0;font-size:12px;color:var(--t2)">👑 Лидер: <a style="color:var(--acc);cursor:pointer" onclick="go(\'#/player/'+encodeURIComponent(info.leader)+'\')">'+escHtml(info.leader)+'</a></div>';
  if(info.registrationTime)h+='<div style="text-align:center;font-size:11px;color:var(--t3)">📅 Создан: '+fmtFullDate(new Date(info.registrationTime))+'</div>';
  // Members
  const ml=members.members||members||[];
  if(ml.length){
    h+='<div class="prof-section"><div class="prof-section-hdr">Участники · '+ml.length+'</div>';
    h+='<div class="card" style="padding:0;overflow:hidden">';
    for(const m of ml){
      const name=m.name||m.username||'—';
      const rank=CLAN_RANK_NAMES[m.rank]||m.rank||'—';
      const joined=m.joinTime?fmtFullDate(new Date(m.joinTime)):'';
      h+='<div class="clan-member-row">';
      h+='<div class="clan-member-name" onclick="go(\'#/player/'+encodeURIComponent(name)+'\')">'+escHtml(name)+'</div>';
      h+='<span class="clan-member-rank">'+rank+'</span>';
      if(joined)h+='<span class="clan-member-date">'+joined+'</span>';
      h+='</div>';
    }
    h+='</div></div>';
  }
  render(h);
}

/* ═══════════ PLAYER (game character) ═══════════ */
const STAT_NAMES={
  'player.play_time_h':'Время в игре (ч)',
  'player.pve.kills':'PvE убийства',
  'player.pvp.kills':'PvP убийства',
  'player.pvp.deaths':'PvP смерти',
  'player.artifacts_looted':'Артефактов найдено',
  'player.mutants.killed':'Мутантов убито',
  'player.distance_traveled':'Пройдено (км)',
  'player.quests_completed':'Квестов выполнено',
};
async function P_player(name){
  if(!name){render(emptyMsg('Укажите имя'));return}
  render(skelRows(3));
  const d=await API.get('/api/character/'+encodeURIComponent(name)+'/profile');
  if(d.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg(d.error));return}
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  // Banner & name
  h+='<div class="prof-banner" style="height:80px"></div>';
  h+='<div style="text-align:center;margin-top:-20px;position:relative;z-index:2">';
  h+='<div class="prof-display-name" style="font-size:22px">🎮 '+escHtml(d.username||name)+'</div>';
  if(d.status)h+='<div style="font-size:11px;color:var(--t3);margin-top:2px">'+escHtml(d.status)+'</div>';
  if(d.alliance)h+='<div style="font-size:11px;color:var(--acc);margin-top:2px">⚔️ '+escHtml(d.alliance)+'</div>';
  h+='</div>';
  // Clan info
  if(d.clan&&d.clan.info){
    const ci=d.clan.info;
    h+='<div class="clan-card" style="margin-top:14px" onclick="go(\'#/clan/'+ci.id+'\')">';
    h+='<div class="clan-badge">'+((ci.tag||'?')[0])+'</div>';
    h+='<div class="clan-info"><div class="clan-name">'+(ci.name||ci.id)+'</div>';
    if(ci.tag)h+='<span class="clan-tag">['+ci.tag+']</span>';
    if(d.clan.member)h+='<div class="clan-meta">'+(CLAN_RANK_NAMES[d.clan.member.rank]||d.clan.member.rank||'')+'</div>';
    h+='</div><div class="clan-level">Lvl '+(ci.level||'?')+'</div></div>';
  }
  // Achievements
  if(d.displayedAchievements&&d.displayedAchievements.length){
    h+='<div class="prof-section"><div class="prof-section-hdr">Достижения</div>';
    h+='<div style="display:flex;flex-wrap:wrap;gap:6px">';
    for(const a of d.displayedAchievements){
      h+='<span style="padding:4px 10px;background:var(--surf);border:1px solid var(--brd);border-radius:var(--r-xs);font-size:11px;color:var(--acc)">🏆 '+escHtml(a)+'</span>';
    }
    h+='</div></div>';
  }
  // Stats
  if(d.stats&&d.stats.length){
    h+='<div class="prof-section"><div class="prof-section-hdr">Статистика</div>';
    h+='<div class="prof-info-grid">';
    for(const s of d.stats){
      const label=STAT_NAMES[s.id]||s.id;
      let val=s.value;
      if(typeof val==='object')val=JSON.stringify(val);
      if(s.type==='FLOAT')val=parseFloat(val).toFixed(1);
      h+='<div class="prof-info-card"><div class="pil">'+escHtml(label)+'</div><div class="piv">'+escHtml(String(val))+'</div></div>';
    }
    h+='</div></div>';
  }
  // Last login
  if(d.lastLogin)h+='<div style="text-align:center;font-size:11px;color:var(--t3);margin-top:14px">Посл. вход: '+fmtSaleDate(d.lastLogin)+'</div>';
  render(h);
}

/* ═══════════ LEADERBOARD ═══════════ */
let _lbSort='deals',_lbPeriod='all';
async function P_leaderboard(){
  render(skelRows(6));
  const d=await API.get('/api/leaderboard?sort='+_lbSort+'&period='+_lbPeriod);
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hdr">🏆 Лидерборд трейдеров</div>';
  // Sort tabs
  h+='<div class="tabs">';
  for(const[v,l]of[['deals','Сделки'],['reputation','Репутация'],['volume','Оборот']]){
    h+='<button class="tab-btn'+(_lbSort===v?' act':'')+'" onclick="_lbSort=\''+v+'\';P_leaderboard()">'+l+'</button>';
  }
  h+='</div>';
  // Period
  h+='<div class="sort-bar" style="margin-bottom:14px">';
  for(const[v,l]of[['week','Неделя'],['month','Месяц'],['all','Все время']]){
    h+='<button class="'+(_lbPeriod===v?'act':'')+'" onclick="_lbPeriod=\''+v+'\';P_leaderboard()">'+l+'</button>';
  }
  h+='</div>';
  const items=d.items||[];
  if(!items.length){h+=emptyMsg('Пока нет трейдеров с активностью');render(h);return}
  // Podium (top 3)
  const top=items.slice(0,3);
  if(top.length>=3){
    const order=[top[1],top[0],top[2]]; // silver, gold, bronze
    const medals=['🥈','🥇','🥉'];
    const classes=['lb-pod-2','lb-pod-1','lb-pod-3'];
    h+='<div class="lb-podium">';
    for(let i=0;i<3;i++){
      const t=order[i],m=medals[i],c=classes[i];
      const av=t.avatar_url?'<img src="'+t.avatar_url+'" alt="">':'👤';
      const val=_lbSort==='reputation'?((t.reputation>0?'+':'')+t.reputation):_lbSort==='volume'?fmtK(t.deals_volume):t.deals_count;
      h+='<div class="lb-pod '+c+'" onclick="go(\'#/user/'+t.id+'\')">';
      h+='<div class="lb-pod-medal">'+m+'</div>';
      h+='<div class="lb-pod-av">'+av+'</div>';
      h+='<div class="lb-pod-name">'+escHtml(t.display_name)+'</div>';
      h+='<div class="lb-pod-val">'+val+'</div>';
      h+='<div class="lb-pod-bar"></div>';
      h+='</div>';
    }
    h+='</div>';
  }
  // Rest of list
  const rest=items.slice(top.length>=3?3:0);
  for(const t of rest){
    const av=t.avatar_url?'<img src="'+t.avatar_url+'" alt="">':'👤';
    const val=_lbSort==='reputation'?((t.reputation>0?'+':'')+t.reputation):_lbSort==='volume'?fmt(t.deals_volume)+' ₽':t.deals_count+' сделок';
    h+='<div class="lb-row" onclick="go(\'#/user/'+t.id+'\')">';
    h+='<div class="lb-rank">#'+t.rank+'</div>';
    h+='<div class="lb-av">'+av+'</div>';
    h+='<div class="lb-info"><div class="lb-name">'+escHtml(t.display_name)+'</div>';
    if(t.game_nickname)h+='<div class="lb-sub">🎮 '+escHtml(t.game_nickname)+'</div>';
    h+='</div>';
    h+='<div class="lb-val">'+val+'</div>';
    h+='</div>';
  }
  render(h);
}

/* ═══════════ CLANS BROWSER ═══════════ */
let _clansPage=0,_clansSearch='',_clansAll=null;
async function P_clans(){
  render(skelRows(6));
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hdr">🏰 Кланы региона</div>';
  // Search
  h+='<div class="srch" style="margin-bottom:12px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';
  h+='<input id="clan-search" placeholder="Поиск клана по названию или тегу..." value="'+escHtml(_clansSearch)+'">';
  h+='</div>';
  // Fetch — server-side search if query, otherwise paginated list
  let d;
  if(_clansSearch){
    d=await API.get('/api/clans/search?q='+encodeURIComponent(_clansSearch));
  } else {
    const limit=50;
    const offset=_clansPage*limit;
    d=await API.get('/api/clans?offset='+offset+'&limit='+limit);
  }
  if(d.error&&!d.data){h+=emptyMsg('Ошибка загрузки: '+d.error);render(h);setupClanSearch();return}
  let clans=d.data||[];
  const totalFromApi=d.totalClans||0;
  if(totalFromApi)h+='<div style="font-size:12px;color:var(--t3);margin-bottom:12px">'+(_clansSearch?'Найдено: '+totalFromApi:'Всего: '+totalFromApi+' кланов')+'</div>';
  if(!clans.length){h+=emptyMsg(_clansSearch?'По запросу «'+escHtml(_clansSearch)+'» ничего не найдено':'Кланы не найдены');render(h);setupClanSearch();return}
  for(const c of clans){
    h+='<div class="clan-card" onclick="go(\'#/clan/'+c.id+'\')">';
    h+='<div class="clan-badge">'+(c.tag?c.tag[0]:'?')+'</div>';
    h+='<div class="clan-info"><div class="clan-name">'+escHtml(c.name||c.id)+'</div>';
    if(c.tag)h+='<span class="clan-tag">['+c.tag+']</span>';
    h+='<div class="clan-meta">👥 '+(c.memberCount||0)+' участников'+(c.alliance?' · ⚔️ '+c.alliance:'')+'</div>';
    h+='</div>';
    h+='<div class="clan-level">Lvl '+(c.level||'?')+'</div>';
    h+='</div>';
  }
  // Pagination (only when not searching)
  if(!_clansSearch){
    const limit=50;
    const totalPages=Math.max(1,Math.ceil(totalFromApi/limit));
    const curPage=_clansPage+1;
    if(totalPages>1){
      h+='<div class="pgr">';
      h+='<button '+(curPage<=1?'disabled':'')+' onclick="_clansPage='+(curPage-2)+';P_clans()">‹</button>';
      h+='<span class="pi">'+curPage+' / '+totalPages+'</span>';
      h+='<button '+(curPage>=totalPages?'disabled':'')+' onclick="_clansPage='+curPage+';P_clans()">›</button>';
      h+='</div>';
    }
  }
  render(h);
  setupClanSearch();
}
function setupClanSearch(){
  const el=document.getElementById('clan-search');
  if(!el)return;
  el.focus();
  // Set cursor at end
  el.selectionStart=el.selectionEnd=el.value.length;
  let debounce;
  el.addEventListener('input',()=>{
    clearTimeout(debounce);
    debounce=setTimeout(()=>{
      _clansSearch=el.value.trim();
      _clansPage=0;
      P_clans();
    },400);
  });
  el.addEventListener('keypress',(e)=>{
    if(e.key==='Enter'){
      _clansSearch=el.value.trim();
      _clansPage=0;
      P_clans();
    }
  });
}

/* ═══════════ MARKETPLACE ═══════════ */
async function P_market(sub){
  if(sub==='create'){P_market_create();return}
  if(sub==='my'){await P_market_my();return}
  render(skelCards(4));
  // Get market state from session
  const mCat=S.mktCat||'all';
  const mType=S.mktType||'';
  const mSort=S.mktSort||'newest';
  const mSearch=S.mktSearch||'';
  let url='/api/market?status=active&per_page=30&sort='+mSort;
  if(mCat&&mCat!=='all')url+='&category='+mCat;
  if(mType)url+='&listing_type='+mType;
  if(mSearch)url+='&search='+encodeURIComponent(mSearch);
  const d=await API.get(url);
  let h='<div class="hdr">🏪 Торговая площадка</div>';
  // Action buttons row
  h+='<div class="mkt-actions"><button class="btn btn-g btn-sm" onclick="go(\'#/market-create\')">+ Создать</button><button class="btn btn-o btn-sm" onclick="go(\'#/market-my\')">Мои объявления</button></div>';
  // Category pills
  h+='<div class="mkt-cats">';
  for(const[v,l]of[['all','Все'],['artefact','🔮 Артефакты'],['weapon','🔫 Оружие'],['armor','🛡 Броня'],['attachment','🔧 Обвес'],['other','📦 Другое']]){
    h+='<button class="mkt-cat'+(mCat===v?' act':'')+'" onclick="setMktCat(\''+v+'\')">'+l+'</button>';
  }
  h+='</div>';
  // Search + filters
  h+='<div class="mkt-filters">';
  h+='<input class="mkt-search" placeholder="🔍 Поиск по объявлениям..." value="'+escHtml(mSearch)+'" onkeypress="if(event.key===\'Enter\'){S.mktSearch=this.value;saveS();go(\'#/market\')}">';
  h+='<div class="mkt-filter-row">';
  h+='<select onchange="setMktType(this.value)"><option value=""'+(mType===''?' selected':'')+'>Все типы</option><option value="sell"'+(mType==='sell'?' selected':'')+'>Продажа</option><option value="buy"'+(mType==='buy'?' selected':'')+'>Покупка</option></select>';
  h+='<select onchange="setMktSort(this.value)"><option value="newest"'+(mSort==='newest'?' selected':'')+'>Новые</option><option value="price_asc"'+(mSort==='price_asc'?' selected':'')+'>Цена ↑</option><option value="price_desc"'+(mSort==='price_desc'?' selected':'')+'>Цена ↓</option></select>';
  h+='</div></div>';
  if(!d.items||!d.items.length){
    h+=emptyMsg('Нет объявлений по фильтру');
  } else {
    h+='<div id="mkt-list">';
    for(const l of d.items)h+=marketCard(l);
    h+='</div>';
    if(d.pages>1)h+='<div id="mkt-sentinel"></div>';
  }
  render(h);
  // Init infinite scroll for marketplace
  if(d.pages>1){
    let mktPage=1;
    initInfScroll('mkt-sentinel',(done,end)=>{
      mktPage++;
      let u='/api/market?status=active&per_page=30&page='+mktPage+'&sort='+mSort;
      if(mCat&&mCat!=='all')u+='&category='+mCat;
      if(mType)u+='&listing_type='+mType;
      if(mSearch)u+='&search='+encodeURIComponent(mSearch);
      API.get(u).then(nd=>{
        const list=document.getElementById('mkt-list');
        if(!list||!nd.items||!nd.items.length){end();return}
        let nh='';for(const l of nd.items)nh+=marketCard(l);
        list.insertAdjacentHTML('beforeend',nh);
        initRevealAnim();
        if(mktPage>=nd.pages)end();else done();
      }).catch(()=>end());
    });
  }
}
function setMktCat(v){S.mktCat=v;saveS();P_market()}
function setMktType(v){S.mktType=v;saveS();P_market()}
function setMktSort(v){S.mktSort=v;saveS();P_market()}

function marketCard(l){
  const av=l.user&&l.user.avatar_url?'<img src="'+l.user.avatar_url+'" alt="">':'👤';
  const uname=l.user?l.user.display_name:'Аноним';
  const ico=l.icon?'<img src="'+l.icon+'" alt="" onerror="this.parentElement.innerHTML=\'📦\'">':'📦';
  const tp=l.listing_type==='buy'?'<span class="mcard-type buy">Покупка</span>':'<span class="mcard-type sell">Продажа</span>';
  let meta=tp;
  if(l.is_artefact && l.quality>=0)meta+=qb(l.quality);
  if(l.is_artefact && l.upgrade_level>0)meta+=upg(l.upgrade_level);
  const nameColor=l.color?'style="color:var(--rk-'+colorCssVar(l.color)+')"':'';
  // Seller rating badge
  let sellerBadge='';
  if(l.user){
    const rep=l.user.reputation||0;
    const deals=l.user.deals_count||0;
    if(deals>0||rep!==0){
      const cls=rep>0?'rep-pos':(rep<0?'rep-neg':'rep-zero');
      sellerBadge='<span class="seller-badge '+cls+'">'+(rep>0?'👍':'👎')+' '+rep+' · '+deals+' сделок</span>';
    }
  }
  // Offers badge
  let offersBadge='';
  if(l.offers_count>0)offersBadge='<span class="offers-badge">💬 '+l.offers_count+' предл.</span>';
  return'<div class="mcard reveal-on-scroll" onclick="go(\'#/user/'+((l.user&&l.user.id)||0)+'\')">'
    +'<div class="mcard-head"><div class="mcard-icon">'+ico+'</div><div class="mcard-info"><div class="mcard-name" '+nameColor+'>'+l.item_name+'</div><div class="mcard-meta">'+meta+offersBadge+'</div></div><div class="mcard-price-col"><div class="mcard-price">'+fmt(l.price)+' ₽</div>'+(l.amount>1?'<div class="mcard-amount">×'+l.amount+'</div>':'')+'</div></div>'
    +(l.description?'<div class="mcard-desc">'+escHtml(l.description)+'</div>':'')
    +'<div class="mcard-bottom"><div class="mcard-user"><div class="mcard-avatar">'+av+'</div><span>'+uname+'</span>'+sellerBadge+'</div><div class="mcard-time">'+fmtSaleDate(l.created_at)+'</div></div>'
    +'<div class="mcard-footer"><button class="mcard-offer-btn" onclick="event.stopPropagation();openOffer('+l.id+','+l.price+')">💰 Предложить цену</button></div>'
    +'</div>';
}

function openOffer(listingId,askPrice){
  const price=prompt('Ваша цена (₽):',''+Math.round(askPrice*0.9));
  if(!price)return;
  const msg=prompt('Сообщение продавцу (необязательно):','');
  API.post('/api/market/'+listingId+'/offer',{price:parseInt(price),message:msg||''}).then(r=>{
    if(r.error){toast('❌ '+r.error);H.error()}else{toast('✅ Предложение отправлено!');H.success()}
  }).catch(()=>toast('❌ Ошибка'));
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
    if(r.error){toast('❌ '+r.error);H.error();return}
    toast('✅ Объявление создано!');H.sell();go('#/market-my');
  }catch(e){toast('❌ Ошибка: требуется авторизация через Telegram');H.error()}
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
      // Offers section
      if(st==='active'&&l.offers_count>0){
        h+='<div class="offers-badge" onclick="event.stopPropagation();toggleOffers(this,'+l.id+')">💰 '+l.offers_count+' предложени'+(l.offers_count===1?'е':l.offers_count<5?'я':'й')+' <span class="offers-arrow">▾</span></div>';
        h+='<div class="offers-list" id="offers-'+l.id+'" style="display:none"></div>';
      }
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
async function toggleOffers(badge,listingId){
  const el=document.getElementById('offers-'+listingId);
  if(!el)return;
  if(el.style.display!=='none'){el.style.display='none';return}
  el.innerHTML='<div class="inf-spinner"></div>';
  el.style.display='block';
  try{
    const offers=await API.get('/api/market/'+listingId+'/offers');
    if(!offers||!offers.length){el.innerHTML='<div style="padding:8px;font-size:11px;color:var(--t3)">Нет предложений</div>';return}
    let oh='';
    for(const o of offers){
      const u=o.user||{};
      const av=u.avatar_url?'<img src="'+u.avatar_url+'" style="width:24px;height:24px;border-radius:50%;object-fit:cover">':'<span style="font-size:14px">👤</span>';
      const statusCls=o.status==='accepted'?'offer-accepted':o.status==='declined'?'offer-declined':'';
      oh+='<div class="offer-row '+statusCls+'">';
      oh+='<div class="offer-user" onclick="event.stopPropagation();go(\'#/user/'+u.id+'\')">'+av+' <span>'+escHtml(u.display_name||'Аноним')+'</span></div>';
      oh+='<div class="offer-price">'+fmt(o.price)+' ₽</div>';
      if(o.message)oh+='<div class="offer-msg">'+escHtml(o.message)+'</div>';
      oh+='<div class="offer-time">'+fmtSaleDate(o.created_at)+'</div>';
      if(o.status==='pending'){
        oh+='<div class="offer-actions">';
        oh+='<button class="btn btn-g btn-xs" onclick="event.stopPropagation();respondOffer('+o.id+',\'accepted\','+listingId+')">✅ Принять</button>';
        oh+='<button class="btn btn-r btn-xs" onclick="event.stopPropagation();respondOffer('+o.id+',\'declined\','+listingId+')">✕ Отклонить</button>';
        oh+='</div>';
      } else {
        oh+='<div class="offer-status-label">'+({accepted:'✅ Принято',declined:'✕ Отклонено',withdrawn:'↩ Отозвано'}[o.status]||o.status)+'</div>';
      }
      oh+='</div>';
    }
    el.innerHTML=oh;
  }catch(e){el.innerHTML='<div style="padding:8px;font-size:11px;color:var(--t3)">Ошибка загрузки</div>'}
}
async function respondOffer(offerId,status,listingId){
  try{
    const r=await API.put('/api/market/offer/'+offerId,{status});
    if(r.error){toast('❌ '+r.error);return}
    toast(status==='accepted'?'✅ Предложение принято':'✕ Предложение отклонено');
    H.success();
    // Refresh offers
    const el=document.getElementById('offers-'+listingId);
    if(el){el.style.display='none';toggleOffers(null,listingId)}
  }catch(e){toast('❌ Ошибка')}
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

  // Scroll-to-bottom floating button
  h+='<button class="ch-scroll-btn" id="chat-scroll-btn" onclick="chatScrollBottom()" style="display:none">↓</button>';

  // Input area (with sticker toggle and reply bar placeholder)
  h+='<div class="ch-input-wrap" id="chat-input-wrap">';
  if(channel==='trading'||channel==='general')h+='<div id="chat-cooldown" class="trade-cooldown" style="display:none"></div>';
  h+='<div id="reply-bar"></div>';
  h+='<div style="position:relative" id="sticker-anchor"></div>';
  h+='<div class="ch-input">';
  h+='<button class="sticker-toggle" onclick="toggleStickerPanel(\''+channel+'\')" title="Стикеры">😀</button>';
  h+='<input id="chat-in" placeholder="Сообщение..." onkeypress="if(event.key===\'Enter\')sendChat(\''+channel+'\')">';
  h+='<button onclick="sendChat(\''+channel+'\')"><svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>';
  h+='</div></div>';

  render(h);
  // Init cooldown timer for general and trading
  if(channel==='trading'||channel==='general')_initChatCooldown(channel);
  const box=document.getElementById('chat-msgs');
  if(box){
    // Scroll the #app container (the actual scrolling parent) to bottom
    requestAnimationFrame(()=>{
      A.scrollTop=A.scrollHeight;
      setTimeout(()=>{A.scrollTop=A.scrollHeight},50);
      setTimeout(()=>{A.scrollTop=A.scrollHeight},200);
      setTimeout(()=>{A.scrollTop=A.scrollHeight},500);
    });
    A.addEventListener('scroll',_chatScrollHandler);
  }
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
    if(r.error){
      toast('❌ '+r.error);inp.value=text;
      if(r.cooldown&&r.cooldown>0)_startChatCooldownTimer(r.cooldown);
      return;
    }
    clearReply();
    const box=document.getElementById('chat-msgs');
    if(box){
      const emp=box.querySelector('.ch-empty');if(emp)emp.remove();
      box.insertAdjacentHTML('beforeend',chatMsg(r));
      A.scrollTop=A.scrollHeight;
      _ctx.chatLastId=r.id;
    }
    // After successful send, start cooldown
    if(ch==='trading')_startChatCooldownTimer(300);
    else if(ch==='general')_startChatCooldownTimer(3);
  }catch(e){toast('❌ Авторизуйтесь через Telegram');inp.value=text}
}

// ── Chat cooldown timer (universal) ──
let _chatCdInterval=null;
async function _initChatCooldown(ch){
  try{
    const d=await API.get('/api/chat/'+ch+'/cooldown');
    if(d.remaining>0)_startChatCooldownTimer(d.remaining);
  }catch(e){}
}
function _startChatCooldownTimer(secs){
  if(_chatCdInterval){clearInterval(_chatCdInterval);_chatCdInterval=null}
  const el=document.getElementById('chat-cooldown');
  if(!el)return;
  let left=secs;
  const inp=document.getElementById('chat-in');
  function tick(){
    if(left<=0){
      el.style.display='none';
      if(inp)inp.disabled=false;
      clearInterval(_chatCdInterval);_chatCdInterval=null;
      return;
    }
    const m=Math.floor(left/60),s=left%60;
    if(m>0){
      el.innerHTML='⏳ Следующее сообщение через <b>'+m+':'+String(s).padStart(2,'0')+'</b>';
    } else {
      el.innerHTML='⏳ Подождите <b>'+s+' сек</b>';
    }
    el.style.display='block';
    if(inp)inp.disabled=true;
    left--;
  }
  tick();
  _chatCdInterval=setInterval(tick,1000);
}
// ── WebSocket Chat + Polling fallback ──
let _chatWs=null,_wsOk=false;

function startChatPoll(ch){
  _connectChatWs(ch);
  _startFallbackPoll(ch);
}

function _connectChatWs(ch){
  try{
    if(_chatWs){try{_chatWs.close()}catch(e){}_chatWs=null}
    const proto=location.protocol==='https:'?'wss:':'ws:';
    const token=tg&&tg.initData?encodeURIComponent(tg.initData):'';
    const url=proto+'//'+location.host+'/ws/chat?channel='+encodeURIComponent(ch)+'&token='+token;
    const ws=new WebSocket(url);
    ws.onopen=()=>{_chatWs=ws;_wsOk=true};
    ws.onmessage=(e)=>{
      try{
        const ev=JSON.parse(e.data);
        if(ev.type==='new_message'&&ev.message){
          const box=document.getElementById('chat-msgs');
          if(box&&ev.message.id>(_ctx.chatLastId||0)){
            const wasBottom=_isChatAtBottom();
            box.insertAdjacentHTML('beforeend',chatMsg(ev.message));
            _ctx.chatLastId=ev.message.id;
            if(wasBottom)A.scrollTop=A.scrollHeight;
            else _showScrollBtn(true);
          }
        }
      }catch(err){}
    };
    ws.onclose=()=>{_chatWs=null;_wsOk=false};
    ws.onerror=()=>{_chatWs=null;_wsOk=false};
    const pingIv=setInterval(()=>{
      if(ws&&ws.readyState===1)ws.send('ping');
      else clearInterval(pingIv);
    },25000);
  }catch(e){_wsOk=false}
}

function _startFallbackPoll(ch){
  async function poll(){
    if(_wsOk){
      if(location.hash.startsWith('#/chat'))_chatPoll=setTimeout(poll,5000);
      return;
    }
    try{
      const msgs=await API.get('/api/chat/'+ch+'/messages?since_id='+(_ctx.chatLastId||0)+'&limit=20');
      if(msgs.length){
        const box=document.getElementById('chat-msgs');
        if(box){
          const wasAtBottom=_isChatAtBottom();
          for(const m of msgs){
            if(m.id>(_ctx.chatLastId||0)){
              box.insertAdjacentHTML('beforeend',chatMsg(m));
              _ctx.chatLastId=m.id;
            }
          }
          if(wasAtBottom)A.scrollTop=A.scrollHeight;
          else _showScrollBtn(true);
        }
      }
    }catch(e){}
    if(location.hash.startsWith('#/chat'))_chatPoll=setTimeout(poll,3000);
  }
  _chatPoll=setTimeout(poll,3000);
}

function _isChatAtBottom(){
  return A.scrollHeight - A.scrollTop - A.clientHeight < 80;
}
function _chatScrollHandler(){
  _showScrollBtn(!_isChatAtBottom());
}
function _showScrollBtn(show){
  const btn=document.getElementById('chat-scroll-btn');
  if(btn)btn.style.display=show?'flex':'none';
}
function chatScrollBottom(){
  A.scrollTop=A.scrollHeight;_showScrollBtn(false);
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
async function blockUserFromProfile(userId,name){
  if(!confirm('Заблокировать '+name+'? Вы не будете видеть сообщения друг друга.'))return;
  try{
    const r=await API.post('/api/users/'+userId+'/block',{});
    if(r.ok||r.blocked){toast('🚫 '+name+' заблокирован');H.success();P_user(userId)}
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


/* ═══════════ PROFILE — Discord/Instagram style ═══════════ */
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
  // Banner
  let h='<div class="prof-banner"></div>';
  // Avatar
  h+='<div class="prof-av-wrap"><div class="prof-avatar" onclick="document.getElementById(\'av-upload\').click()">'+av+'<input type="file" id="av-upload" accept="image/*" style="display:none" onchange="uploadAvatar(this)"></div></div>';
  // Name
  h+='<div class="prof-name-row"><div class="prof-display-name">'+escHtml(me.display_name)+'</div>';
  if(me.game_nickname)h+='<div class="prof-handle">🎮 '+escHtml(me.game_nickname)+'</div>';
  h+='</div>';
  // Bio
  if(me.bio)h+='<div class="prof-bio">'+escHtml(me.bio)+'</div>';
  // Stats row
  const rep=me.reputation||0;
  const repClass=rep>0?'pos':rep<0?'neg':'';
  h+='<div class="prof-stats">';
  h+='<div class="prof-stat"><div class="prof-stat-val '+repClass+'">'+(rep>0?'+':'')+rep+'</div><div class="prof-stat-lbl">Репутация</div></div>';
  h+='<div class="prof-stat" onclick="go(\'#/tracked\')"><div class="prof-stat-val">⭐</div><div class="prof-stat-lbl">Избранное</div></div>';
  h+='<div class="prof-stat" onclick="go(\'#/market-my\')"><div class="prof-stat-val">📋</div><div class="prof-stat-lbl">Объявления</div></div>';
  h+='</div>';
  // Actions
  h+='<div class="prof-actions">';
  h+='<button class="btn btn-o" onclick="go(\'#/profile/edit\')">✏️ Изменить</button>';
  h+='<button class="btn btn-o" onclick="go(\'#/blocked\')">🚫 Чёрный список</button>';
  h+='</div>';
  // Info cards
  h+='<div class="prof-section"><div class="prof-section-hdr">Информация</div><div class="prof-info-grid">';
  if(me.game_nickname)h+='<div class="prof-info-card"><div class="pil">Ник в игре</div><div class="piv">🎮 '+escHtml(me.game_nickname)+'</div></div>';
  if(me.discord)h+='<div class="prof-info-card"><div class="pil">Discord</div><div class="piv">💬 '+escHtml(me.discord)+'</div></div>';
  h+='<div class="prof-info-card"><div class="pil">Регистрация</div><div class="piv">📅 '+(me.created_at?fmtFullDate(new Date(me.created_at)):'—')+'</div></div>';
  h+='<div class="prof-info-card"><div class="pil">Telegram</div><div class="piv">@'+(me.telegram_username||'—')+'</div></div>';
  h+='</div></div>';
  // Settings
  h+='<div class="prof-section"><div class="prof-section-hdr">Настройки</div>';
  const isLight=(document.documentElement.dataset.theme||'dark')==='light';
  h+='<div class="theme-toggle" onclick="toggleTheme();P_profile()"><div><div class="theme-toggle-label">'+(isLight?'☀️ Светлая тема':'🌙 Тёмная тема')+'</div><div class="theme-toggle-sub">Переключить оформление</div></div><div class="theme-switch'+(isLight?' on':'')+'"></div></div>';
  const emiOn=emiS&&emiS.enabled;
  h+='<div class="card" style="padding:12px;display:flex;align-items:center;justify-content:space-between;margin-top:8px">';
  h+='<div><div style="font-weight:700;font-size:13px">☢️ Уведомления о выбросе</div><div style="font-size:11px;color:var(--t3)">При начале и конце выброса</div></div>';
  h+='<button class="btn btn-sm '+(emiOn?'btn-r':'btn-g')+'" onclick="toggleEmission()" style="flex-shrink:0">'+(emiOn?'🔕 Выкл':'🔔 Вкл')+'</button>';
  h+='</div>';
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
  h+='<div class="profile-field"><label>Отображаемое имя</label><input id="pe-name" value="'+escHtml(me.display_name||'')+'"></div>';
  h+='<div class="profile-field"><label>Ник в игре</label><input id="pe-game" value="'+escHtml(me.game_nickname||'')+'" placeholder="Например: Player-1"></div>';
  h+='<div class="profile-field"><label>Discord</label><input id="pe-disc" value="'+escHtml(me.discord||'')+'" placeholder="username#1234"></div>';
  h+='<div class="profile-field"><label>О себе</label><textarea id="pe-bio" rows="3" placeholder="Расскажите о себе...">'+escHtml(me.bio||'')+'</textarea></div>';
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

/* ═══════════ USER (public profile) — Discord/Instagram style ═══════════ */
async function P_user(uid){
  if(!uid||uid==='0'){render(emptyMsg('Пользователь не найден'));return}
  render(skelRows(3));
  const u=await API.get('/api/users/'+uid);
  if(u.error){render('<a class="back" onclick="history.back()">← Назад</a>'+emptyMsg('Не найден'));return}
  const av=u.avatar_url?'<img src="'+u.avatar_url+'" alt="">':'👤';
  // Banner
  let h='<a class="back" onclick="history.back()" style="position:relative;z-index:3">← Назад</a>';
  h+='<div class="prof-banner"></div>';
  // Avatar
  h+='<div class="prof-av-wrap"><div class="prof-avatar" style="cursor:default">'+av;
  if(u.is_online)h+='<div class="online-dot" style="position:absolute;bottom:4px;right:4px;width:14px;height:14px;border-radius:50%;background:var(--grn);border:3px solid var(--bg1)"></div>';
  h+='</div></div>';
  // Name
  h+='<div class="prof-name-row"><div class="prof-display-name">'+escHtml(u.display_name)+'</div>';
  if(u.game_nickname)h+='<div class="prof-handle">🎮 '+escHtml(u.game_nickname)+'</div>';
  h+='</div>';
  // Bio
  if(u.bio)h+='<div class="prof-bio">'+escHtml(u.bio)+'</div>';
  // Stats row
  const rep=u.reputation||0;
  const repClass=rep>0?'pos':rep<0?'neg':'';
  h+='<div class="prof-stats">';
  h+='<div class="prof-stat"><div class="prof-stat-val '+repClass+'">'+(rep>0?'+':'')+rep+'</div><div class="prof-stat-lbl">Репутация</div></div>';
  h+='<div class="prof-stat"><div class="prof-stat-val">'+(u.deals_count||0)+'</div><div class="prof-stat-lbl">Сделок</div></div>';
  h+='<div class="prof-stat"><div class="prof-stat-val">'+(u.followers_count||0)+'</div><div class="prof-stat-lbl">Подписч.</div></div>';
  h+='</div>';
  // Action buttons
  if(!u.is_self){
    h+='<div class="prof-actions">';
    h+='<button class="btn btn-b btn-sm" onclick="initDM('+uid+')">💬 Написать</button>';
    if(u.is_following){
      h+='<button class="btn btn-r btn-sm" onclick="unfollowUser('+uid+')">✕ Отписаться</button>';
    } else {
      h+='<button class="btn btn-o btn-sm" onclick="followUser('+uid+')">👤 Подписаться</button>';
    }
    h+='<button class="btn btn-r btn-sm" onclick="blockUserFromProfile('+uid+',\''+esc(u.display_name)+'\')">🚫</button>';
    h+='</div>';
  }
  // Info cards
  h+='<div class="prof-section"><div class="prof-section-hdr">Информация</div><div class="prof-info-grid">';
  if(u.game_nickname)h+='<div class="prof-info-card"><div class="pil">Ник в игре</div><div class="piv">🎮 '+escHtml(u.game_nickname)+'</div></div>';
  if(u.discord)h+='<div class="prof-info-card"><div class="pil">Discord</div><div class="piv">💬 '+escHtml(u.discord)+'</div></div>';
  const posRev=u.positive_reviews||0,negRev=u.negative_reviews||0;
  h+='<div class="prof-info-card"><div class="pil">Отзывы</div><div class="piv">👍 '+posRev+' / 👎 '+negRev+'</div></div>';
  h+='<div class="prof-info-card"><div class="pil">С нами с</div><div class="piv">📅 '+(u.member_since?fmtFullDate(new Date(u.member_since)):'—')+'</div></div>';
  h+='</div></div>';
  // Active listings
  if(u.listings&&u.listings.length){
    h+='<div class="prof-section"><div class="prof-section-hdr">Объявления · '+u.active_listings+'</div>';
    for(const l of u.listings){
      const icon=l.icon?'<img src="'+l.icon+'" alt="">':'📦';
      const typeClass=l.listing_type==='sell'?'plm-type-sell':'plm-type-buy';
      const typeText=l.listing_type==='sell'?'Продаю':'Куплю';
      h+='<div class="prof-listing-mini" onclick="go(\'#/market\')">';
      h+='<div class="plm-icon">'+icon+'</div>';
      h+='<div class="plm-info"><div class="plm-name">'+escHtml(l.item_name||l.item_id)+'</div><div class="plm-price">'+fmt(l.price)+' ₽</div></div>';
      h+='<span class="plm-type '+typeClass+'">'+typeText+'</span>';
      h+='</div>';
    }
    h+='</div>';
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
