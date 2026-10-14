"""
Reddit scraper for r/hyderabad — searches for Manikonda/Neknampur civic posts.

Setup (free):
  1. Go to https://www.reddit.com/prefs/apps
  2. Create app → script type → get client_id + client_secret
  3. Add to .streamlit/secrets.toml:
       [reddit]
       client_id     = "..."
       client_secret = "..."
       user_agent    = "ConstituencyBot/1.0"

Falls back gracefully if credentials are missing.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.data_ingestion import classify_sentiment
from modules.scrapers.news_sites import _extract_location, _extract_category, \
    _extract_families, AGENCY_MAP
from datetime import datetime

SUBREDDITS = ["hyderabad", "india", "Hyderabad"]
SEARCH_TERMS = [
    "Manikonda", "Neknampur", "Puppalguda",
    "Lanco Hills", "Manikonda water", "Neknampur drainage",
]


def _get_praw():
    try:
        import praw
        import streamlit as st
        secrets = st.secrets.get("reddit", {})
        if not secrets.get("client_id"):
            return None
        return praw.Reddit(
            client_id=secrets["client_id"],
            client_secret=secrets["client_secret"],
            user_agent=secrets.get("user_agent", "ConstituencyBot/1.0"),
        )
    except Exception:
        return None


def scrape_reddit() -> tuple[list[dict], list[dict]]:
    """Returns (news_articles, grievances). Empty lists if credentials missing."""
    reddit = _get_praw()
    if not reddit:
        return [], []

    news, grievances = [], []
    seen = set()

    for term in SEARCH_TERMS:
        try:
            for sub_name in SUBREDDITS:
                sub = reddit.subreddit(sub_name)
                for post in sub.search(term, sort="new", limit=10, time_filter="year"):
                    if post.id in seen or not post.selftext:
                        continue
                    seen.add(post.id)
                    full_text = f"{post.title} {post.selftext}"
                    lower = full_text.lower()

                    if "manikonda" not in lower and "neknampur" not in lower \
                       and "puppalguda" not in lower:
                        continue

                    pub_date = datetime.fromtimestamp(post.created_utc).strftime("%Y-%m-%d")
                    days_pending = (datetime.today() - datetime.fromtimestamp(post.created_utc)).days
                    location, lat, lon = _extract_location(full_text)
                    category = _extract_category(full_text)
                    sentiment = classify_sentiment(full_text)

                    news.append({
                        "title":     post.title,
                        "source":    f"Reddit r/{sub_name}",
                        "url":       f"https://reddit.com{post.permalink}",
                        "published": pub_date,
                        "keyword":   term,
                        "sentiment": sentiment,
                        "summary":   post.selftext[:250],
                    })
                    grievances.append({
                        "location":          location,
                        "lat":               lat,
                        "lon":               lon,
                        "category":          category,
                        "description":       (post.selftext or post.title)[:300],
                        "reported_date":     pub_date,
                        "families_affected": _extract_families(full_text),
                        "agency":            AGENCY_MAP.get(category, "GHMC"),
                        "source_url":        f"https://reddit.com{post.permalink}",
                        "source_type":       "reddit",
                        "days_pending":      days_pending,
                        "era":               "BRS Era (Pre-2023)" if days_pending > 365
                                             else "Congress Era (2024–Present)",
                    })
        except Exception:
            continue

    return news, grievances
