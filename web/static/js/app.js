/* ═══════════════════════════════════════════
   PerekupHelper SPA — v6
   ═══════════════════════════════════════════ */
const A=document.getElementById('app');
function go(h){location.hash=h}

/* ── State ── */
let S={catPP:20,lotPP:15,salePP:15,catSort:'name',lotSort:'buyout_price',lotOrder:'asc',saleQlt:'all'};
try{Object.assign(S,JSON.parse(localStorage.getItem('ph_s')||'{}'))}catch(e){}
function saveS(){localStorage.setItem('ph_s',JSON.stringify(S))}

/* ── Cache ── */
const _c=new Map();
function cG(k){const e=_c.get(k);if(e&&Date.now()-e.t<300000)return e.v;return null}
function cS(k,v){_c.set(k,{v,t:Date.now()})}

/* ── Toast ── */
let _te;
function toast(m){if(!_te){_te=document.createElement('div');_te.className='toast';document.body.appendChild(_te)}_te.textContent=m;_te.classList.add('show');setTimeout(()=>_te.classList.remove('show'),2200)}

/* ── Render ── */
function render(h){A.innerHTML='<div class="page">'+h+'</div>';A.scrollTop=0}

/* ── Parse quality + upgrade from API additional ── */
function parseQU(add){
  if(!add)return{q:-1,u:0};
  let q=(add.qlt!=null)?Number(add.qlt):-1;
  let u=Math.max(0,Math.min(15,Math.round(add.ptn||0)));
  return{q,u};
}

/* ── Emission helpers ── */
let _emiData=null,_emiTs=0;
async function getEmission(){
  if(_emiData&&Date.now()-_emiTs<30000)return _emiData;
  try{_emiData=await API.get('/api/emission');_emiTs=Date.now()}catch(e){_emiData=null}
  return _emiData;
}
function emiHTML(d){
  if(!d)return '';
  const now=Date.now();
  const cs=d.currentEmissionStart?new Date(d.currentEmissionStart).getTime():0;
  const ce=d.currentEmissionEnd?new Date(d.currentEmissionEnd).getTime():0;
  const isOn=cs>0&&ce>0&&now>=cs&&now<ce;
  if(isOn){
    const left=ce-now;
    return '<div class="emi"><div class="emi-dot on"></div><div class="emi-text">☢️ Выброс идёт</div><div class="emi-timer">'+fmtMs(left)+'</div></div>';
  }
  // Зона чиста — показываем когда был последний
  const ps=d.previousEmissionStart?new Date(d.previousEmissionStart).getTime():0;
  const pe=d.previousEmissionEnd?new Date(d.previousEmissionEnd).getTime():0;
  let info='';
  if(pe>0)info=fmtAgo(now-pe)+' назад';
  return '<div class="emi"><div class="emi-dot off"></div><div class="emi-text">Зона чиста</div><div class="emi-timer">'+info+'</div></div>';
}
function fmtMs(ms){
  if(ms<=0)return '0:00';
  const m=Math.floor(ms/60000),s=Math.floor((ms%60000)/1000);
  return m+':'+String(s).padStart(2,'0');
}
function fmtAgo(ms){
  if(ms<60000)return '<1 мин';
  if(ms<3600000)return Math.floor(ms/60000)+' мин';
  if(ms<86400000)return Math.floor(ms/3600000)+' ч';
  return Math.floor(ms/86400000)+' д';
}

/* ── Router ── */
async function route(){
  const h=location.hash||'#/',p=h.replace('#','').split('/').filter(Boolean),pg=p[0]||'';
  document.querySelectorAll('.tab').forEach(t=>{
    const r=t.dataset.route;
    t.classList.toggle('active',r===h||(r==='#/'&&h==='#/'));
  });
  if(tg&&pg){tg.BackButton.show();tg.BackButton.onClick(()=>history.back())}
  else if(tg){tg.BackButton.hide()}
  try{
    if(!pg||h==='#/')await P_home();
    else if(pg==='catalog')await P_cat(p.slice(1).join('/'));
    else if(pg==='item')await P_item(p[1]);
    else if(pg==='auction')await P_auc(p[1]);
    else if(pg==='search')P_search();
    else if(pg==='tracked')await P_tracked();
    else await P_home();
  }catch(e){render('<div class="empty"><div class="empty-i">⚠️</div><div class="empty-t">'+e.message+'</div></div>')}
  if(tg)tg.expand();
}
window.addEventListener('hashchange',route);
window.addEventListener('load',route);

/* ═══════════ HOME (merged with catalog) ═══════════ */
async function P_home(){
  render('<div class="ld">Загрузка</div>');
  const ck=cG('cats');
  const [cats,tr,emi]=await Promise.all([
    ck?Promise.resolve(ck):API.get('/api/categories'),
    API.get('/api/tracked'),
    getEmission()
  ]);
  if(!ck)cS('cats',cats);
  const tot=cats.reduce((s,c)=>s+c.count,0);
  let h='';
  // Emission
  h+=emiHTML(emi);
  // Banner
  h+='<div class="banner"><div class="banner-title">⚡ PerekupHelper</div><div class="banner-sub">Мониторинг аукциона Stalcraft</div></div>';
  // Stats
  h+='<div class="sgrid"><div class="sbox"><div class="sv">'+fmtK(tot)+'</div><div class="sl">Предметов</div></div>';
  h+='<div class="sbox"><div class="sv">'+tr.length+'</div><div class="sl">Избранное</div></div>';
  h+='<div class="sbox"><div class="sv">'+cats.length+'</div><div class="sl">Категорий</div></div></div>';
  // Tracked
  if(tr.length){
    h+='<div class="sec">⭐ Отслеживаемые</div><div class="hscroll">';
    for(const t of tr){h+='<div class="hcard" onclick="haptic();go(\'#/item/'+t.item_id+'\')"><div class="hcard-img">'+ICO(t.icon)+'</div><div class="hcard-name">'+t.name+'</div><div class="hcard-price">'+(t.avg_24h?fmt(t.avg_24h)+' ₽':'—')+'</div></div>'}
    h+='</div>';
  }
  // Categories grid
  h+='<div class="sec">📦 Каталог</div><div class="cgrid">';
  for(const c of cats){h+='<div class="cbtn" onclick="haptic();go(\'#/catalog/'+c.id+'\')"><div class="ce">'+CE(c.id)+'</div><div class="cl">'+CN(c.name)+'</div><div class="cc">'+c.count+'</div></div>'}
  h+='</div>';
  render(h);
}

/* ═══════════ CATEGORY ═══════════ */
async function P_cat(cat,pg){
  if(!cat){await P_home();return}
  pg=pg||1;render('<div class="ld">Загрузка</div>');
  const ck=cG('cats');const allC=ck||await API.get('/api/categories');if(!ck)cS('cats',allC);
  const par=allC.find(c=>c.id===cat);
  if(par&&par.children&&par.children.length){
    let h='<a class="back" href="#/">← Главная</a>';
    h+='<div class="hdr">'+CE(cat)+' '+CN(par.name)+'</div><div class="sub">'+par.count+' предметов</div><div class="cgrid">';
    for(const s of par.children)h+='<div class="cbtn" onclick="haptic();go(\'#/catalog/'+s.id+'\')"><div class="ce">'+CE(s.id)+'</div><div class="cl">'+CN(s.name)+'</div><div class="cc">'+s.count+'</div></div>';
    h+='</div>';render(h);return;
  }
  const d=await API.get('/api/categories/'+cat+'/items?page='+pg+'&per_page='+S.catPP+'&sort='+S.catSort);
  const bk=cat.includes('/')?cat.split('/').slice(0,-1).join('/'):'';
  _ctx.cat=cat;
  let h='<a class="back" href="'+(bk?'#/catalog/'+bk:'#/')+'">← Назад</a>';
  h+='<div class="hdr">'+(d.items[0]?d.items[0].category_name:CN(cat))+'</div><div class="sub">'+d.total+' предметов</div>';
  h+=sortBar([['name','По имени'],['color','По редкости']],S.catSort,'setSort');
  h+=ppBar(S.catPP,[10,20,50],'cat');
  h+='<div class="card">';
  for(const i of d.items)h+=R(i.id,i.icon,i.name,i.rank_name,i.color,null,i.api_supported);
  h+='</div>';
  if(d.pages>1)h+=pgBar(pg,d.pages,"P_cat('"+cat+"',{p})");
  render(h);
}
function setSort(s){S.catSort=s;saveS();if(_ctx.cat)P_cat(_ctx.cat,1)}

/* ═══════════ ITEM DETAIL ═══════════ */
async function P_item(id){
  render('<div class="ld">Загрузка</div>');
  const [item,tr]=await Promise.all([API.get('/api/items/'+id),API.get('/api/tracked')]);
  if(item.error){render('<div class="empty"><div class="empty-i">❌</div><div class="empty-t">Не найден</div></div>');return}
  const isTr=tr.some(t=>t.item_id===id);
  const apiOk=item.api_supported!==false;
  let h='<a class="back" onclick="history.back()">← Назад</a>';
  h+='<div class="hero rk-'+item.color+'"><div class="hero-img">'+ICO(item.icon)+'</div><div class="hero-r"><div class="hero-t">'+item.name+'</div><div class="hero-s">'+item.category_name;
  if(item.rank_name)h+=' · <span class="rk-tag rk-tag-'+item.color+'">'+item.rank_name+'</span>';
  h+='</div></div></div>';
  if(apiOk){
    h+='<div class="pblk"><div class="pt">💰 Цены</div>';
    if(item.is_artefact&&item.quality_breakdown&&item.quality_breakdown.length){
      for(const b of item.quality_breakdown)h+='<div class="pr"><span class="pl">'+qb(b.quality)+upg(b.upgrade_level)+'</span><span class="pv">'+fmt(b.avg_price)+' ₽ <small style="color:var(--t3)">('+b.count+')</small></span></div>';
    } else if(item.prices&&(item.prices.avg_24h||item.prices.avg_7d)){
      if(item.prices.avg_24h)h+='<div class="pr"><span class="pl">Средняя 24ч</span><span class="pv">'+fmt(item.prices.avg_24h)+' ₽</span></div>';
      if(item.prices.avg_7d)h+='<div class="pr"><span class="pl">Средняя 7д</span><span class="pv">'+fmt(item.prices.avg_7d)+' ₽</span></div>';
    } else h+='<div class="pr"><span class="pl" style="opacity:.5">Добавь в отслеживание</span></div>';
    h+='</div>';
  } else h+=warnBox('Аукцион недоступен','Предмет не поддерживается API.');
  h+='<div class="bgrp">';
  if(apiOk){
    if(isTr)h+='<button class="btn btn-r" onclick="haptic(\'medium\');UT(\''+id+'\')">✕ Убрать</button>';
    else h+='<button class="btn btn-g" onclick="haptic(\'medium\');TK(\''+id+'\')">📌 Отслеживать</button>';
    h+='<a class="btn btn-o" href="#/auction/'+id+'" onclick="haptic()">📊 Аукцион</a>';
  }
  h+='</div>';
  if(item.stats&&item.stats.length){
    h+='<div class="sec">Характеристики</div><div class="card" style="padding:10px 12px"><div class="stl">';
    for(const s of item.stats){let c='';if(s.color==='53C353')c='sg';else if(s.color==='C15252')c='sr';h+='<div class="str"><span class="stk">'+s.key+'</span><span class="stv '+c+'">'+s.value+'</span></div>'}
    h+='</div></div>';
  }
  render(h);
}
async function TK(id){await API.post('/api/tracked',{item_id:id});toast('📌 Добавлено');P_item(id)}
async function UT(id){await API.del('/api/tracked/'+id);toast('✕ Убрано');P_item(id)}

/* ═══════════ AUCTION ═══════════ */
async function P_auc(id,lp,sp){
  lp=lp||1;sp=sp||1;
  render('<div class="ld">Загрузка лотов</div>');
  const item=await API.get('/api/items/'+id);
  if(item.api_supported===false){render('<a class="back" href="#/item/'+id+'">← Назад</a>'+warnBox('Недоступно','API не поддерживает.'));return}
  const isA=!!item.is_artefact,nm=item.name||id;
  const lOff=(lp-1)*S.lotPP,sOff=(sp-1)*S.salePP;
  const [ld,hd,pd]=await Promise.all([
    API.get('/api/auction/'+id+'/lots?limit='+S.lotPP+'&offset='+lOff+'&sort='+S.lotSort+'&order='+S.lotOrder),
    API.get('/api/auction/'+id+'/history?limit='+S.salePP+'&offset='+sOff),
    API.get('/api/auction/'+id+'/prices')]);
  const lots=ld.lots||[],sales=hd.prices||[];
  const lTotal=ld.total||0,sTotal=hd.total||0;
  const lPages=Math.ceil(lTotal/S.lotPP)||1,sPages=Math.ceil(sTotal/S.salePP)||1;
  _ctx.aucId=id;_ctx.lp=lp;_ctx.sp=sp;
  let h='<a class="back" href="#/item/'+id+'">← '+nm+'</a>';
  h+='<div class="hdr">📊 Аукцион</div><div class="sub">'+nm+'</div>';
  // Breakdown
  if(pd.breakdown&&pd.breakdown.length){
    h+='<div class="pblk"><div class="pt">📈 Средние по качеству (7д)</div>';
    for(const b of pd.breakdown)h+='<div class="pr"><span class="pl">'+qb(b.quality)+upg(b.upgrade_level)+'</span><span class="pv">~'+fmt(b.avg_price)+' ₽ <small style="color:var(--t3)">мин.'+fmt(b.min_price)+' ('+b.count+')</small></span></div>';
    h+='</div>';
  }
  // Lots
  h+='<div class="sec">🏷 Лоты ('+lTotal+')</div>';
  h+=sortBar([['buyout_price|asc','Цена ↑'],['buyout_price|desc','Цена ↓'],['time_created|desc','Новые']],S.lotSort+'|'+S.lotOrder,'setLS');
  h+=ppBar(S.lotPP,[10,15,25,50],'lot');
  if(lots.length){
    h+='<div class="card"><div class="tw"><table class="lt"><thead><tr><th>Цена</th>'+(isA?'<th>Кач / Заточка</th>':'')+'<th>Тип</th><th>Истекает</th></tr></thead><tbody>';
    for(const l of lots){
      const pr=l.buyoutPrice||l.currentPrice||l.startPrice||0;
      const tp=l.buyoutPrice>0?'Выкуп':'Ставка';
      let qc='';
      if(isA){const{q,u}=parseQU(l.additional);qc='<td>'+qb(q)+(u>0?' '+upg(u):'')+'</td>'}
      h+='<tr><td class="lp">'+fmt(pr)+' ₽</td>'+(isA?qc:'')+'<td>'+tp+'</td><td class="td-date">'+fmtDateS(l.endTime)+'</td></tr>';
    }
    h+='</tbody></table></div></div>';
    if(lPages>1)h+=pgBar(lp,lPages,"P_auc('"+id+"',{p},"+sp+")");
  } else h+=emptyMsg('Нет активных лотов');
  // Sales
  h+='<div class="sec">📋 Продажи ('+sTotal+')</div>';
  if(isA){
    h+='<div class="sort-bar"><span style="font-size:10px;color:var(--t3)">Качество:</span>';
    for(const[v,l]of[['all','Все'],['0','Обычный'],['1','Необычн.'],['2','Особый'],['3','Редкий'],['4','Исключ.'],['5','Легенд.']]){
      h+='<button class="'+(S.saleQlt===v?'act':'')+'" onclick="setSaleQlt(\''+v+'\')"><span class="'+(v!=='all'?'q-'+v:'')+'" style="font-size:9px">'+l+'</span></button>';
    }
    h+='</div>';
  }
  h+=ppBar(S.salePP,[10,15,25,50],'sale');
  let fs=sales;
  if(isA&&S.saleQlt!=='all'){const fq=parseInt(S.saleQlt);fs=sales.filter(s=>{const{q}=parseQU(s.additional);return q===fq})}
  if(fs.length){
    h+='<div class="card"><div class="tw"><table class="lt"><thead><tr><th>Цена</th>'+(isA?'<th>Кач / Заточка</th>':'')+'<th>Кол</th><th>Дата</th></tr></thead><tbody>';
    for(const s of fs){
      let qc='';
      if(isA){const{q,u}=parseQU(s.additional);qc='<td>'+qb(q)+(u>0?' '+upg(u):'')+'</td>'}
      h+='<tr><td class="lp">'+fmt(s.price)+' ₽</td>'+(isA?qc:'')+'<td>'+(s.amount||1)+'</td><td class="td-date">'+fmtDateS(s.time)+'</td></tr>';
    }
    h+='</tbody></table></div></div>';
    if(sPages>1)h+=pgBar(sp,sPages,"P_auc('"+id+"',"+lp+",{p})");
  } else {
    h+=emptyMsg(isA&&S.saleQlt!=='all'&&sales.length?'Нет продаж этого качества':'Нет данных');
  }
  h+='<button class="btn btn-o" style="margin-top:10px" onclick="P_auc(\''+id+'\','+lp+','+sp+')">🔄 Обновить</button>';
  render(h);
}
function setLS(v){const[s,o]=v.split('|');S.lotSort=s;S.lotOrder=o;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,1,_ctx.sp||1)}
function setSaleQlt(v){S.saleQlt=v;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,_ctx.lp||1,1)}

/* ═══════════ SEARCH ═══════════ */
let _st,_sSort='relevance',_lastQ='';
function P_search(){
  let h='<div class="hdr">🔍 Поиск</div><div class="sub">Найди любой предмет</div>';
  h+='<div class="srch"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><input id="si" placeholder="Название предмета..." autofocus></div>';
  h+=sortBar([['relevance','Релевантность'],['name','По имени'],['color','По редкости']],_sSort,'setSS');
  h+='<div id="sr"></div>';
  render(h);
  const si=document.getElementById('si');
  if(si){si.value=_lastQ;si.addEventListener('input',e=>{clearTimeout(_st);_lastQ=e.target.value;_st=setTimeout(()=>DS(e.target.value),200)});if(_lastQ)DS(_lastQ)}
}
function setSS(v){_sSort=v;P_search()}
async function DS(q){
  const b=document.getElementById('sr');if(!b)return;
  if(q.trim().length<1){b.innerHTML='';return}
  b.innerHTML='<div class="ld">Поиск...</div>';
  try{
    const it=await API.get('/api/search?q='+encodeURIComponent(q)+'&limit=50&sort='+_sSort);
    if(!it.length){b.innerHTML=emptyMsg('Ничего не найдено');return}
    let h='<div class="card">';for(const i of it)h+=R(i.id,i.icon,i.name,i.rank_name||i.category_name,i.color,null,i.api_supported);h+='</div>';b.innerHTML=h;
  }catch(e){b.innerHTML=emptyMsg('Ошибка')}
}

/* ═══════════ TRACKED ═══════════ */
async function P_tracked(){
  render('<div class="ld">Загрузка</div>');
  const tr=await API.get('/api/tracked');
  let h='<div class="hdr">⭐ Избранное</div><div class="sub">'+tr.length+' предметов</div>';
  if(!tr.length){
    h+='<div class="empty"><div class="empty-i">📭</div><div class="empty-t">Пока ничего не отслеживается</div><button class="btn btn-g" style="margin:14px auto 0;width:auto;padding:10px 24px" onclick="go(\'#/search\')">🔍 Найти предмет</button></div>';
  } else {
    h+='<div class="card">';for(const t of tr)h+=R(t.item_id,t.icon,t.name,'',t.color,t.avg_24h,t.api_supported);h+='</div>';
  }
  render(h);
}

/* ═══════════ HELPERS ═══════════ */
function ICO(s){
  if(!s||s==='/icons/'||s==='')return '<div class="no-icon">📦</div>';
  return '<img src="'+s+'" onerror="this.parentElement.innerHTML=\'<div class=\\\'no-icon\\\'>📦</div>\'" loading="lazy">';
}
function R(id,icon,name,tag,color,price,apiOk){
  const p=price?'<div class="ip">'+fmt(price)+' ₽</div>':'';
  const w=(apiOk===false)?'<span class="badge-wiki">wiki</span>':'';
  let tH='';if(tag)tH='<div class="it"><span class="rk-tag rk-tag-'+(color||'DEFAULT')+'">'+tag+'</span></div>';
  return '<div class="irow rk-'+(color||'DEFAULT')+'" onclick="haptic();go(\'#/item/'+id+'\')"><div class="irow-icon">'+ICO(icon)+'</div><div class="ib"><div class="in">'+name+w+'</div>'+tH+'</div>'+p+'</div>';
}
function sortBar(opts,cur,fn){
  let h='<div class="sort-bar">';
  for(const[v,l]of opts)h+='<button class="'+(cur===v?'act':'')+'" onclick="'+fn+"('"+v+"')"+'">'+(l||v)+'</button>';
  return h+'</div>';
}
function ppBar(cur,opts,key){
  let h='<div class="pps"><span>Показать:</span>';
  for(const v of opts)h+='<button class="'+(v===cur?'act':'')+'" onclick="setPP(\''+key+'\','+v+')">'+v+'</button>';
  return h+'</div>';
}
function pgBar(cur,tot,tpl){
  return '<div class="pgr"><button '+(cur<=1?'disabled':'')+' onclick="'+tpl.replace('{p}',cur-1)+'">‹</button><span class="pi">'+cur+' / '+tot+'</span><button '+(cur>=tot?'disabled':'')+' onclick="'+tpl.replace('{p}',cur+1)+'">›</button></div>';
}
function emptyMsg(t){return '<div class="empty"><div class="empty-t" style="padding:16px 0">'+t+'</div></div>'}
function warnBox(t,d){return '<div class="warn-box"><span class="warn-icon">⚠️</span><div class="warn-text"><b>'+t+'</b><br>'+d+'</div></div>'}
let _ctx={};
function setPP(key,val){
  if(key==='cat'){S.catPP=val;saveS();if(_ctx.cat)P_cat(_ctx.cat,1)}
  else if(key==='lot'){S.lotPP=val;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,1,_ctx.sp||1)}
  else if(key==='sale'){S.salePP=val;saveS();if(_ctx.aucId)P_auc(_ctx.aucId,_ctx.lp||1,1)}
}
function fmtDateS(s){
  if(!s)return '—';
  try{
    const d=new Date(s),now=new Date(),df=now-d;
    if(isNaN(d))return s.replace('T',' ').slice(0,16);
    if(df<60000)return 'только что';
    if(df<3600000)return Math.floor(df/60000)+'м';
    if(df<86400000)return Math.floor(df/3600000)+'ч';
    if(df<604800000)return Math.floor(df/86400000)+'д';
    return d.toLocaleDateString('ru-RU',{day:'numeric',month:'short'});
  }catch(e){return '—'}
}
const CE_MAP={weapon:'🔫',armor:'🛡',artefact:'💎',attachment:'🔩',bullet:'🔸',containers:'📦',medicine:'💊',food:'🍖',drink:'🥤',other:'📦',grenade:'💥',backpacks:'🎒',misc:'📎',weapon_modules:'⚙️',weapon_style:'🎨',armor_style:'🎨',device:'📡',consumables:'💉'};
function CE(id){return CE_MAP[id.split('/')[0]]||'📁'}
function CN(n){return n.replace(/[\p{Emoji}\uFE0F\u200D]+\s*/gu,'').trim()||n}
function fmtK(n){if(n>=1000)return(n/1000).toFixed(1).replace('.0','')+'к';return String(n)}
