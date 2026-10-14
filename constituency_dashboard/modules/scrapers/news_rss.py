"""
Google News RSS scraper — confirmed working for Manikonda/Neknampur keywords.
Returns structured article dicts with sentiment classification.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser
from textblob import TextBlob
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.data_ingestion import classify_sentiment

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ConstituencyBot/1.0)"
}

RSS_KEYWORDS = [
    "Manikonda water crisis",
    "Neknampur lake encroachment",
    "Manikonda drainage flooding",
    "Manikonda GHMC complaint",
    "Puppalguda power cut",
    "Lanco Hills traffic Manikonda",
    "Neknampur civic issues",
    "Manikonda sewage",
    "Manikonda residents complaint",
    "Neknampur water shortage",
    "Manikonda road pothole",
    "Prajavani Rangareddy",
]


def _rss_url(keyword: str) -> str:
    q = keyword.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"


def _parse_feed(keyword: str, timeout: int = 15) -> list[dict]:
    url = _rss_url(keyword)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        articles = []
        for item in soup.find_all("item")[:5]:
            title   = item.find("title").text.strip() if item.find("title") else ""
            link    = item.find("link").text.strip() if item.find("link") else ""
            pub     = item.find("pubDate")
            source  = item.find("source")
            desc    = item.find("description")

            pub_str = ""
            if pub:
                try:
                    pub_str = dateparser.parse(pub.text).strftime("%Y-%m-%d")
                except Exception:
                    pub_str = pub.text[:10]

            summary = ""
            if desc:
                raw = BeautifulSoup(desc.text, "html.parser").get_text()
                summary = raw[:300].strip()

            full_text = f"{title}. {summary}"
            articles.append({
                "title":     title,
                "source":    source.text.strip() if source else "Google News",
                "url":       link,
                "published": pub_str,
                "keyword":   keyword,
                "sentiment": classify_sentiment(full_text),
                "summary":   summary,
            })
        return articles
    except Exception as e:
        return []


def scrape_all(keywords: list[str] = None) -> list[dict]:
    """Scrape all keywords and return deduplicated article list."""
    if keywords is None:
        keywords = RSS_KEYWORDS
    seen_urls = set()
    results = []
    for kw in keywords:
        for art in _parse_feed(kw):
            if art["url"] not in seen_urls and art["title"]:
                seen_urls.add(art["url"])
                results.append(art)
    return results
