"""
Data Ingestion Layer
- Async news / social media scraper (httpx + BeautifulSoup)
- TextBlob sentiment classifier with constituency-specific lexicon
- Falls back to mock headlines when network is unavailable
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
from textblob import TextBlob
import pandas as pd
from datetime import datetime
from typing import List, Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    SEARCH_KEYWORDS,
    SENTIMENT_ANGRY, SENTIMENT_NEUTRAL, SENTIMENT_HOPEFUL,
)

# ── Constituency-specific sentiment lexicon overrides ────────────────────────
# Words that carry strong local political sentiment not captured by TextBlob
_POSITIVE_BOOST  = {"prajavani", "resolved", "inaugurated", "camp", "hopeful", "progress"}
_NEGATIVE_BOOST  = {"encroachment", "flooding", "pending", "ignored", "delayed",
                     "crisis", "overload", "contamination", "unresolved", "abandoned"}


def classify_sentiment(text: str) -> str:
    """
    Three-class sentiment specific to Congress administration promises.
    Uses TextBlob polarity + local lexicon override.
    """
    lower = text.lower()

    # Lexicon boost — constituency-specific terms dominate generic polarity
    neg_hits = sum(1 for w in _NEGATIVE_BOOST if w in lower)
    pos_hits = sum(1 for w in _POSITIVE_BOOST if w in lower)

    if neg_hits > pos_hits:
        return SENTIMENT_ANGRY
    if pos_hits > neg_hits:
        return SENTIMENT_HOPEFUL

    # Fall back to TextBlob polarity
    polarity = TextBlob(text).sentiment.polarity
    if polarity < -0.1:
        return SENTIMENT_ANGRY
    elif polarity > 0.1:
        return SENTIMENT_HOPEFUL
    return SENTIMENT_NEUTRAL


# ── Async news scraper ────────────────────────────────────────────────────────

_MOCK_HEADLINES = [
    {
        "title":   "Manikonda residents demand action on water crisis ahead of summer",
        "source":  "Telangana Today",
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "url":     "#",
        "keyword": "Manikonda water crisis",
    },
    {
        "title":   "Neknampur lake encroachment: Survey ordered, locals await action",
        "source":  "The Hans India",
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "url":     "#",
        "keyword": "Neknampur lake encroachment",
    },
    {
        "title":   "Prajavani petitions pile up: 1,200 pending in Manikonda alone",
        "source":  "Deccan Chronicle",
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "url":     "#",
        "keyword": "Prajavani pending Manikonda",
    },
    {
        "title":   "Lanco Hills flyover: 3 years on, commuters still stuck in gridlock",
        "source":  "Times of India",
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "url":     "#",
        "keyword": "Lanco Hills traffic",
    },
    {
        "title":   "Puppalguda power crisis: Transformer upgrade finally sanctioned",
        "source":  "Telangana Today",
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "url":     "#",
        "keyword": "Puppalguda power cut",
    },
    {
        "title":   "Monsoon fear: Neknampur nala capacity reduced by illegal construction",
        "source":  "The Hindu",
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "url":     "#",
        "keyword": "Neknampur drainage flooding",
    },
]


async def _fetch_google_news(keyword: str, client: httpx.AsyncClient) -> List[Dict]:
    """
    Scrape Google News RSS for a keyword.
    Returns list of {title, source, date, url, keyword} dicts.
    """
    url = f"https://news.google.com/rss/search?q={keyword.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
    results = []
    try:
        resp = await client.get(url, timeout=10.0)
        soup = BeautifulSoup(resp.text, "xml")
        for item in soup.find_all("item")[:3]:
            results.append({
                "title":   item.title.text if item.title else "",
                "source":  item.source.text if item.source else "Unknown",
                "date":    item.pubDate.text[:10] if item.pubDate else "",
                "url":     item.link.text if item.link else "#",
                "keyword": keyword,
            })
    except Exception:
        pass  # Network unavailable — caller uses mock fallback
    return results


async def fetch_all_news(keywords: List[str] = None) -> pd.DataFrame:
    """
    Async-gather news for all keywords concurrently.
    Falls back to mock headlines if network is unavailable.
    """
    if keywords is None:
        keywords = SEARCH_KEYWORDS

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_fetch_google_news(kw, client) for kw in keywords]
        results_nested = await asyncio.gather(*tasks)

    articles = [art for batch in results_nested for art in batch]

    if not articles:
        articles = _MOCK_HEADLINES  # Graceful degradation

    df = pd.DataFrame(articles)
    df["sentiment"] = df["title"].apply(classify_sentiment)
    return df


def fetch_news_sync(keywords: List[str] = None) -> pd.DataFrame:
    """Sync wrapper — call from Streamlit (runs its own event loop)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Streamlit is already running an event loop; use thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, fetch_all_news(keywords))
                return future.result(timeout=30)
        return loop.run_until_complete(fetch_all_news(keywords))
    except Exception:
        # Absolute fallback to mock data
        df = pd.DataFrame(_MOCK_HEADLINES)
        df["sentiment"] = df["title"].apply(classify_sentiment)
        return df


def sentiment_summary(df: pd.DataFrame) -> Dict[str, int]:
    counts = df["sentiment"].value_counts().to_dict()
    return {
        SENTIMENT_ANGRY:   counts.get(SENTIMENT_ANGRY, 0),
        SENTIMENT_NEUTRAL: counts.get(SENTIMENT_NEUTRAL, 0),
        SENTIMENT_HOPEFUL: counts.get(SENTIMENT_HOPEFUL, 0),
    }
