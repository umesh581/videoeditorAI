"""
Seed data layer — realistic Manikonda/Neknampur civic grievances.

In production, replace get_grievances() with a live DB query or
a CSV export from the Prajavani portal.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ERA_BRS, ERA_CONGRESS

_TODAY = datetime.today()


def _days_ago(n: int) -> str:
    return (_TODAY - timedelta(days=n)).strftime("%Y-%m-%d")


# ── Raw grievance records ────────────────────────────────────────────────────
_RAW_GRIEVANCES = [
    # id, location, lat, lon, category, description, reported, status, era, families, petition_no
    (1,  "Neknampur Village",    17.4123, 78.3689, "Lake Encroachment",
     "Neknampur lake boundary encroached by 3 acres; affecting 200 families' water recharge",
     _days_ago(87), "Pending", ERA_BRS, 200, "PV-2024-0041"),

    (2,  "Lanco Hills Road",     17.4089, 78.3812, "Roads & Traffic",
     "3-km stretch unpaved; peak-hour gridlock affecting ~1,200 commuters daily",
     _days_ago(73), "Pending", ERA_BRS, 400, "PV-2024-0083"),

    (3,  "Puppalguda Colony",    17.3934, 78.3798, "Power / Electricity",
     "Recurring 8–12 hr load-shedding; transformer overload flagged since 2022",
     _days_ago(48), "In Progress", ERA_CONGRESS, 120, "PV-2025-0012"),

    (4,  "Manikonda Village",    17.4071, 78.3765, "Water Supply",
     "Borewells dry June–Sep; HMWSSB tanker supply irregular (2–3 days gap)",
     _days_ago(62), "Pending", ERA_BRS, 310, "PV-2024-0099"),

    (5,  "Khajaguda X Roads",    17.3985, 78.3841, "Drainage & Flooding",
     "Storm-water drain blocked; 4 ft flooding last monsoon, 3 houses damaged",
     _days_ago(34), "Pending", ERA_CONGRESS, 85, "PV-2025-0034"),

    (6,  "Nallagandla Junction", 17.4245, 78.3456, "Roads & Traffic",
     "Median break missing; 2 accidents in 30 days. NHAI jurisdiction dispute ongoing",
     _days_ago(21), "Pending", ERA_CONGRESS, 0, "PV-2025-0051"),

    (7,  "Manikonda Basti",      17.4055, 78.3740, "Sanitation",
     "Garbage segregation halted; 3 bins overflowing for 9 days. GHMC ward complaint filed",
     _days_ago(9),  "Pending", ERA_CONGRESS, 65, "PV-2025-0072"),

    (8,  "Neknampur Layout",     17.4138, 78.3701, "Land Encroachment",
     "Govt layout open space encroached for parking lot construction; locals protest",
     _days_ago(55), "Pending", ERA_BRS, 140, "PV-2024-0115"),

    (9,  "Raj Bhavan Colony",    17.4102, 78.3829, "Water Supply",
     "Pipeline burst unrepaired 18 days; water logging + supply cut for 15 families",
     _days_ago(18), "In Progress", ERA_CONGRESS, 15, "PV-2025-0061"),

    (10, "Puppalguda Lake Rd",   17.3921, 78.3815, "Drainage & Flooding",
     "Nala encroachment reduced drain width; 2023 & 2024 floods on record",
     _days_ago(95), "Pending", ERA_BRS, 230, "PV-2024-0008"),

    (11, "Manikonda GHMC Ward",  17.4060, 78.3780, "Prajavani Petition",
     "Batch of 12 petitions — sewage, street lights, footpath — pending 45+ days",
     _days_ago(45), "Pending", ERA_CONGRESS, 180, "PV-2025-0003"),

    (12, "Neknampur Main Rd",    17.4115, 78.3672, "Roads & Traffic",
     "Pothole stretch 1.2 km; GHMC contractor marked complete but work not done",
     _days_ago(30), "Pending", ERA_CONGRESS, 95, "PV-2025-0039"),

    (13, "Lanco Hills Phase 2",  17.4078, 78.3833, "Power / Electricity",
     "Street lights non-functional for 22 nights; TSSPDCL complaint #44219 unacted",
     _days_ago(22), "Pending", ERA_CONGRESS, 0, "PV-2025-0055"),

    (14, "Manikonda Outer Ring",  17.4035, 78.3751, "Water Supply",
     "Fluoride contamination in borewells; HMWSSB lab report pending 3 months",
     _days_ago(91), "Pending", ERA_BRS, 270, "PV-2024-0022"),

    (15, "Puppalguda Ext.",      17.3910, 78.3805, "Power / Electricity",
     "48-hr power cuts reported by 15 families; substation fault since Tuesday",
     _days_ago(3),  "Pending", ERA_CONGRESS, 15, "PV-2025-0089"),
]

_COLUMNS = [
    "id", "location", "lat", "lon", "category",
    "description", "reported_date", "status", "era",
    "families_affected", "petition_no"
]


def get_grievances() -> pd.DataFrame:
    df = pd.DataFrame(_RAW_GRIEVANCES, columns=_COLUMNS)
    df["reported_date"] = pd.to_datetime(df["reported_date"])
    df["days_pending"] = (pd.Timestamp.today() - df["reported_date"]).dt.days
    df["agency"] = df["category"].map({
        "Water Supply":       "HMWSSB",
        "Lake Encroachment":  "HMDA / Revenue",
        "Drainage & Flooding":"GHMC",
        "Power / Electricity":"TSSPDCL",
        "Roads & Traffic":    "GHMC / NHAI",
        "Prajavani Petition": "District Collector",
        "Sanitation":         "GHMC",
        "Land Encroachment":  "Revenue / HMDA",
    })
    return df


# ── Voter sentiment records ───────────────────────────────────────────────────
_RAW_SENTIMENT = [
    ("Congress promised piped water by December 2024 — nothing yet. Same old story.",
     "Angry / Frustrated", "Manikonda Village", 17.4071, 78.3765),

    ("They at least started the road work near Lanco Hills, gives some hope.",
     "Hopeful", "Lanco Hills", 17.4089, 78.3812),

    ("Prajavani is just a file-collection exercise. My petition is 2 months old.",
     "Angry / Frustrated", "Neknampur", 17.4123, 78.3689),

    ("The new ward councillor actually visited us after the flooding. Small step.",
     "Hopeful", "Khajaguda", 17.3985, 78.3841),

    ("Power cuts are the same as BRS days. Nothing changed.",
     "Angry / Frustrated", "Puppalguda", 17.3934, 78.3798),

    ("I don't follow politics. Just want the road fixed.",
     "Neutral", "Nallagandla", 17.4245, 78.3456),

    ("Garbage piles up and someone comes to take photos for social media.",
     "Angry / Frustrated", "Manikonda Basti", 17.4055, 78.3740),

    ("Congress government opened RDO grievance camp — at least they're listening.",
     "Hopeful", "Raj Bhavan Colony", 17.4102, 78.3829),

    ("Lake encroachment complaint filed in 2022. BRS ignored it. Congress also silent.",
     "Angry / Frustrated", "Neknampur Layout", 17.4138, 78.3701),

    ("Let's see — they've been in power only 18 months. Reserving judgement.",
     "Neutral", "Manikonda", 17.4060, 78.3780),

    ("The fluoride issue has been known for years. Nobody acts, just surveys.",
     "Angry / Frustrated", "Manikonda Outer Ring", 17.4035, 78.3751),

    ("I heard the MP is pushing for the nala widening project. Fingers crossed.",
     "Hopeful", "Puppalguda Lake Rd", 17.3921, 78.3815),
]

_SENTIMENT_COLS = ["text", "sentiment", "location", "lat", "lon"]


def get_sentiment_data() -> pd.DataFrame:
    return pd.DataFrame(_RAW_SENTIMENT, columns=_SENTIMENT_COLS)


# ── BRS vs Congress project tracker ──────────────────────────────────────────
_BRS_PROJECTS = [
    ("Neknampur Lake Beautification",  "2021", "Sanctioned ₹4.2 Cr", "0%",   "Funds diverted"),
    ("Manikonda Underground Drainage", "2020", "Sanctioned ₹12 Cr",  "15%",  "Contractor abandoned"),
    ("Lanco Hills Flyover Proposal",   "2022", "DPR approved",        "0%",   "Land acquisition stalled"),
    ("Puppalguda Borewell Recharge",   "2019", "Sanctioned ₹1.8 Cr", "40%",  "Incomplete, machinery gone"),
    ("Ward 3 Street Light Scheme",     "2021", "Sanctioned ₹60 L",   "60%",  "150 of 250 lights done"),
]

_CONGRESS_ACTIONS = [
    ("Prajavani Grievance Camps",         "2024", "4 camps held",          "Ongoing",   "1,240 petitions received"),
    ("Manikonda Water Pipeline Survey",   "2024", "Survey completed",      "Planning",  "DPR under review at HMWSSB"),
    ("Khajaguda Drain Desilting",         "2025", "Work order issued",     "In Progress","60% complete before monsoon"),
    ("Puppalguda Transformer Upgrade",    "2025", "₹45 L sanctioned",      "In Progress","Expected completion Jun 2025"),
    ("Neknampur Lake FTL Survey",         "2025", "Revenue survey ordered","In Progress","Boundary demarcation pending"),
]

_BRS_COLS = ["project", "year", "allocation", "completion", "status_note"]
_CON_COLS = ["initiative", "year", "action_taken", "status", "note"]


def get_brs_projects() -> pd.DataFrame:
    return pd.DataFrame(_BRS_PROJECTS, columns=_BRS_COLS)


def get_congress_actions() -> pd.DataFrame:
    return pd.DataFrame(_CONGRESS_ACTIONS, columns=_CON_COLS)
