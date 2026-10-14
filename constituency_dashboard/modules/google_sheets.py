"""
Google Sheets sync module.

Reads form responses from a connected Google Sheet and converts them
into grievance records for the dashboard.

Setup (one-time, 5 minutes):
  1. Follow FORM_SETUP guide — run the Apps Script to create the form
  2. Share the Sheet with your service account email
  3. Add credentials to .streamlit/secrets.toml:

     [google]
     sheet_id          = "your_sheet_id_here"
     service_account   = '''{ ...paste service account JSON here... }'''

  OR use a simpler API key approach for public sheets:
     [google]
     sheet_id          = "your_sheet_id_here"
     api_key           = "your_api_key_here"
"""

import json
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.form_config import CPGRAMS_CATEGORIES, AGENCY_MAP


# ── Column mapping — Google Form response sheet → grievance fields ─────────────
# Keys = exact Google Form question titles (set by Apps Script)
COLUMN_MAP = {
    "Timestamp":                   "scraped_at",
    "Reporter Name":               "_reporter_name",
    "Reporter Phone":              "_reporter_phone",
    "Location":                    "location",
    "Custom Location":             "_custom_location",
    "Ward Number":                 "_ward",
    "Grievance Category (CPGRAMS)":"_category_code",
    "Civic Sub-category":          "_civic_sub",
    "Issue Description":           "description",
    "Families Affected":           "families_affected",
    "Urgency Level":               "_urgency",
    "Photo / Evidence Link":       "source_url",
}


def _available():
    """Return True if gspread + credentials are configured."""
    try:
        import streamlit as st
        return bool(st.secrets.get("google", {}).get("sheet_id"))
    except Exception:
        return False


def _get_sheet_data_via_api(sheet_id: str, api_key: str) -> pd.DataFrame:
    """Public sheet read via Sheets REST API — no service account needed."""
    import requests
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        f"/values/A1:Z2000?key={api_key}"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    rows = data.get("values", [])
    if len(rows) < 2:
        return pd.DataFrame()
    headers = rows[0]
    return pd.DataFrame(rows[1:], columns=headers)


def _get_sheet_data_via_gspread(sheet_id: str, sa_json: str) -> pd.DataFrame:
    """Private sheet read via gspread + service account."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(
        json.loads(sa_json),
        scopes=["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).sheet1
    return pd.DataFrame(ws.get_all_records())


def fetch_sheet_responses() -> pd.DataFrame:
    """Fetch raw form responses from Google Sheets. Returns empty DF if not configured."""
    try:
        import streamlit as st
        cfg = st.secrets.get("google", {})
        sheet_id = cfg.get("sheet_id", "")
        if not sheet_id:
            return pd.DataFrame()

        api_key  = cfg.get("api_key", "")
        sa_json  = cfg.get("service_account", "")

        if api_key:
            return _get_sheet_data_via_api(sheet_id, api_key)
        elif sa_json:
            return _get_sheet_data_via_gspread(sheet_id, sa_json)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def transform_responses(raw_df: pd.DataFrame) -> list[dict]:
    """Convert Google Form responses into grievance dicts for DB insert."""
    if raw_df.empty:
        return []

    grievances = []
    cat_label_to_code = {v: k for k, v in CPGRAMS_CATEGORIES.items()}

    for _, row in raw_df.iterrows():
        try:
            # Location
            location = str(row.get("Location", "Manikonda")).strip()
            if "Other" in location:
                location = str(row.get("Custom Location", "Manikonda")).strip() or "Manikonda"

            # Category
            cat_label = str(row.get("Grievance Category (CPGRAMS)", "")).strip()
            cat_code  = cat_label_to_code.get(cat_label, "002")
            civic_sub = str(row.get("Civic Sub-category", "")).strip()
            category  = civic_sub if civic_sub and cat_code == "002" else cat_label

            # Description
            desc = str(row.get("Issue Description", "")).strip()
            if civic_sub and civic_sub not in desc:
                desc = f"[{civic_sub}] {desc}"

            # Families affected
            fam = 0
            try:
                fam = int(str(row.get("Families Affected", "0")).strip() or "0")
            except Exception:
                pass

            # Date
            ts = str(row.get("Timestamp", "")).strip()
            try:
                reported_date = datetime.strptime(ts, "%m/%d/%Y %H:%M:%S").strftime("%Y-%m-%d")
            except Exception:
                reported_date = datetime.today().strftime("%Y-%m-%d")

            days_pending = (datetime.today() - datetime.strptime(reported_date, "%Y-%m-%d")).days

            # Urgency → escalation tier
            urgency = str(row.get("Urgency Level", "")).lower()
            tier = "CRITICAL" if "critical" in urgency else \
                   "POLITICAL" if "high" in urgency else \
                   "URGENT"   if "medium" in urgency else "MONITOR"

            grievances.append({
                "location":          location,
                "lat":               _location_coords(location)[0],
                "lon":               _location_coords(location)[1],
                "category":          category or cat_label,
                "description":       desc[:500],
                "reported_date":     reported_date,
                "status":            "Pending",
                "era":               "Congress Era (2024–Present)",
                "families_affected": fam,
                "petition_no":       f"FIELD-{reported_date[:7].replace('-','')}-{abs(hash(desc))%9999:04d}",
                "agency":            AGENCY_MAP.get(cat_code, "GHMC"),
                "source_url":        str(row.get("Photo / Evidence Link", "")),
                "source_type":       "google_form",
                "days_pending":      days_pending,
                "escalation_tier":   tier,
                "opportunity_score": _score(days_pending, fam, tier),
            })
        except Exception:
            continue
    return grievances


def _location_coords(location: str) -> tuple:
    COORDS = {
        "Manikonda Village":   (17.4071, 78.3765),
        "Neknampur":           (17.4123, 78.3689),
        "Puppalguda":          (17.3934, 78.3798),
        "Lanco Hills":         (17.4089, 78.3812),
        "Khajaguda":           (17.3985, 78.3841),
        "Nallagandla":         (17.4245, 78.3456),
        "Raj Bhavan Colony":   (17.4102, 78.3829),
        "Alkapur Township":    (17.4050, 78.3720),
        "Fairfield Colony":    (17.4090, 78.3700),
        "Lakshmi Nagar Colony":(17.4060, 78.3755),
        "YSR Colony":          (17.4010, 78.3780),
        "Byouth Colony":       (17.4030, 78.3800),
        "Pioneer Estate":      (17.4080, 78.3720),
        "EVV Colony":          (17.4100, 78.3690),
        "EIPL Tamarind":       (17.4115, 78.3672),
        "Manikonda Basti":     (17.4055, 78.3740),
        "Neknampur Layout":    (17.4138, 78.3701),
    }
    return COORDS.get(location, (17.4065, 78.3772))


def _score(days: int, families: int, tier: str) -> float:
    age  = min(days / 100, 1.0) * 50
    fam  = min(families / 300, 1.0) * 30
    bonus= {"CRITICAL": 20, "POLITICAL": 15, "URGENT": 10}.get(tier, 0)
    return round(age + fam + bonus, 1)
