#!/usr/bin/env python3
"""Fetch latest news per category from Google News RSS and write data.json.
No API key required. Runs entirely on stdlib."""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape

JST = timezone(timedelta(hours=9))

CATEGORIES = {
    "tennis": {
        "query": "テニス ATP OR 錦織",
        "keywords": ["ATPツアー", "錦織圭", "ウィンブルドン"],
        "tag": "テニス",
    },
    "music": {
        "query": "サカナクション OR 離婚伝説 OR THE BAWDIES OR ヨナヲ 新曲 OR ライブ",
        "keywords": ["サカナクション", "離婚伝説", "THE BAWDIES", "ヨナヲ"],
        "tag": "音楽",
    },
    "tech": {
        "query": "AI 新機能 OR ガジェット 新製品",
        "keywords": ["AIニュース", "新製品", "ガジェット"],
        "tag": "ガジェット・AI",
    },
    "culture": {
        "query": "東京 展覧会 OR 川崎 イベント OR 世界遺産 離島 旅行",
        "keywords": ["展覧会", "川崎/鶴見", "世界遺産・離島"],
        "tag": "アート・旅",
    },
}

MAX_ITEMS = 4
UA = "Mozilla/5.0 (compatible; HobbyDashboardBot/1.0)"


def strip_html(text):
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_raw(query):
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=ja&gl=JP&ceid=JP:ja"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as res:
        xml_data = res.read()
    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall("./channel/item"):
        title = strip_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "Google News"
        pub_date_raw = item.findtext("pubDate", "")
        try:
            pub_dt = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z")
            pub_dt = pub_dt.replace(tzinfo=timezone.utc).astimezone(JST)
        except ValueError:
            pub_dt = datetime.now(JST)
        date_str = pub_dt.strftime("%Y/%m/%d")
        description = strip_html(item.findtext("description", ""))
        # Google News description often duplicates the title; fall back gracefully
        summary = description if description and description != title else title
        items.append({
            "title": title,
            "url": link,
            "summary": summary[:160],
            "source": source,
            "date": date_str,
            "tag": "ニュース",
            "score": 1,
            "_dt": pub_dt,
        })
    items.sort(key=lambda x: x["_dt"], reverse=True)
    return items


def fetch_items(query):
    """Fetch recent items, preferring the last 3 days but widening the
    window if too few recent results are found."""
    now = datetime.now(JST)
    raw = []
    for window_days, suffix in ((3, " when:3d"), (14, " when:14d"), (None, "")):
        raw = fetch_raw(query + suffix)
        if window_days is not None:
            raw = [it for it in raw if (now - it["_dt"]).days <= window_days]
        if len(raw) >= 2 or suffix == "":
            break
    for it in raw:
        del it["_dt"]
    return raw[:MAX_ITEMS]


def main():
    data = {"updated_at": datetime.now(JST).strftime("%Y/%m/%d %H:%M")}
    for key, conf in CATEGORIES.items():
        try:
            data[key] = fetch_items(conf["query"])
        except Exception as e:
            print(f"Failed to fetch {key}: {e}")
            data[key] = []
        data[f"{key}_keywords"] = conf["keywords"]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
