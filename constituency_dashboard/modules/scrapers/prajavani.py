"""
Prajavani Portal scraper — telangana.gov.in grievance system.

The portal uses a session-based form. This scraper:
  1. Fetches the public search page
  2. Submits a district/mandal filter form
  3. Extracts pending petition records

Falls back gracefully if the portal blocks or changes structure.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.scrapers.news_sites import _extract_location, _extract_category, AGENCY_MAP

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

BASE_URLS = [
    "https://prajavani.telangana.gov.in",
    "https://grievances.telangana.gov.in",
]

MANDAL_KEYWORDS = ["manikonda", "neknampur", "rajendranagar", "rangareddy"]


def _try_portal(base_url: str, timeout: int = 25) -> list[dict]:
    """Attempt to scrape grievance listings from a portal URL."""
    grievances = []
    try:
        # Step 1: Get main page and extract form tokens
        session = requests.Session()
        resp = session.get(base_url, headers=HEADERS, timeout=timeout)
        soup = BeautifulSoup(resp.content, "html.parser")

        # Look for public search/status pages
        search_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(k in href for k in ["search", "status", "report", "pending", "public"]):
                full = href if href.startswith("http") else base_url + "/" + href.lstrip("/")
                search_links.append(full)

        # Step 2: Try each search page for tabular data
        for url in search_links[:5]:
            try:
                r2 = session.get(url, headers=HEADERS, timeout=timeout)
                s2 = BeautifulSoup(r2.content, "html.parser")
                rows = _extract_table_rows(s2, base_url)
                grievances.extend(rows)
                if rows:
                    break
            except Exception:
                continue

        # Step 3: If no table found, try direct form POST with mandal filter
        if not grievances:
            form = soup.find("form")
            if form:
                form_data = {
                    inp.get("name", ""): inp.get("value", "")
                    for inp in form.find_all("input")
                    if inp.get("name")
                }
                form_data.update({"district": "rangareddy", "mandal": "manikonda"})
                action = form.get("action", base_url)
                if not action.startswith("http"):
                    action = base_url + "/" + action.lstrip("/")
                r3 = session.post(action, data=form_data, headers=HEADERS, timeout=timeout)
                s3 = BeautifulSoup(r3.content, "html.parser")
                grievances.extend(_extract_table_rows(s3, base_url))

    except Exception:
        pass
    return grievances


def _extract_table_rows(soup: BeautifulSoup, source_url: str) -> list[dict]:
    """Extract grievance rows from any table on the page."""
    grievances = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not any(kw in " ".join(headers) for kw in
                   ["petition", "complaint", "grievance", "status", "subject", "date"]):
            continue

        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < 3:
                continue
            text = " ".join(cells)
            lower = text.lower()

            if not any(kw in lower for kw in MANDAL_KEYWORDS):
                continue

            location, lat, lon = _extract_location(text)
            category = _extract_category(text)

            # Try to extract petition number from first few cells
            petition_no = ""
            for cell in cells[:3]:
                if re.search(r"[A-Z]{2,}-?\d{4,}", cell):
                    petition_no = cell
                    break

            # Try to extract date
            reported_date = datetime.today().strftime("%Y-%m-%d")
            for cell in cells:
                m = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", cell)
                if m:
                    try:
                        reported_date = datetime.strptime(
                            m.group(), "%d/%m/%Y"
                        ).strftime("%Y-%m-%d")
                    except Exception:
                        pass
                    break

            days_pending = (datetime.today() - datetime.strptime(reported_date, "%Y-%m-%d")).days

            grievances.append({
                "location":          location,
                "lat":               lat,
                "lon":               lon,
                "category":          category,
                "description":       text[:300],
                "reported_date":     reported_date,
                "petition_no":       petition_no,
                "families_affected": 0,
                "agency":            AGENCY_MAP.get(category, "GHMC"),
                "source_url":        source_url,
                "source_type":       "prajavani_portal",
                "days_pending":      days_pending,
                "era":               "BRS Era (Pre-2023)" if days_pending > 365
                                     else "Congress Era (2024–Present)",
            })
    return grievances


def scrape_prajavani() -> list[dict]:
    """Try all known portal URLs. Returns grievance list (may be empty)."""
    for url in BASE_URLS:
        result = _try_portal(url)
        if result:
            return result
    return []
