
const feed = document.getElementById("feed");
const emptyState = document.getElementById("emptyState");
const filters = document.querySelectorAll(".filter");
let items = [];
let meta = {};

const badgeLabel = {
  new: "NEW OPEN",
  limited: "LIMITED",
  buzz: "BUZZ"
};

function formatDate(iso) {
  if (!iso) return "日付未確認";
  const d = new Date(iso);
  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(d);
}

function render(list) {
  feed.innerHTML = "";
  emptyState.hidden = list.length !== 0;

  list.forEach(item => {
    const card = document.createElement("article");
    card.className = "card";
    const tags = (item.tags || []).map(t => `<span class="tag">${t}</span>`).join("");

    card.innerHTML = `
      <div class="card-top">
        <span class="badge ${item.type}">${badgeLabel[item.type] || "INFO"}</span>
        <span class="date">${formatDate(item.detected_at)}</span>
      </div>
      <div>
        <h4>${item.name}</h4>
        <div class="location">📍 ${item.area}</div>
      </div>
      <p class="desc">${item.summary}</p>
      <div class="tags">${tags}</div>
      ${item.source_count ? `<div class="radar-evidence">📡 ${item.source_count} SOURCE${item.source_count > 1 ? "S" : ""} DETECTED · CONFIDENCE ${item.confidence || 50}%</div>` : ""}
      <div class="card-actions">
        ${item.source_url ? `<a class="link" href="${item.source_url}" target="_blank" rel="noopener noreferrer">情報源を見る</a>` : ""}
        ${item.map_url ? `<a class="link secondary" href="${item.map_url}" target="_blank" rel="noopener noreferrer">MAP</a>` : ""}
      </div>
    `;
    feed.appendChild(card);
  });
}

function updateMetrics() {
  document.getElementById("count24").textContent = items.length;
  document.getElementById("countNew").textContent = items.filter(x => x.type === "new").length;
  document.getElementById("countLimited").textContent = items.filter(x => x.type === "limited").length;
  document.getElementById("countBuzz").textContent = items.filter(x => x.type === "buzz").length;
  document.getElementById("lastScan").textContent = meta.last_scan || "--";
  document.getElementById("dataUpdated").textContent = meta.data_updated || "--";
}

filters.forEach(btn => {
  btn.addEventListener("click", () => {
    filters.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.dataset.filter;
    render(target === "all" ? items : items.filter(x => x.type === target));
  });
});

fetch("./data/ramen.json", { cache: "no-store" })
  .then(r => {
    if (!r.ok) throw new Error("data load failed");
    return r.json();
  })
  .then(data => {
    meta = data.meta || {};
    items = (data.items || []).sort((a,b) => new Date(b.detected_at) - new Date(a.detected_at));
    updateMetrics();
    render(items);
  })
  .catch(err => {
    console.error(err);
    emptyState.hidden = false;
    emptyState.textContent = "データを読み込めませんでした。";
  });
