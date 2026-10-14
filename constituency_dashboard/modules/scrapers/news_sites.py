"""
Direct scraper for Hyderabad news sites confirmed to cover Manikonda/Neknampur:
  - hyderabadmail.com
  - telanganatoday.com
  - siasat.com
  - thehansindia.com
  - newsmeter.in

Extracts articles and converts them into grievance-compatible records
by matching location + issue-type keywords in the text.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.data_ingestion import classify_sentiment

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ConstituencyBot/1.0)"}
TIMEOUT = 20

# ── Known locations with coordinates ─────────────────────────────────────────
LOCATION_MAP = {
    "manikonda":          (17.4071, 78.3765),
    "neknampur":          (17.4123, 78.3689),
    "lanco hills":        (17.4089, 78.3812),
    "puppalguda":         (17.3934, 78.3798),
    "khajaguda":          (17.3985, 78.3841),
    "nallagandla":        (17.4245, 78.3456),
    "raj bhavan colony":  (17.4102, 78.3829),
    "alkapur":            (17.4050, 78.3720),
    "eipl tamarind":      (17.4115, 78.3672),
    "fairfield colony":   (17.4090, 78.3700),
    "lakshmi nagar":      (17.4060, 78.3755),
    "ysr colony":         (17.4010, 78.3780),
    "byouth colony":      (17.4030, 78.3800),
    "pioneer estate":     (17.4080, 78.3720),
}

# Issue-type keyword → category
ISSUE_MAP = {
    r"water (supply|crisis|shortage|scarcity|pipeline|tanker)": "Water Supply",
    r"drain(age|age system|age line|flooding|flood)":           "Drainage & Flooding",
    r"flood(ing|ed|s)?":                                        "Drainage & Flooding",
    r"(road|pothole|pavement|footpath|street)":                 "Roads & Traffic",
    r"(power|electricity|transformer|load.?shed|outage|cut)":   "Power / Electricity",
    r"(lake|nala|encroach|ftl|buffer zone)":                    "Lake Encroachment",
    r"(garbage|waste|sanit|sweeping|dump)":                     "Sanitation",
    r"(prajavani|petition|complaint|grievance)":                "Prajavani Petition",
    r"(layout|open space|land grab|encroach)":                  "Land Encroachment",
}

AGENCY_MAP = {
    "Water Supply":       "HMWSSB",
    "Drainage & Flooding":"GHMC",
    "Roads & Traffic":    "GHMC / NHAI",
    "Power / Electricity":"TSSPDCL",
    "Lake Encroachment":  "HMDA / Revenue",
    "Sanitation":         "GHMC",
    "Prajavani Petition": "District Collector",
    "Land Encroachment":  "Revenue / HMDA",
}

SITE_CONFIGS = [
    {
        "name":    "Hyderabad Mail",
        "urls":    [
            "https://hyderabadmail.com/?s=manikonda",
            "https://hyderabadmail.com/?s=neknampur",
        ],
        "article_sel": "article",
        "title_sel":   "h2.entry-title a, h1.entry-title",
        "date_sel":    "time.entry-date",
        "body_sel":    "div.entry-content",
        "link_attr":   "href",
    },
    {
        "name":    "Telangana Today",
        "urls":    [
            "https://telanganatoday.com/?s=manikonda",
            "https://telanganatoday.com/?s=neknampur",
        ],
        "article_sel": "article",
        "title_sel":   "h2.entry-title a, h3.entry-title a",
        "date_sel":    "time",
        "body_sel":    "div.entry-content",
        "link_attr":   "href",
    },
    {
        "name":    "The Siasat Daily",
        "urls":    [
            "https://www.siasat.com/?s=manikonda+water",
            "https://www.siasat.com/?s=neknampur",
        ],
        "article_sel": "article",
        "title_sel":   "h2.post-title a, h3.post-title a",
        "date_sel":    "span.date",
        "body_sel":    "div.post-content",
        "link_attr":   "href",
    },
]


def _extract_location(text: str) -> tuple[str, float, float]:
    lower = text.lower()
    for name, (lat, lon) in LOCATION_MAP.items():
        if name in lower:
            return name.title(), lat, lon
    return "Manikonda", 17.4071, 78.3765


def _extract_category(text: str) -> str:
    lower = text.lower()
    for pattern, category in ISSUE_MAP.items():
        if re.search(pattern, lower):
            return category
    return "Prajavani Petition"


def _extract_families(text: str) -> int:
    patterns = [
        r"(\d+)\s*(families|households|residents|homes)",
        r"(\d+)\s*people",
        r"(\d+)\s*flats",
    ]
    for p in patterns:
        m = re.search(p, text.lower())
        if m:
            n = int(m.group(1))
            if n < 10000:
                return n
    return 0


def _parse_date(date_str: str) -> str:
    try:
        return dateparser.parse(date_str).strftime("%Y-%m-%d")
    except Exception:
        return datetime.today().strftime("%Y-%m-%d")


def _scrape_site(cfg: dict) -> list[dict]:
    articles = []
    for url in cfg["urls"]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            soup = BeautifulSoup(resp.content, "html.parser")
            for art in soup.select(cfg["article_sel"])[:8]:
                title_el = art.select_one(cfg["title_sel"])
                date_el  = art.select_one(cfg["date_sel"])
                body_el  = art.select_one(cfg["body_sel"])

                if not title_el:
                    continue

                title    = title_el.get_text(strip=True)
                link     = title_el.get("href", url) if title_el.name == "a" else \
                           (title_el.find("a") or {}).get("href", url)
                date_str = date_el.get("datetime", date_el.get_text()) if date_el else ""
                body_txt = body_el.get_text(" ", strip=True)[:600] if body_el else ""
                full_txt = f"{title} {body_txt}"

                # Only keep constituency-relevant articles
                lower = full_txt.lower()
                if not any(loc in lower for loc in LOCATION_MAP):
                    continue

                location, lat, lon = _extract_location(full_txt)
                category = _extract_category(full_txt)
                pub_date = _parse_date(date_str) if date_str else datetime.today().strftime("%Y-%m-%d")
                days_pending = (datetime.today() - dateparser.parse(pub_date)).days

                articles.append({
                    "title":            title,
                    "source":           cfg["name"],
                    "url":              str(link),
                    "published":        pub_date,
                    "keyword":          f"{location} — {category}",
                    "sentiment":        classify_sentiment(full_txt),
                    "summary":          body_txt[:200],
                    # grievance fields
                    "location":         location,
                    "lat":              lat,
                    "lon":              lon,
                    "category":         category,
                    "description":      body_txt[:250] or title,
                    "reported_date":    pub_date,
                    "families_affected":_extract_families(full_txt),
                    "agency":           AGENCY_MAP.get(category, "GHMC"),
                    "source_url":       str(link),
                    "source_type":      "scraped_news",
                    "days_pending":     days_pending,
                    "era":              "BRS Era (Pre-2023)" if days_pending > 365 else "Congress Era (2024–Present)",
                })
        except Exception:
            continue
    return articles


def scrape_all_sites() -> tuple[list[dict], list[dict]]:
    """Returns (news_articles, grievances) — both lists ready for DB insert."""
    all_news = []
    all_grievances = []
    seen_titles = set()

    for cfg in SITE_CONFIGS:
        for item in _scrape_site(cfg):
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                all_news.append({k: item[k] for k in
                    ["title","source","url","published","keyword","sentiment","summary"]})
                all_grievances.append({k: item[k] for k in
                    ["location","lat","lon","category","description","reported_date",
                     "families_affected","agency","source_url","source_type",
                     "days_pending","era"]})

    return all_news, all_grievances
