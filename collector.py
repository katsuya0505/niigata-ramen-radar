#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NIIGATA RAMEN RADAR collector v0.2

5つの公開Webサイトの一覧ページから候補リンクを取得し、
ラーメン関連かつ新潟関連の記事だけを data/ramen.json に保存します。

- 記事本文や写真は保存しません。
- 表示用の要約は、取得したタイトルを元に短い独自文を生成します。
- robots.txt / 利用規約 / サイト側の仕様変更により取得できない場合があります。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "ramen.json"
SOURCES_FILE = ROOT / "sources.json"
JST = timezone(timedelta(hours=9))

RAMEN_WORDS = [
    "ラーメン", "らーめん", "らぁめん", "らぁ麺", "拉麺",
    "中華そば", "中華蕎麦", "つけ麺", "つけめん", "油そば",
    "まぜそば", "担々麺", "タンメン", "ちゃんぽん", "麺屋",
]
NIIGATA_WORDS = [
    "新潟", "長岡", "上越", "三条", "燕", "新発田", "柏崎", "村上",
    "見附", "魚沼", "南魚沼", "十日町", "佐渡", "阿賀野", "胎内",
    "五泉", "加茂", "妙高", "糸魚川", "小千谷",
]
NEW_WORDS = ["オープン", "OPEN", "開店", "新店", "初上陸", "出店", "移転", "リニューアル"]
LIMITED_WORDS = ["限定", "期間限定", "季節限定", "夏季", "冬季", "新メニュー", "発売"]
CLOSE_WORDS = ["閉店", "営業終了"]
SKIP_WORDS = ["まとめ", "おすすめ", "ランキング", "選", "特集"]

AREA_PATTERNS = [
    r"(新潟市(?:中央|西|東|北|南|江南|秋葉|西蒲)区)",
    r"(新潟市)",
    r"(長岡市|上越市|三条市|燕市|新発田市|柏崎市|村上市|見附市|魚沼市|南魚沼市|十日町市|佐渡市|阿賀野市|胎内市|五泉市|加茂市|妙高市|糸魚川市|小千谷市)",
]

HEADERS = {
    "User-Agent": "NIIGATA-RAMEN-RADAR/0.2 (+personal experimental project; respectful crawler)",
    "Accept-Language": "ja,en;q=0.8",
}

@dataclass
class Candidate:
    source_id: str
    source_name: str
    url: str
    title: str
    context: str = ""
    published_at: Optional[str] = None

def now_jst() -> datetime:
    return datetime.now(JST)

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def contains_any(text: str, words: list[str]) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)

def same_domain(url: str, base_url: str) -> bool:
    return urlparse(url).netloc.endswith(urlparse(base_url).netloc)

def fetch(session: requests.Session, url: str, timeout: int = 15) -> Optional[str]:
    try:
        r = session.get(url, timeout=timeout, headers=HEADERS)
        r.raise_for_status()
        if "text/html" not in r.headers.get("Content-Type", "text/html"):
            return None
        r.encoding = r.apparent_encoding or r.encoding
        return r.text
    except requests.RequestException as e:
        print(f"[WARN] fetch failed: {url} ({e})")
        return None

def extract_jsonld(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    headline = None
    published = None
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = node.string or node.get_text()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue

        stack = obj if isinstance(obj, list) else [obj]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if not headline and isinstance(x.get("headline"), str):
                    headline = clean_text(x["headline"])
                if not published and isinstance(x.get("datePublished"), str):
                    published = x["datePublished"]
                for v in x.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(x, list):
                stack.extend(x)
    return headline, published

def page_title_and_text(html: str) -> tuple[str, str, Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    jsonld_title, published = extract_jsonld(soup)
    h1 = soup.find("h1")
    title = jsonld_title or (clean_text(h1.get_text(" ", strip=True)) if h1 else "")
    if not title and soup.title:
        title = clean_text(soup.title.get_text(" ", strip=True))
    # 本文を保存することはなく、判定のためだけに一時利用
    body_text = clean_text(soup.get_text(" ", strip=True))
    return title, body_text[:25000], published

def listing_candidates(session: requests.Session, source: dict) -> list[Candidate]:
    found: dict[str, Candidate] = {}
    for start_url in source["start_urls"]:
        html = fetch(session, start_url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            title = clean_text(a.get_text(" ", strip=True))
            if len(title) < 5:
                continue
            url = urljoin(start_url, a["href"]).split("#")[0]
            if not same_domain(url, source["base_url"]):
                continue
            # 一覧ページではラーメン語があるものを優先。
            # PR TIMES等は一覧自体がラーメン専用なので全候補を許容。
            ramen_listing = contains_any(title, RAMEN_WORDS)
            if source["id"] == "prtimes":
                ramen_listing = True
            if not ramen_listing:
                # 親要素の短い文脈も確認
                parent_text = clean_text(a.parent.get_text(" ", strip=True))[:500] if a.parent else ""
                if not contains_any(parent_text, RAMEN_WORDS):
                    continue
            else:
                parent_text = clean_text(a.parent.get_text(" ", strip=True))[:500] if a.parent else ""

            # ナビゲーションやカテゴリURLを避ける簡易判定
            path = urlparse(url).path
            if path in {"/", "/openclose/", "/topics/", "/gourmet/", "/gourmet/special_ramen", "/postpic/"}:
                continue

            found[url] = Candidate(
                source_id=source["id"],
                source_name=source["name"],
                url=url,
                title=title,
                context=parent_text,
            )
    return list(found.values())

def is_niigata_related(text: str) -> bool:
    return contains_any(text, NIIGATA_WORDS)

def classify(text: str) -> str:
    if contains_any(text, CLOSE_WORDS):
        return "buzz"  # v0.2フロントは3分類のため、閉店は話題扱い
    if contains_any(text, NEW_WORDS):
        return "new"
    if contains_any(text, LIMITED_WORDS):
        return "limited"
    return "buzz"

def extract_area(text: str) -> str:
    for pat in AREA_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return "新潟県"

def quote_chunks(title: str) -> list[str]:
    chunks = []
    for pat in [r"『([^』]{2,40})』", r"「([^」]{2,40})」", r"“([^”]{2,40})”", r"【([^】]{2,40})】"]:
        chunks.extend(re.findall(pat, title))
    return [clean_text(x) for x in chunks]

def extract_shop_name(title: str) -> str:
    chunks = quote_chunks(title)
    # 店名候補：引用内で、一般的な説明語より固有名詞らしいものを優先
    reject = ["ラーメン", "新店", "まとめ", "限定", "おすすめ", "オープン", "新潟"]
    candidates = []
    for c in chunks:
        score = len(c)
        if any(r == c for r in reject):
            score -= 100
        if contains_any(c, ["店", "麺", "亭", "屋", "家", "食堂", "そば", "RAMEN", "Ramen"]):
            score += 20
        candidates.append((score, c))
    if candidates:
        candidates.sort(reverse=True)
        best = candidates[0][1]
        if len(best) <= 40:
            return best

    # 引用がない場合はタイトルを短縮して表示名に使う
    x = re.sub(r"^[【〖].+?[】〗]", "", title)
    x = re.split(r"[！!｜|/-]", x)[0]
    return clean_text(x)[:42] or "ラーメン情報"

def normalize_key(name: str) -> str:
    x = name.lower()
    x = re.sub(r"[ 　\t\r\n・･\-ー_（）()【】〖〗『』「」“”\"'.,!！?？/\\]", "", x)
    for w in ["新潟店", "本店", "支店", "ラーメン", "らーめん", "らぁめん", "拉麺", "麺屋", "中華そば"]:
        x = x.replace(w, "")
    return x[:50]

def make_summary(source_name: str, title: str, item_type: str) -> str:
    if item_type == "new":
        lead = "新店・開店に関する情報"
    elif item_type == "limited":
        lead = "限定・新メニューに関する情報"
    else:
        lead = "ラーメンに関する新着情報"
    return f"{source_name}で{lead}を検知しました。詳細は情報源で確認できます。"

def stable_id(key: str) -> int:
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:10], 16)

def collect() -> list[dict]:
    cfg = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    session = requests.Session()
    raw_items: list[dict] = []

    for source in cfg["sources"]:
        print(f"\n[SCAN] {source['name']}")
        candidates = listing_candidates(session, source)
        print(f"  listing candidates: {len(candidates)}")
        max_pages = int(source.get("max_detail_pages", 10))

        # 新しそうな候補を先頭から一定数だけ確認し、負荷を抑える
        checked = 0
        for c in candidates:
            if checked >= max_pages:
                break
            checked += 1
            time.sleep(0.6)

            html = fetch(session, c.url)
            if not html:
                continue
            page_title, body_text, published = page_title_and_text(html)
            title = page_title or c.title
            combined = " ".join([title, c.context, body_text[:6000]])

            if not contains_any(combined, RAMEN_WORDS):
                continue
            if source.get("require_niigata_on_detail", False) and not is_niigata_related(combined):
                continue
            # それ以外の媒体も新潟地域メディアだが、全国記事混入防止でチェック
            if not is_niigata_related(combined) and source["id"] in {"niikei", "komachi", "025"}:
                continue

            item_type = classify(title + " " + body_text[:2500])
            shop = extract_shop_name(title)
            area = extract_area(title + " " + body_text[:3000])
            detected = now_jst().isoformat(timespec="seconds")

            raw_items.append({
                "source_id": source["id"],
                "source_name": source["name"],
                "source_url": c.url,
                "source_title": title,
                "name": shop,
                "area": area,
                "type": item_type,
                "published_at": published,
                "detected_at": detected,
            })
            print(f"  + {shop} [{item_type}]")

    return merge_duplicates(raw_items)

def merge_duplicates(raw_items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for x in raw_items:
        key = normalize_key(x["name"])
        if len(key) < 2:
            key = normalize_key(x["source_title"])
        groups.setdefault(key, []).append(x)

    merged = []
    for key, group in groups.items():
        # 主要表示は最も情報が具体的なタイトルを持つもの
        group.sort(key=lambda x: (x["type"] == "new", len(x["source_title"])), reverse=True)
        lead = group[0]
        source_names = sorted({x["source_name"] for x in group})
        source_links = [
            {"name": x["source_name"], "url": x["source_url"], "title": x["source_title"]}
            for x in group
        ]

        score = min(98, 50 + (len(source_names)-1)*15)
        tags = [lead["type"].upper(), lead["area"], f"{len(source_names)} source" if len(source_names) > 1 else source_names[0]]

        merged.append({
            "id": stable_id(key),
            "type": lead["type"],
            "name": lead["name"],
            "area": lead["area"],
            "summary": make_summary(lead["source_name"], lead["source_title"], lead["type"]),
            "detected_at": lead["detected_at"],
            "published_at": lead.get("published_at"),
            "tags": tags,
            "source_url": lead["source_url"],
            "sources": source_links,
            "source_count": len(source_names),
            "confidence": score,
            "map_url": "https://www.google.com/maps/search/" + requests.utils.quote(f"{lead['name']} {lead['area']}")
        })

    merged.sort(key=lambda x: x.get("published_at") or x["detected_at"], reverse=True)
    return merged

def load_existing() -> dict:
    if not DATA_FILE.exists():
        return {"meta": {}, "items": []}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"meta": {}, "items": []}

def merge_with_existing(new_items: list[dict], keep: int = 80) -> dict:
    old = load_existing()
    existing = {str(x.get("id")): x for x in old.get("items", []) if x.get("id") is not None}

    for item in new_items:
        sid = str(item["id"])
        if sid in existing:
            prev = existing[sid]
            # 初回検知日時は残す
            item["detected_at"] = prev.get("detected_at", item["detected_at"])
        existing[sid] = item

    items = list(existing.values())
    items.sort(key=lambda x: x.get("published_at") or x.get("detected_at") or "", reverse=True)
    items = items[:keep]

    stamp = now_jst().strftime("%Y-%m-%d %H:%M")
    return {
        "meta": {
            "last_scan": stamp,
            "data_updated": stamp,
            "mode": "live",
            "source_count": 5,
            "detected_this_scan": len(new_items)
        },
        "items": items
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=80, help="保存する最大件数")
    parser.add_argument("--dry-run", action="store_true", help="JSONを書き換えず結果だけ表示")
    args = parser.parse_args()

    print("NIIGATA RAMEN RADAR collector v0.2")
    new_items = collect()
    result = merge_with_existing(new_items, keep=args.keep)

    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:12000])
        return

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DONE] {DATA_FILE}")
    print(f"       {len(result['items'])} items / {len(new_items)} detected this scan")

if __name__ == "__main__":
    main()
