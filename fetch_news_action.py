"""GitHub Actions에서 RSS를 fetch해 news.json으로 저장"""
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

# 카테고리 여러 개로 분산해 RSS 15개 한계 돌파
SOURCES = [
    {"key": "yna",      "name": "연합뉴스",   "cls": "yna",
     "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"key": "yna",      "name": "연합뉴스",   "cls": "yna",
     "url": "https://www.yna.co.kr/rss/finance.xml"},
    {"key": "mk",       "name": "매일경제",   "cls": "mk",
     "url": "https://www.mk.co.kr/rss/40300001/"},
    {"key": "mk",       "name": "매일경제",   "cls": "mk",
     "url": "https://www.mk.co.kr/rss/50200011/"},
    {"key": "hankyung", "name": "한국경제",   "cls": "hankyung",
     "url": "https://www.hankyung.com/feed/economy"},
    {"key": "hankyung", "name": "한국경제",   "cls": "hankyung",
     "url": "https://www.hankyung.com/feed/finance"},
    {"key": "newsis",   "name": "뉴시스",     "cls": "newsis",
     "url": "https://www.newsis.com/RSS/economy/"},
    {"key": "mt",       "name": "머니투데이", "cls": "mt",
     "url": "https://news.mt.co.kr/newArticleRSS.html?pCategory=A01"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; news-fetcher/1.0)"}
PER_SOURCE = 30

def strip_tags(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def pub_date_kst(pub_str):
    if not pub_str:
        return None
    try:
        return parsedate_to_datetime(pub_str).astimezone(KST).date()
    except Exception:
        return None

def fetch_one(src):
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall("./channel/item") or root.findall(".//item")
        articles = []
        for it in items[:PER_SOURCE]:
            def t(tag):
                el = it.find(tag)
                return el.text or "" if el is not None else ""
            title = strip_tags(t("title")).replace("[CDATA[", "").replace("]]", "")
            link  = strip_tags(t("link")) or strip_tags(t("guid"))
            desc  = strip_tags(t("description"))[:200]
            pub   = t("pubDate").strip()
            if title:
                articles.append({
                    "title": title, "link": link, "desc": desc,
                    "pub": pub, "src": src["key"],
                    "srcName": src["name"], "cls": src["cls"]
                })
        print(f"  {src['key']} ({src['url'].split('/')[-1][:20]}): {len(articles)}건")
        return articles
    except Exception as e:
        print(f"  {src['key']} 실패: {e}")
        return []

# 전체 수집
raw = []
for src in SOURCES:
    raw.extend(fetch_one(src))
    time.sleep(0.3)

# 중복 링크 먼저 제거
seen, raw = set(), [a for a in raw if not (a["link"] in seen or seen.add(a["link"]))]

# 최근 3일치만 유지 (날짜 미상 포함)
today = datetime.now(KST).date()
cutoff = today - timedelta(days=2)

articles = [
    a for a in raw
    if pub_date_kst(a["pub"]) is None or pub_date_kst(a["pub"]) >= cutoff
]

articles.sort(key=lambda a: a.get("pub", ""), reverse=True)

print(f"\n수집 합계: {len(raw)}건 → 3일치 필터 후: {len(articles)}건")

result = {
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "count": len(articles),
    "articles": articles,
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"완료: {len(articles)}건 → news.json")
