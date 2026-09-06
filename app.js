const feed = document.getElementById("feed");
const emptyState = document.getElementById("emptyState");
const filters = document.querySelectorAll(".filter");
const periods = document.querySelectorAll(".period");
let items = [], meta = {}, activeDays = 1, activeFilter = "all";
const badgeLabel={opening:"NEW OPEN",opening_soon:"OPENING SOON",limited:"LIMITED",closed:"CLOSED",relocation:"RELOCATION",renewal:"RENEWAL"};
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
function render(){const list=periodItems().filter(x=>groupMatches(x,activeFilter));feed.innerHTML="";emptyState.hidden=list.length!==0;list.forEach(item=>{const card=document.createElement("article");card.className="card";const tags=(item.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join("");card.innerHTML=`${mapMarkup(item)}<div class="card-top"><span class="badge ${esc(item.type)}">${badgeLabel[item.type]||"INFO"}</span><span class="date">${formatDate(item.detected_at)}</span></div><div><h4>${esc(item.name)}</h4><div class="location">📍 ${esc(item.area)}</div></div><p class="desc">${esc(item.summary)}</p><div class="tags">${tags}</div>${item.source_count?`<div class="radar-evidence">📡 ${item.source_count} SOURCE${item.source_count>1?"S":""} DETECTED · CONFIDENCE ${item.confidence||55}%</div>`:""}<div class="card-actions">${item.source_url?`<a class="link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">情報源を見る</a>`:""}${item.map_url?`<a class="link secondary" href="${esc(item.map_url)}" target="_blank" rel="noopener noreferrer">MAP</a>`:""}</div>`;feed.appendChild(card)});updateMetrics()}
function countTypes(list,types){return list.filter(x=>types.includes(x.type)).length}
function updateMetrics(){const list=periodItems();document.getElementById("countAll").textContent=list.length;document.getElementById("periodCount").textContent=list.length;document.getElementById("countNew").textContent=countTypes(list,["opening","opening_soon"]);document.getElementById("countLimited").textContent=countTypes(list,["limited"]);document.getElementById("countClosed").textContent=countTypes(list,["closed"]);document.getElementById("countChange").textContent=countTypes(list,["relocation","renewal"]);document.getElementById("lastScan").textContent=meta.last_scan||"--";document.getElementById("dataUpdated").textContent=meta.data_updated||"--";document.getElementById("feedTitle").textContent=activeDays===1?"今日の更新情報":activeDays===7?"7日間の更新情報":"30日間の更新情報"}
filters.forEach(btn=>btn.addEventListener("click",()=>{filters.forEach(b=>b.classList.remove("active"));btn.classList.add("active");activeFilter=btn.dataset.filter;render()}));
periods.forEach(btn=>btn.addEventListener("click",()=>{periods.forEach(b=>b.classList.remove("active"));btn.classList.add("active");activeDays=Number(btn.dataset.days);render()}));
fetch("./data/ramen.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("data load failed");return r.json()}).then(data=>{meta=data.meta||{};items=(data.items||[]).sort((a,b)=>itemDate(b)-itemDate(a));render()}).catch(err=>{console.error(err);emptyState.hidden=false;emptyState.textContent="データを読み込めませんでした。"});
