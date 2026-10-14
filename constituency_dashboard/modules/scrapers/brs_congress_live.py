"""
Live BRS-vs-Congress accountability scraper.

Pulls news articles via Google News RSS using two keyword sets:
  • BRS-era failures: abandoned projects, KCR-era complaints, stalled work
  • Congress-era actions: new initiatives, Revanth-era announcements, Prajavani

Each article is classified into an "era bucket" and returned as a record the
dashboard can display alongside the curated seed list.

This is best-effort — Google News surfaces recent coverage, so older BRS
failures (2014–23) may not appear unless they're re-reported now. Combine
with the curated mock_data.py seed for a fuller picture.
"""

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.data_ingestion import classify_sentiment

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ConstituencyBot/1.0)"}

BRS_QUERIES = [
    "BRS abandoned project Rangareddy",
    "KCR era stalled Manikonda",
    "BRS unfinished Telangana infrastructure",
    "Manikonda lake encroachment BRS",
    "Neknampur lake polluted KCR government",
    "Puppalguda road BRS incomplete",
    "BRS Rangareddy water shortage",
]

CONGRESS_QUERIES = [
    "Revanth Reddy Manikonda",
    "Congress Telangana Prajavani Rangareddy",
    "Congress government Manikonda water",
    "Revanth Reddy GHMC reforms",
    "Telangana Congress lake restoration",
    "Congress Rangareddy drainage project",
    "Prajavani Manikonda grievance",
]


def _rss(q: str) -> str:
    return f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"


def _parse(q: str, era: str, timeout: int = 12) -> list:
    try:
        r = requests.get(_rss(q), headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        out = []
        for item in soup.find_all("item")[:4]:
            title = item.find("title").text.strip() if item.find("title") else ""
            link  = item.find("link").text.strip() if item.find("link") else ""
            pub   = item.find("pubDate")
            src   = item.find("source")
            desc  = item.find("description")

            pub_str = ""
            if pub:
                try:
                    pub_str = dateparser.parse(pub.text).strftime("%Y-%m-%d")
                except Exception:
                    pub_str = pub.text[:10]

            summary = ""
            if desc:
                summary = BeautifulSoup(desc.text, "html.parser").get_text()[:300].strip()

            out.append({
                "title":     title,
                "source":    (src.text.strip() if src else "Google News") + f" · {era}",
                "url":       link,
                "published": pub_str,
                "keyword":   f"{era}: {q}",
                "sentiment": classify_sentiment(title + ". " + summary),
                "summary":   summary,
                "era":       era,
            })
        return out
    except Exception:
        return []


def scrape_brs_congress() -> tuple:
    """Return (brs_items, congress_items) — live news for the accountability page."""
    brs = []
    seen = set()
    for q in BRS_QUERIES:
        for art in _parse(q, "BRS Era"):
            if art["url"] and art["url"] not in seen and art["title"]:
                seen.add(art["url"])
                brs.append(art)

    cong = []
    for q in CONGRESS_QUERIES:
        for art in _parse(q, "Congress Era"):
            if art["url"] and art["url"] not in seen and art["title"]:
                seen.add(art["url"])
                cong.append(art)

    return brs, cong
