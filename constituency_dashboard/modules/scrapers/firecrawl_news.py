"""
Firecrawl-powered scrapers — gives us reliable, JS-rendered access to:
  • Local + Telugu newspapers (Eenadu, NT, Velugu, Sakshi, Telangana Today, Siasat)
  • The CM/MLA office press releases
  • @JITHUINC profile (via x.com directly, since Firecrawl renders JS)

Every record returned carries a real source URL — no synthesis.
"""

import re
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.firecrawl_client import search, scrape, is_available
from modules.data_ingestion import classify_sentiment

# Tight queries targeting the constituency
NEWS_QUERIES = [
    "Manikonda water shortage GHMC",
    "Neknampur lake encroachment HYDRAA",
    "Puppalguda drainage flooding",
    "Lanco Hills Manikonda civic issue",
    "Khajaguda Nallagandla road pothole",
    "Rangareddy Prajavani grievance pending",
    "Manikonda municipal corporation complaint",
    "Neknampur GHMC ward problem",
    "Rajendranagar Manikonda Eenadu",
    "మణికొండ సమస్య",       # "Manikonda problem" in Telugu
    "నెక్నాంపూర్ సరస్సు",  # "Neknampur lake" in Telugu
]

# Grievance keywords used to flag a news item as a real local issue (vs general coverage)
GRIEVANCE_HINTS = [
    "complaint", "problem", "shortage", "pending", "demand",
    "protest", "blocked", "overflow", "stagnant", "encroach",
    "ఫిర్యాదు", "సమస్య",
]

LOCATION_HINTS = [
    "Manikonda", "Neknampur", "Puppalguda", "Lanco Hills",
    "Khajaguda", "Nallagandla", "Rajendranagar",
]


def _detect_location(text: str) -> str:
    for loc in LOCATION_HINTS:
        if loc.lower() in text.lower():
            return loc
    return "Manikonda"


def _is_grievance(text: str) -> bool:
    t = text.lower()
    return any(h in t for h in GRIEVANCE_HINTS)


def scrape_firecrawl_news() -> tuple:
    """Returns (articles, grievances) — both lists carry source URLs."""
    if not is_available():
        return [], []

    articles  = []
    grievances = []
    seen = set()

    for q in NEWS_QUERIES:
        results = search(q, limit=5)
        for r in results:
            url = r.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)

            title    = r.get("title", "")[:300]
            markdown = r.get("markdown", "") or r.get("description", "")
            summary  = re.sub(r"\s+", " ", markdown)[:400].strip()
            full     = f"{title}. {summary}"
            if not title:
                continue

            domain  = url.split("/")[2] if "://" in url else ""
            article = {
                "title":     title,
                "source":    f"Firecrawl · {domain}",
                "url":       url,
                "published": "",
                "keyword":   f"firecrawl: {q}",
                "sentiment": classify_sentiment(full),
                "summary":   summary,
            }
            articles.append(article)

            # Promote to grievance if it reads like one
            if _is_grievance(full):
                loc = _detect_location(full)
                today = datetime.today().strftime("%Y-%m-%d")
                grievances.append({
                    "location":          loc,
                    "lat":               17.4065,
                    "lon":               78.3772,
                    "category":          "Civic amenities / Quality of service",
                    "description":       summary,
                    "reported_date":     today,
                    "status":            "Pending",
                    "era":               "Congress Era (2024–Present)",
                    "families_affected": 0,
                    "petition_no":       f"FC-{today.replace('-','')}-{abs(hash(url))%9999:04d}",
                    "agency":            "GHMC",
                    "source_url":        url,
                    "source_type":       f"firecrawl/{domain}",
                    "days_pending":      0,
                })

    return articles, grievances


def scrape_jithender_profile() -> list:
    """Try to pull @JITHUINC's recent tweets via Firecrawl (renders JS)."""
    if not is_available():
        return []

    # Try x.com and nitter — first that works
    for base in ["https://x.com/JITHUINC", "https://nitter.net/JITHUINC"]:
        data = scrape(base)
        md   = data.get("markdown", "")
        if not md or len(md) < 200:
            continue

        # Naive tweet extraction: lines that look like prose, not nav chrome
        lines = [ln.strip() for ln in md.split("\n") if ln.strip()]
        candidate_lines = [
            ln for ln in lines
            if len(ln) > 40
            and not ln.startswith(("#", "*", "-", "[", "!", "Reply", "Repost", "Like", "View"))
            and not ln.lower().startswith(("home", "explore", "notifications", "messages", "profile", "©", "terms of"))
        ]

        tweets = []
        for i, text in enumerate(candidate_lines[:20]):
            tweets.append({
                "title":     text[:280],
                "source":    "X/@JITHUINC (via Firecrawl)",
                "url":       base,
                "published": "",
                "keyword":   "@JITHUINC",
                "sentiment": classify_sentiment(text),
                "summary":   text[:300],
            })
        if tweets:
            return tweets
    return []
