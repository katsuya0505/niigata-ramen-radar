#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NIIGATA RAMEN RADAR collector v0.3

目的:
「ラーメン記事を集める」のではなく、
新店・開店予定・閉店・移転・リニューアル・限定など
“街の変化”だけを検知して data/ramen.json に保存する。

改善点:
- デモデータを自動除外
- 単なるおすすめ/紹介/まとめ記事を除外
- NEW誤判定を大幅に抑制
- 店名抽出を改善（引用符、記事末尾の店名を優先）
- 文字化けらしきタイトルを除外
- OPENING / LIMITED / CLOSED / RELOCATION / RENEWAL / BUZZ に分類
- 同じ記事・同じ店舗の重複をまとめる
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

HEADERS = {
    "User-Agent": "NIIGATA-RAMEN-RADAR/0.3 (+personal experimental project; respectful crawler)",
    "Accept-Language": "ja,en;q=0.8",
}

RAMEN_WORDS = [
    "ラーメン", "らーめん", "らぁめん", "らぁ麺", "拉麺",
    "中華そば", "中華蕎麦", "つけ麺", "つけめん",
    "油そば", "まぜそば", "担々麺", "タンメン", "ちゃんぽん",
    "麺屋", "麺処", "麺家"
]

NIIGATA_WORDS = [
    "新潟", "長岡", "上越", "三条", "燕", "新発田", "柏崎", "村上",
    "見附", "魚沼", "南魚沼", "十日町", "佐渡", "阿賀野", "胎内",
    "五泉", "加茂", "妙高", "糸魚川", "小千谷"
]

# “変化”を示す語
OPEN_WORDS = [
    "オープン", "OPEN", "開店", "新店", "新規出店", "出店",
    "初上陸", "グランドオープン", "プレオープン", "開業"
]
OPENING_SOON_WORDS = [
    "オープン予定", "開店予定", "近日オープン", "近日開店",
    "まもなくオープン", "今秋オープン", "今冬オープン",
    "今春オープン", "今夏オープン"
]
LIMITED_WORDS = [
    "限定", "期間限定", "季節限定", "数量限定",
    "新メニュー", "限定メニュー", "発売", "提供開始"
]
CLOSE_WORDS = [
    "閉店", "営業終了", "閉業", "閉鎖", "営業を終了"
]
RELOCATION_WORDS = [
    "移転", "移転オープン", "移転開店"
]
RENEWAL_WORDS = [
    "リニューアル", "改装", "リニューアルオープン", "改装オープン"
]

# 普通の紹介記事・まとめ記事である可能性が高い語
LISTICLE_WORDS = [
    "おすすめ", "まとめ", "選", "厳選", "特集", "食べ比べ",
    "食べるなら", "絶品", "人気店", "必見", "名店",
    "ランキング", "活動日誌", "食べ歩き"
]

# タイトルに変化語がなくても、本文だけでOPENと誤判定しないため、
# 強い変化判定には「タイトル」重視。
STRONG_CHANGE_GROUPS = {
    "closed": CLOSE_WORDS,
    "relocation": RELOCATION_WORDS,
    "renewal": RENEWAL_WORDS,
    "opening_soon": OPENING_SOON_WORDS,
    "opening": OPEN_WORDS,
    "limited": LIMITED_WORDS,
}

AREA_PATTERNS = [
    r"(新潟市(?:中央|西|東|北|南|江南|秋葉|西蒲)区)",
    r"(新潟市)",
    r"(長岡市|上越市|三条市|燕市|新発田市|柏崎市|村上市|見附市|魚沼市|南魚沼市|十日町市|佐渡市|阿賀野市|胎内市|五泉市|加茂市|妙高市|糸魚川市|小千谷市)"
]

@dataclass
class Candidate:
    source_id: str
    source_name: str
    url: str
    title: str
    context: str = ""

def now_jst() -> datetime:
    return datetime.now(JST)

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def contains_any(text: str, words: list[str]) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)

def looks_mojibake(text: str) -> bool:
    if not text:
        return True
    # 日本語媒体なのにキリル/ラテン拡張文字が異常に多い場合を除外
    suspicious = len(re.findall(r"[ҒҢұҚҲӒӓӧӱÐÑØÞßà-ÿ]", text))
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    return (suspicious + cyrillic) >= 3

def same_domain(url: str, base_url: str) -> bool:
    return urlparse(url).netloc.endswith(urlparse(base_url).netloc)

def fetch(session: requests.Session, url: str, timeout: int = 20) -> Optional[str]:
    try:
        r = session.get(url, timeout=timeout, headers=HEADERS)
        r.raise_for_status()
        if "text/html" not in r.headers.get("Content-Type", "text/html"):
            return None

        # requestsのapparent_encodingが壊す場合があるので、
        # HTMLにcharsetがあればそれを優先。なければUTF-8系を試す。
        enc = None
        m = re.search(r'charset=["\']?([A-Za-z0-9_\-]+)', r.text[:4000], re.I)
        if m:
            enc = m.group(1)
        if enc:
            r.encoding = enc
        elif not r.encoding or r.encoding.lower() in {"iso-8859-1", "ascii"}:
            r.encoding = "utf-8"

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
    h1_text = clean_text(h1.get_text(" ", strip=True)) if h1 else ""
    title_tag = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""

    # json-ldが媒体名だけなどの場合、h1を優先
    choices = [h1_text, jsonld_title or "", title_tag]
    choices = [x for x in choices if x and not looks_mojibake(x)]
    title = max(choices, key=len) if choices else ""

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
            if len(title) < 5 or looks_mojibake(title):
                continue

            url = urljoin(start_url, a["href"]).split("#")[0]
            if not same_domain(url, source["base_url"]):
                continue

            parent_text = clean_text(a.parent.get_text(" ", strip=True))[:600] if a.parent else ""
            ramen_listing = contains_any(title + " " + parent_text, RAMEN_WORDS)

            # PR TIMESの検索ページはラーメン専用なので候補を広めに取る
            if source["id"] == "prtimes":
                ramen_listing = True

            if not ramen_listing:
                continue

            path = urlparse(url).path.rstrip("/")
            skip_paths = {
                "", "/openclose", "/topics", "/gourmet",
                "/gourmet/special_ramen", "/postpic"
            }
            if path in skip_paths:
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

def change_type(title: str, body_head: str) -> Optional[str]:
    """
    v0.3ではタイトルを最優先。
    本文だけに「オープン」があっても、新店とは判定しない。
    """
    t = clean_text(title)
    body = clean_text(body_head[:1800])

    # 優先順位：閉店 > 移転 > リニューアル > 開店予定 > 開店 > 限定
    if contains_any(t, CLOSE_WORDS):
        return "closed"
    if contains_any(t, RELOCATION_WORDS):
        return "relocation"
    if contains_any(t, RENEWAL_WORDS):
        return "renewal"
    if contains_any(t, OPENING_SOON_WORDS):
        return "opening_soon"
    if contains_any(t, OPEN_WORDS):
        return "opening"
    if contains_any(t, LIMITED_WORDS):
        return "limited"

    # タイトルに変化語がなくても、本文冒頭で明確な閉店・移転・予定がある場合のみ採用
    for typ, words in [
        ("closed", CLOSE_WORDS),
        ("relocation", RELOCATION_WORDS),
        ("renewal", RENEWAL_WORDS),
        ("opening_soon", OPENING_SOON_WORDS),
    ]:
        if contains_any(body, words):
            return typ

    return None

def is_generic_article(title: str, typ: Optional[str]) -> bool:
    """
    まとめ記事・紹介記事は基本除外。
    ただしタイトル自体に強い変化語があれば採用。
    """
    if not contains_any(title, LISTICLE_WORDS):
        return False

    if typ in {"closed", "relocation", "renewal", "opening_soon"}:
        return False

    # 「おすすめ5選」「まとめ5選」などは除外
    if re.search(r"\d+\s*選", title):
        return True
    return True

def extract_area(text: str) -> str:
    for pat in AREA_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return "新潟県"

def quoted_chunks(title: str) -> list[str]:
    patterns = [
        r"「([^」]{2,60})」",
        r"『([^』]{2,60})』",
        r"“([^”]{2,60})”",
        r"【([^】]{2,60})】",
    ]
    out = []
    for pat in patterns:
        out.extend(re.findall(pat, title))
    return [clean_text(x) for x in out]

def score_shop_candidate(c: str) -> int:
    score = 0
    if len(c) <= 35:
        score += 10
    if contains_any(c, ["店", "麺", "亭", "家", "食堂", "そば", "RAMEN", "Ramen"]):
        score += 25
    if re.search(r"(本店|支店|店)$", c):
        score += 20
    if contains_any(c, LISTICLE_WORDS):
        score -= 40
    if re.search(r"\d+\s*選", c):
        score -= 60
    if contains_any(c, ["新潟市", "長岡市", "駅近く", "周辺"]):
        score -= 15
    return score

def extract_shop_name(title: str) -> str:
    # 1. 引用符内を最優先
    chunks = quoted_chunks(title)
    scored = [(score_shop_candidate(c), c) for c in chunks]
    scored = [x for x in scored if x[0] > 0]
    if scored:
        scored.sort(reverse=True)
        return scored[0][1][:50]

    # 2. 「地域『店名』」形式がなくても、末尾に店舗名があるケース
    # 例: / 新潟市西区「万人家 大学前店」
    m = re.search(
        r"(?:新潟市(?:中央|西|東|北|南|江南|秋葉|西蒲)区|長岡市|上越市|三条市|燕市|新発田市|柏崎市|南魚沼市)[\s　]*[「『]?([^」』｜|/]{2,50})[」』]?\s*$",
        title
    )
    if m:
        candidate = clean_text(m.group(1))
        if score_shop_candidate(candidate) > 0:
            return candidate

    # 3. 「○○がオープン」「○○閉店」など
    parts = re.split(
        r"(?:が|、|！|!|｜|\||/|-).{0,5}(?:オープン|OPEN|開店|閉店|移転|リニューアル)",
        title,
        maxsplit=1
    )
    if parts:
        candidate = clean_text(parts[0])
        candidate = re.sub(r"^[【〖].+?[】〗]\s*", "", candidate)
        if 2 <= len(candidate) <= 50 and not contains_any(candidate, LISTICLE_WORDS):
            return candidate

    # 最後の保険
    x = re.sub(r"^[【〖].+?[】〗]\s*", "", title)
    x = re.split(r"[！!｜|/]", x)[0]
    return clean_text(x)[:50] or "店舗情報"

def normalize_key(name: str) -> str:
    x = name.lower()
    x = re.sub(r"[ 　\t\r\n・･\-ー_（）()【】〖〗『』「」“”\"'.,!！?？/\\]", "", x)
    for w in ["ラーメン", "らーめん", "らぁめん", "拉麺", "麺屋", "中華そば"]:
        x = x.replace(w, "")
    return x[:60]

def stable_id(key: str) -> int:
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:10], 16)

def make_summary(source_name: str, typ: str) -> str:
    labels = {
        "opening": "新店・開店情報",
        "opening_soon": "開店予定情報",
        "limited": "限定・新メニュー情報",
        "closed": "閉店情報",
        "relocation": "移転情報",
        "renewal": "リニューアル情報",
        "buzz": "話題情報",
    }
    return f"{source_name}で{labels.get(typ, '新着情報')}を検知しました。詳細は情報源で確認できます。"

def collect() -> list[dict]:
    cfg = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    session = requests.Session()
    raw_items: list[dict] = []

    for source in cfg["sources"]:
        print(f"\n[SCAN] {source['name']}")
        candidates = listing_candidates(session, source)
        print(f"  listing candidates: {len(candidates)}")

        max_pages = int(source.get("max_detail_pages", 14))
        checked = 0

        for c in candidates:
            if checked >= max_pages:
                break
            checked += 1
            time.sleep(0.5)

            html = fetch(session, c.url)
            if not html:
                continue

            page_title, body_text, published = page_title_and_text(html)
            title = page_title or c.title
            if looks_mojibake(title):
                print(f"  - skip mojibake: {c.url}")
                continue

            combined = " ".join([title, c.context, body_text[:5000]])

            if not contains_any(combined, RAMEN_WORDS):
                continue

            if source.get("require_niigata_on_detail", False) and not is_niigata_related(combined):
                continue

            if source["id"] in {"niikei", "komachi", "025"} and not is_niigata_related(combined):
                continue

            typ = change_type(title, body_text)

            # “変化”がなければ掲載しない
            if typ is None:
                continue

            # まとめ・おすすめ系は除外
            if is_generic_article(title, typ):
                continue

            shop = extract_shop_name(title)
            if looks_mojibake(shop):
                continue

            area = extract_area(title + " " + body_text[:2500])
            detected = now_jst().isoformat(timespec="seconds")

            raw_items.append({
                "source_id": source["id"],
                "source_name": source["name"],
                "source_url": c.url,
                "source_title": title,
                "name": shop,
                "area": area,
                "type": typ,
                "published_at": published,
                "detected_at": detected,
            })
            print(f"  + {shop} [{typ}]")

    return merge_duplicates(raw_items)

def merge_duplicates(raw_items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}

    for x in raw_items:
        key = normalize_key(x["name"])
        if len(key) < 2:
            key = normalize_key(x["source_title"])

        # 同一店のカテゴリ違いを分けすぎない
        groups.setdefault(key, []).append(x)

    merged = []

    for key, group in groups.items():
        priority = {
            "closed": 6,
            "relocation": 5,
            "renewal": 4,
            "opening_soon": 3,
            "opening": 2,
            "limited": 1,
            "buzz": 0,
        }

        group.sort(
            key=lambda x: (
                priority.get(x["type"], 0),
                len(x["source_title"])
            ),
            reverse=True
        )

        lead = group[0]
        unique_sources = {}
        for x in group:
            unique_sources[(x["source_name"], x["source_url"])] = {
                "name": x["source_name"],
                "url": x["source_url"],
                "title": x["source_title"]
            }

        source_links = list(unique_sources.values())
        source_names = sorted({x["source_name"] for x in group})
        source_count = len(source_names)

        confidence = min(98, 55 + max(0, source_count - 1) * 15)

        merged.append({
            "id": stable_id(key),
            "type": lead["type"],
            "name": lead["name"],
            "area": lead["area"],
            "summary": make_summary(lead["source_name"], lead["type"]),
            "detected_at": lead["detected_at"],
            "published_at": lead.get("published_at"),
            "tags": [
                lead["type"].upper(),
                lead["area"],
                f"{source_count} SOURCES" if source_count > 1 else lead["source_name"]
            ],
            "source_url": lead["source_url"],
            "sources": source_links,
            "source_count": source_count,
            "confidence": confidence,
            "map_url": "https://www.google.com/maps/search/" + requests.utils.quote(
                f"{lead['name']} {lead['area']}"
            )
        })

    merged.sort(
        key=lambda x: x.get("published_at") or x.get("detected_at") or "",
        reverse=True
    )
    return merged

def is_demo_item(item: dict) -> bool:
    name = str(item.get("name", "")).lower()
    summary = str(item.get("summary", "")).lower()
    demo_words = ["sample", "demo", "radar"]
    return (
        any(w in name for w in demo_words)
        or "デモ" in summary
        or "サンプル" in summary
    )

def load_existing() -> dict:
    if not DATA_FILE.exists():
        return {"meta": {}, "items": []}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"meta": {}, "items": []}

def merge_with_existing(new_items: list[dict], keep: int = 80) -> dict:
    old = load_existing()

    existing = {}
    for x in old.get("items", []):
        if is_demo_item(x):
            continue
        if x.get("id") is None:
            continue

        # v0.3からは“変化情報”以外の古いbuzz/誤判定を原則捨てる
        if x.get("type") not in {
            "opening", "opening_soon", "limited",
            "closed", "relocation", "renewal"
        }:
            continue

        existing[str(x["id"])] = x

    for item in new_items:
        sid = str(item["id"])
        if sid in existing:
            prev = existing[sid]
            item["detected_at"] = prev.get("detected_at", item["detected_at"])
        existing[sid] = item

    items = list(existing.values())
    items.sort(
        key=lambda x: x.get("published_at") or x.get("detected_at") or "",
        reverse=True
    )
    items = items[:keep]

    stamp = now_jst().strftime("%Y-%m-%d %H:%M")

    return {
        "meta": {
            "last_scan": stamp,
            "data_updated": stamp,
            "mode": "live",
            "version": "0.3",
            "source_count": 5,
            "detected_this_scan": len(new_items),
            "item_count": len(items),
            "policy": "change-only"
        },
        "items": items
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=80)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("NIIGATA RAMEN RADAR collector v0.3")
    print("POLICY: CHANGE ONLY")
    new_items = collect()
    result = merge_with_existing(new_items, keep=args.keep)

    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:14000])
        return

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n[DONE] {DATA_FILE}")
    print(f"       detected: {len(new_items)}")
    print(f"       stored:   {len(result['items'])}")

if __name__ == "__main__":
    main()
