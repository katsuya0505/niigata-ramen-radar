const feed = document.getElementById("feed");
const emptyState = document.getElementById("emptyState");
const filters = document.querySelectorAll(".filter");
const periods = document.querySelectorAll(".period");
let items = [], meta = {}, activeDays = 1, activeFilter = "all";
const badgeLabel={opening:"NEW OPEN",opening_soon:"OPENING SOON",limited:"LIMITED",closed:"CLOSED",relocation:"RELOCATION",renewal:"RENEWAL"};

const headlineList = document.getElementById("headlineList");
const summaryTitle = document.getElementById("summaryTitle");
const summaryLead = document.getElementById("summaryLead");
const latestChanges = document.getElementById("latestChanges");

function areaShort(area){
  const a=String(area||"").trim();
  const m=a.match(/新潟市([^市]+区)/);
  if(m)return m[1];
  return a.replace(/^新潟県/,'').replace(/^新潟市/,'')||"地域未確認";
}
function periodLabel(){return activeDays===1?"今日":activeDays===7?"この7日間":"この30日間"}
function namesFor(list,types){
  return list.filter(x=>types.includes(x.type)).map(x=>`${esc(x.name)}（${esc(areaShort(x.area))}）`);
}
function headlineRow(label,types,filterKey,list){
  const names=namesFor(list,types);
  const body=names.length?names.map(n=>`<span class="headline-name">${n}</span>`).join('<span class="headline-sep">、</span>'):'<span class="headline-none">該当情報なし</span>';
  return `<div class="headline-row"><div class="headline-type">${label}</div><div class="headline-body">${body}</div><a href="#latestChanges" class="headline-jump" data-jump-filter="${filterKey}">詳しく見る ↓</a></div>`;
}
function renderHeadlines(){
  if(!headlineList)return;
  const list=periodItems();
  const p=periodLabel();
  summaryTitle.textContent=`${p}のラーメン情報`;
  const n=list.length;
  summaryLead.textContent=n?`${p}は${n}件の変化を検知しています。店名と地域だけ先に確認できます。`:`${p}は新しい変化を検知していません。`;
  headlineList.innerHTML=[
    headlineRow('新店・開店予定',['opening','opening_soon'],'opening',list),
    headlineRow('閉店',['closed'],'closed',list),
    headlineRow('移転・リニューアル',['relocation','renewal'],'change',list),
    headlineRow('限定情報',['limited'],'limited',list)
  ].join('');
}
function jumpToFilter(filterKey){
  const target=[...filters].find(b=>b.dataset.filter===filterKey)||[...filters].find(b=>b.dataset.filter==='all');
  filters.forEach(b=>b.classList.remove('active'));
  if(target)target.classList.add('active');
  activeFilter=filterKey;
  render();
  setTimeout(()=>latestChanges?.scrollIntoView({behavior:'smooth',block:'start'}),10);
}
document.addEventListener('click',e=>{
  const a=e.target.closest('[data-jump-filter]');
  if(!a)return;
  e.preventDefault();
  jumpToFilter(a.dataset.jumpFilter||'all');
});
function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}
function itemDate(item){const raw=item.detected_at||item.published_at; const d=new Date(raw||0); return Number.isNaN(d.getTime())?new Date(0):d}
function formatDate(iso){if(!iso)return"日付未確認";const d=new Date(iso);if(Number.isNaN(d.getTime()))return String(iso);return new Intl.DateTimeFormat("ja-JP",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(d)}
function groupMatches(item,target){if(target==="all")return true;if(target==="opening")return["opening","opening_soon"].includes(item.type);if(target==="change")return["relocation","renewal"].includes(item.type);return item.type===target}
function withinDays(item,days){const d=itemDate(item); if(d.getTime()===0)return false; const now=new Date(); const start=new Date(now); start.setHours(0,0,0,0); if(days>1)start.setDate(start.getDate()-(days-1)); return d>=start && d<=now}
function periodItems(){return items.filter(x=>withinDays(x,activeDays))}
function mapSearchQuery(item){
  // MAPボタンが使っている検索語を優先。取得できない場合は店名＋地域で検索する。
  if(item.map_url){
    try{
      const u=new URL(item.map_url);
      const q=u.searchParams.get("query")||u.searchParams.get("q")||u.searchParams.get("query_place_id");
      if(q)return q;
    }catch(e){}
  }
  return [item.name,item.area,"新潟県"].filter(Boolean).join(" ");
}
function googleMapEmbed(query){
  // APIキー不要のGoogle Maps埋め込み検索表示。MAPボタンと同じ検索対象をカード内に可視化する。
  return `https://maps.google.com/maps?hl=ja&q=${encodeURIComponent(query)}&z=15&output=embed`;
}
function mapMarkup(item){
  const query=mapSearchQuery(item);
  const src=googleMapEmbed(query);
  const fallbackUrl=item.map_url||`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  return `<div class="card-map google-map"><iframe src="${src}" title="${esc(item.name)} 地図" loading="eager" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe><div class="map-status exact">MAP</div><a class="map-open" href="${esc(fallbackUrl)}" target="_blank" rel="noopener noreferrer">大きな地図で見る ↗</a></div>`;
}
function render(){const list=periodItems().filter(x=>groupMatches(x,activeFilter));feed.innerHTML="";emptyState.hidden=list.length!==0;list.forEach(item=>{const card=document.createElement("article");card.className="card";const tags=(item.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join("");card.innerHTML=`${mapMarkup(item)}<div class="card-top"><span class="badge ${esc(item.type)}">${badgeLabel[item.type]||"INFO"}</span><span class="date">${formatDate(item.detected_at)}</span></div><div><h4>${esc(item.name)}</h4><div class="location">📍 ${esc(item.area)}</div></div><p class="desc">${esc(item.summary)}</p><div class="tags">${tags}</div>${item.source_count?`<div class="radar-evidence">📡 ${item.source_count} SOURCE${item.source_count>1?"S":""} DETECTED · CONFIDENCE ${item.confidence||55}%</div>`:""}<div class="card-actions">${item.source_url?`<a class="link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">情報源を見る</a>`:""}${item.map_url?`<a class="link secondary" href="${esc(item.map_url)}" target="_blank" rel="noopener noreferrer">MAP</a>`:""}</div>`;feed.appendChild(card)});renderHeadlines();updateMetrics()}
function countTypes(list,types){return list.filter(x=>types.includes(x.type)).length}
function updateMetrics(){const list=periodItems();document.getElementById("countAll").textContent=list.length;document.getElementById("periodCount").textContent=list.length;document.getElementById("countNew").textContent=countTypes(list,["opening","opening_soon"]);document.getElementById("countLimited").textContent=countTypes(list,["limited"]);document.getElementById("countClosed").textContent=countTypes(list,["closed"]);document.getElementById("countChange").textContent=countTypes(list,["relocation","renewal"]);document.getElementById("lastScan").textContent=meta.last_scan||"--";document.getElementById("dataUpdated").textContent=meta.data_updated||"--";document.getElementById("feedTitle").textContent=activeDays===1?"今日の更新情報":activeDays===7?"7日間の更新情報":"30日間の更新情報"}
filters.forEach(btn=>btn.addEventListener("click",()=>{filters.forEach(b=>b.classList.remove("active"));btn.classList.add("active");activeFilter=btn.dataset.filter;render()}));
periods.forEach(btn=>btn.addEventListener("click",()=>{periods.forEach(b=>b.classList.remove("active"));btn.classList.add("active");activeDays=Number(btn.dataset.days);render()}));
fetch("./data/ramen.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("data load failed");return r.json()}).then(data=>{meta=data.meta||{};items=(data.items||[]).sort((a,b)=>itemDate(b)-itemDate(a));render()}).catch(err=>{console.error(err);emptyState.hidden=false;emptyState.textContent="データを読み込めませんでした。"});

// v0.7.5: fresh opening signal alert + lightweight live refresh
const freshAlert=document.getElementById("freshAlert");
const radarStatus=document.getElementById("radarStatus");
const radarStatusText=document.getElementById("radarStatusText");
function ageMinutes(item){const t=itemDate(item).getTime();return t?Math.floor((Date.now()-t)/60000):999999}
function renderFreshAlert(){
  if(!freshAlert)return;
  const fresh=items.filter(x=>["opening","opening_soon"].includes(x.type)&&ageMinutes(x)>=0&&ageMinutes(x)<60).sort((a,b)=>itemDate(b)-itemDate(a))[0];
  if(!fresh){freshAlert.classList.remove("active");radarStatus?.classList.remove("warning");if(radarStatusText)radarStatusText.textContent="RADAR ONLINE";return}
  const mins=Math.max(0,ageMinutes(fresh));
  freshAlert.classList.add("active");radarStatus?.classList.add("warning");if(radarStatusText)radarStatusText.textContent="NEW SIGNAL";
  freshAlert.innerHTML=`<div class="alert-kicker">⚠ WARNING / FRESH SIGNAL</div><div class="alert-main"><span class="warning-triangle">▲</span><strong>NEW RAMEN SHOP DETECTED</strong><span class="alert-age">${mins<1?'たった今':mins+'分前'}</span></div><div class="alert-shop">${esc(fresh.name)}（${esc(areaShort(fresh.area))}）</div><a class="alert-link" href="#latestChanges" data-jump-filter="opening">新店情報を確認 ↓</a>`;
}
const originalRender=render;
render=function(){originalRender();renderFreshAlert()};
async function refreshRadarData(){
  try{const r=await fetch(`./data/ramen.json?t=${Date.now()}`,{cache:"no-store"});if(!r.ok)return;const data=await r.json();const next=JSON.stringify(data.items||[]);const prev=JSON.stringify(items);meta=data.meta||meta;if(next!==prev){items=(data.items||[]).sort((a,b)=>itemDate(b)-itemDate(a));render()}else{renderFreshAlert();updateMetrics()}}
  catch(e){console.debug("radar refresh skipped",e)}
}
setInterval(refreshRadarData,5*60*1000);

// v0.7.6: NEARBY RADAR — browser geolocation -> Google Maps nearby ramen search.
const nearbyButton = document.getElementById("nearbyButton");
const nearbyStatus = document.getElementById("nearbyStatus");
const nearbyMap = document.getElementById("nearbyMap");
const nearbyPlaceholder = document.getElementById("nearbyPlaceholder");
const nearbyExternal = document.getElementById("nearbyExternal");

function setNearbyStatus(text, state=""){
  if(!nearbyStatus)return;
  nearbyStatus.textContent=text;
  nearbyStatus.className=`nearby-status ${state}`.trim();
}
function nearbyEmbedUrl(lat, lon){
  // API key is not required for this simple Maps embed search.
  return `https://maps.google.com/maps?q=${encodeURIComponent("ラーメン")}&ll=${lat},${lon}&z=14&output=embed`;
}
function nearbyMapsUrl(lat, lon){
  return `https://www.google.com/maps/search/${encodeURIComponent("ラーメン")}/@${lat},${lon},14z`;
}
function startNearbyRadar(){
  if(!navigator.geolocation){
    setNearbyStatus("LOCATION UNAVAILABLE — この端末では位置情報を利用できません", "error");
    return;
  }
  nearbyButton?.classList.add("scanning");
  if(nearbyButton)nearbyButton.disabled=true;
  setNearbyStatus("SCANNING CURRENT LOCATION...", "scanning");
  navigator.geolocation.getCurrentPosition(pos=>{
    const lat=pos.coords.latitude;
    const lon=pos.coords.longitude;
    if(nearbyMap){
      nearbyMap.src=nearbyEmbedUrl(lat,lon);
      nearbyMap.hidden=false;
    }
    if(nearbyPlaceholder)nearbyPlaceholder.hidden=true;
    if(nearbyExternal)nearbyExternal.href=nearbyMapsUrl(lat,lon);
    setNearbyStatus("LOCATION LOCKED — 周辺のラーメン店を表示中", "locked");
    nearbyButton?.classList.remove("scanning");
    if(nearbyButton){nearbyButton.disabled=false;nearbyButton.innerHTML='<span class="nearby-ping">◎</span> 現在地を再スキャン';}
  },err=>{
    const msg = err.code===1 ? "位置情報の利用が許可されていません" : err.code===2 ? "現在地を取得できませんでした" : "位置情報の取得がタイムアウトしました";
    setNearbyStatus(`SCAN FAILED — ${msg}`, "error");
    nearbyButton?.classList.remove("scanning");
    if(nearbyButton)nearbyButton.disabled=false;
  },{enableHighAccuracy:false,timeout:10000,maximumAge:300000});
}
nearbyButton?.addEventListener("click",startNearbyRadar);
