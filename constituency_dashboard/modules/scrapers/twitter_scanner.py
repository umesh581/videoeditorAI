"""
X / Twitter scanner for Manikonda–Neknampur civic accounts.

X's public API now requires paid access, so we use Nitter (open-source X mirror)
RSS feeds. Nitter instances rotate, so we try multiple mirrors with fallback.
If all fail, we degrade gracefully and return an empty list (the scheduler
logs the error and other sources keep working).
"""

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.data_ingestion import classify_sentiment

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ConstituencyBot/1.0)"}

# Known Manikonda / Neknampur related handles
HANDLES = [
    "JITHUINC",          # Jithender Merugu — the candidate
    "ManaManikonda",
    "ManikondaMc",
    "MMRWA4",
    "CongressManiko1",
    "shrikantkovela",
    "Hyderabadrains",
    "ManikondaM88292",
    "INCTelangana",      # State Congress — for talking-point alignment
    "revanth_anumula",   # CM Revanth Reddy
]

# Subset of handles whose tweets count as "the candidate's own voice"
CANDIDATE_HANDLES = ["JITHUINC"]

NITTER_MIRRORS = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
]

# Keywords used to filter generic tweets down to civic-relevant ones
CIVIC_KEYWORDS = [
    "water", "drainage", "pothole", "garbage", "sewage", "encroach",
    "power cut", "street light", "road", "GHMC", "HMWSSB", "lake",
    "Manikonda", "Neknampur", "Puppalguda", "Rajendranagar", "Lanco",
    "Khajaguda", "Nallagandla",
]


def _fetch_handle(handle: str, timeout: int = 10) -> list:
    """Try each Nitter mirror until one returns RSS for this handle."""
    for base in NITTER_MIRRORS:
        url = f"{base}/{handle}/rss"
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code != 200 or "<item" not in r.text:
                continue
            soup = BeautifulSoup(r.content, "xml")
            tweets = []
            for item in soup.find_all("item")[:10]:
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

                full = (title + " " + summary).lower()
                # Keep ALL tweets from the candidate's own handle (for style analysis);
                # filter other handles down to civic-only.
                if handle not in CANDIDATE_HANDLES:
                    if not any(kw.lower() in full for kw in CIVIC_KEYWORDS):
                        continue

                tweets.append({
                    "title":     title[:200],
                    "source":    f"X/@{handle}",
                    "url":       link,
                    "published": pub_str,
                    "keyword":   f"@{handle}",
                    "sentiment": classify_sentiment(title + ". " + summary),
                    "summary":   summary,
                })
            return tweets
        except Exception:
            continue
    return []


def scrape_twitter() -> list:
    """Scan all configured handles. Returns deduplicated tweet list."""
    seen = set()
    results = []
    for h in HANDLES:
        for tw in _fetch_handle(h):
            if tw["url"] and tw["url"] not in seen:
                seen.add(tw["url"])
                results.append(tw)
    return results
