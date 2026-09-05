const feed = document.getElementById("feed");
const emptyState = document.getElementById("emptyState");
const filters = document.querySelectorAll(".filter");

let items = [];
let meta = {};

const badgeLabel = {
  opening: "NEW OPEN",
  opening_soon: "OPENING SOON",
  limited: "LIMITED",
  closed: "CLOSED",
  relocation: "RELOCATION",
  renewal: "RENEWAL"
};

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(iso) {
  if (!iso) return "日付未確認";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(d);
}

function groupMatches(item, target) {
  if (target === "all") return true;
  if (target === "opening") return ["opening", "opening_soon"].includes(item.type);
  if (target === "limited") return item.type === "limited";
  if (target === "closed") return item.type === "closed";
  if (target === "change") return ["relocation", "renewal"].includes(item.type);
  return item.type === target;
}

function imageMarkup(item) {
  if (!item.image_url) {
    return `
      <div class="card-media no-image">
        <div class="radar-placeholder"><span></span><b>NO IMAGE</b></div>
      </div>`;
  }

  return `
    <div class="card-media has-image">
      <img
        src="${esc(item.image_url)}"
        alt="${esc(item.name)}"
        loading="lazy"
        referrerpolicy="no-referrer"
      >
      <div class="radar-placeholder image-fallback" hidden><span></span><b>IMAGE UNAVAILABLE</b></div>
    </div>`;
}

function render(list) {
  feed.innerHTML = "";
  emptyState.hidden = list.length !== 0;

  list.forEach(item => {
    const card = document.createElement("article");
    card.className = "card";

    const tags = (item.tags || [])
      .map(t => `<span class="tag">${esc(t)}</span>`)
      .join("");

    card.innerHTML = `
      ${imageMarkup(item)}
      <div class="card-top">
        <span class="badge ${esc(item.type)}">${badgeLabel[item.type] || "INFO"}</span>
        <span class="date">${formatDate(item.detected_at)}</span>
      </div>
      <div>
        <h4>${esc(item.name)}</h4>
        <div class="location">📍 ${esc(item.area)}</div>
      </div>
      <p class="desc">${esc(item.summary)}</p>
      <div class="tags">${tags}</div>
      ${item.source_count ? `
        <div class="radar-evidence">
          📡 ${item.source_count} SOURCE${item.source_count > 1 ? "S" : ""} DETECTED
          · CONFIDENCE ${item.confidence || 55}%
        </div>` : ""}
      <div class="card-actions">
        ${item.source_url ? `<a class="link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">情報源を見る</a>` : ""}
        ${item.map_url ? `<a class="link secondary" href="${esc(item.map_url)}" target="_blank" rel="noopener noreferrer">MAP</a>` : ""}
      </div>
    `;

    const img = card.querySelector(".card-media img");
    if (img) {
      img.addEventListener("error", () => {
        img.hidden = true;
        const fallback = card.querySelector(".image-fallback");
        if (fallback) fallback.hidden = false;
      });
    }

    feed.appendChild(card);
  });
}

function countTypes(types) {
  return items.filter(x => types.includes(x.type)).length;
}

function updateMetrics() {
  document.getElementById("count24").textContent = meta.detected_this_scan ?? items.length;
  document.getElementById("countNew").textContent = countTypes(["opening", "opening_soon"]);
  document.getElementById("countLimited").textContent = countTypes(["limited"]);
  document.getElementById("countClosed").textContent = countTypes(["closed"]);
  document.getElementById("countChange").textContent = countTypes(["relocation", "renewal"]);
  document.getElementById("lastScan").textContent = meta.last_scan || "--";
  document.getElementById("dataUpdated").textContent = meta.data_updated || "--";
}

filters.forEach(btn => {
  btn.addEventListener("click", () => {
    filters.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.dataset.filter;
    render(items.filter(item => groupMatches(item, target)));
  });
});

fetch("./data/ramen.json", { cache: "no-store" })
  .then(r => {
    if (!r.ok) throw new Error("data load failed");
    return r.json();
  })
  .then(data => {
    meta = data.meta || {};
    items = (data.items || []).sort(
      (a, b) => new Date(b.detected_at || 0) - new Date(a.detected_at || 0)
    );
    updateMetrics();
    render(items);
  })
  .catch(err => {
    console.error(err);
    emptyState.hidden = false;
    emptyState.textContent = "データを読み込めませんでした。";
  });
