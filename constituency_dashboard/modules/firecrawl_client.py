"""
Firecrawl API wrapper — handles JS-rendered news sites + the X profile.

Why Firecrawl:
  • /search returns scraped content WITH source URLs (always citable)
  • Bypasses anti-bot on Telugu papers, Telangana Today, Siasat
  • Renders JavaScript, so X/Nitter-equivalents work

Setup:
  Add to .streamlit/secrets.toml:
    [firecrawl]
    api_key = "fc-xxxxxxxxxxxxxxxxxxxxxxxx"

Free tier: 500 credits/mo · paid: $19/mo for 3000 credits.
Each /search call ≈ 1 credit, each /scrape ≈ 1 credit.
"""

import requests
import logging

log = logging.getLogger(__name__)

BASE = "https://api.firecrawl.dev/v1"


def _key():
    try:
        import streamlit as st
        return st.secrets.get("firecrawl", {}).get("api_key", "")
    except Exception:
        import os
        return os.environ.get("FIRECRAWL_API_KEY", "")


def is_available() -> bool:
    return bool(_key())


def search(query: str, limit: int = 10, timeout: int = 60) -> list:
    """
    Web search → returns scraped results with title, url, markdown.
    Always returns a list (empty if unavailable / errored).
    """
    key = _key()
    if not key:
        return []
    try:
        r = requests.post(
            f"{BASE}/search",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "query": query,
                "limit": limit,
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
            },
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", []) or []
    except Exception as e:
        log.error(f"[Firecrawl/search] {query!r}: {e}")
        return []


def scrape(url: str, timeout: int = 60) -> dict:
    """Scrape a single URL → returns {'title', 'markdown', 'url'} or {}."""
    key = _key()
    if not key:
        return {}
    try:
        r = requests.post(
            f"{BASE}/scrape",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True,
            },
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        return {
            "title":    data.get("metadata", {}).get("title", ""),
            "url":      data.get("metadata", {}).get("sourceURL", url),
            "markdown": data.get("markdown", ""),
            "published": data.get("metadata", {}).get("publishedTime", ""),
        }
    except Exception as e:
        log.error(f"[Firecrawl/scrape] {url}: {e}")
        return {}
