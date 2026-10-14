"""
Telugu newspaper scrapers — Namaste Telangana, Eenadu, V6 Velugu.
Strategy: use Google News RSS with Telugu source filters, since direct
site scraping is blocked or content is in non-HTML formats (e-paper PDFs).

This gives ground-level Rangareddy / Rajendranagar coverage in Telugu that
the English Google News RSS misses.
"""

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.data_ingestion import classify_sentiment

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ConstituencyBot/1.0)"}

# Google News query: keyword + site filter, in Telugu locale
TELUGU_SOURCES = [
    ("Namaste Telangana", "ntnews.com"),
    ("Eenadu",            "eenadu.net"),
    ("V6 Velugu",         "v6velugu.com"),
    ("Sakshi",            "sakshi.com"),
    ("Andhra Jyothy",     "andhrajyothy.com"),
]

# Keywords mix Telugu transliteration + English place names
KEYWORDS = [
    "Manikonda",
    "Neknampur",
    "Puppalguda",
    "Rajendranagar",
    "Rangareddy civic",
    "మణికొండ",          # Manikonda in Telugu
    "నెక్నాంపూర్",        # Neknampur in Telugu
    "రాజేంద్రనగర్",       # Rajendranagar in Telugu
]


def _rss_url(keyword: str, site: str) -> str:
    q = f'"{keyword}" site:{site}'.replace(" ", "+").replace('"', "%22")
    return f"https://news.google.com/rss/search?q={q}&hl=te&gl=IN&ceid=IN:te"


def _parse_feed(keyword: str, source_name: str, site: str, timeout: int = 12) -> list:
    url = _rss_url(keyword, site)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        articles = []
        for item in soup.find_all("item")[:5]:
            title = item.find("title").text.strip() if item.find("title") else ""
            link  = item.find("link").text.strip() if item.find("link") else ""
            pub   = item.find("pubDate")
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

            articles.append({
                "title":     title,
                "source":    f"{source_name} (Telugu)",
                "url":       link,
                "published": pub_str,
                "keyword":   keyword,
                "sentiment": classify_sentiment(title + ". " + summary),
                "summary":   summary,
            })
        return articles
    except Exception:
        return []


def scrape_telugu_news() -> list:
    """Scrape all Telugu newspaper coverage for the constituency."""
    seen = set()
    results = []
    for source_name, site in TELUGU_SOURCES:
        for kw in KEYWORDS:
            for art in _parse_feed(kw, source_name, site):
                if art["url"] and art["url"] not in seen and art["title"]:
                    seen.add(art["url"])
                    results.append(art)
    return results
