"""GitHub Actions에서 RSS를 fetch해 news.json으로 저장 (오늘치 KST 기준)"""
import json, re, time
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

SOURCES = [
    {"key": "yna",      "name": "연합뉴스", "cls": "yna",
     "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"key": "mk",       "name": "매일경제", "cls": "mk",
     "url": "https://www.mk.co.kr/rss/40300001/"},
    {"key": "hankyung", "name": "한국경제", "cls": "hankyung",
     "url": "https://www.hankyung.com/feed/economy"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; news-fetcher/1.0)"}

def strip_tags(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def is_today_kst(pub_str):
    if not pub_str:
        return True  # 날짜 없으면 포함
    try:
        dt = parsedate_to_datetime(pub_str).astimezone(KST)
        return dt.date() == datetime.now(KST).date()
    except Exception:
        return True  # 파싱 실패시 포함

def fetch_one(src):
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = ""
        items = root.findall("./channel/item") or root.findall(".//item")
        articles = []
        for it in items[:15]:
            def t(tag):
                el = it.find(tag)
                return el.text or "" if el is not None else ""
            title = strip_tags(t("title")).replace("[CDATA[", "").replace("]]", "")
            link  = strip_tags(t("link")) or strip_tags(t("guid"))
            desc  = strip_tags(t("description"))[:200]
            pub   = t("pubDate").strip()
            if title and is_today_kst(pub):
                articles.append({
                    "title": title, "link": link, "desc": desc,
                    "pub": pub, "src": src["key"],
                    "srcName": src["name"], "cls": src["cls"]
                })
        print(f"  {src['key']}: {len(articles)}건")
        return articles
    except Exception as e:
        print(f"  {src['key']} 실패: {e}")
        return []

articles = []
for src in SOURCES:
    articles.extend(fetch_one(src))
    time.sleep(0.5)

articles.sort(key=lambda a: a.get("pub",""), reverse=True)
result = {
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "count": len(articles),
    "articles": articles
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n완료: {len(articles)}건 → news.json")
