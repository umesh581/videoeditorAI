"""
Shared form field definitions — used by both the Streamlit intake form
and the Google Form auto-generator (Apps Script).

All categories match the official CPGRAMS Rangareddy taxonomy exactly,
so your data is directly comparable to government records.
"""

# Manikonda / Neknampur micro-locations
LOCATIONS = [
    "Manikonda Village",
    "Neknampur",
    "Puppalguda",
    "Lanco Hills",
    "Khajaguda",
    "Nallagandla",
    "Raj Bhavan Colony",
    "Alkapur Township",
    "Fairfield Colony",
    "Lakshmi Nagar Colony",
    "YSR Colony",
    "Byouth Colony",
    "Pioneer Estate",
    "EVV Colony",
    "EIPL Tamarind",
    "Manikonda Basti",
    "Neknampur Layout",
    "Puppalguda Extension",
    "Other (specify below)",
]

# Official CPGRAMS Rangareddy grievance categories (code → label)
CPGRAMS_CATEGORIES = {
    "002": "Civic amenities / Quality of service",
    "001": "Delay in decision / implementation",
    "004": "Revenue / Land / Tax",
    "010": "Corruption / Malpractices",
    "008": "Service matters (Govt employees)",
    "003": "Law & Order",
    "011": "Harassment / Misbehaviour",
    "005": "Compensations / Refunds",
    "006": "Social Evils",
    "007": "Retirement dues",
    "012": "SC / ST / Backward class issues",
    "015": "Legal Redress",
    "009": "Requests / Permissions",
    "013": "Central Govt miscellaneous",
    "014": "State Govt miscellaneous",
}

# Sub-categories under "Civic amenities" — most common in Manikonda
CIVIC_SUBCATEGORIES = [
    "Water supply / shortage",
    "Drainage / flooding",
    "Road / pothole",
    "Power cut / electricity",
    "Street lights",
    "Garbage / sanitation",
    "Lake / nala encroachment",
    "Open space encroachment",
    "Tree fall / maintenance",
    "Public toilet",
    "Other civic issue",
]

# Responsible agencies (used for routing)
AGENCY_MAP = {
    "002": "GHMC / Municipal Commissioner Manikonda",
    "001": "District Collector / RDO",
    "004": "Revenue Dept / Tahsildar",
    "010": "District Collector",
    "008": "Dept of Personnel",
    "003": "Police / Commissioner",
    "011": "District Collector",
    "005": "Relevant Dept",
    "006": "Police / Social Welfare",
    "007": "AG Office / Treasury",
    "012": "SC/ST Welfare Dept",
    "015": "District Legal Services",
    "009": "Relevant Dept",
    "013": "Central Govt Office",
    "014": "State Govt Office",
}

URGENCY_LEVELS = [
    "Critical — Immediate risk to health/safety",
    "High — Affecting daily life significantly",
    "Medium — Ongoing inconvenience",
    "Low — Long-standing, can wait",
]

WARD_NUMBERS = [str(i) for i in range(100, 140)]  # Manikonda area wards

# Mandal codes for Rangareddy (from CPGRAMS AJAX)
MANDALS = {
    "21/151": "SAROORNAGAR",
    "25/151": "SRILINGAMPALLE",
    "20/151": "RAJENDRANAGAR",
    "7/151":  "GANDIPET",
    "3/151":  "BALAPUR",
}

# Department code for Manikonda (from CPGRAMS AJAX extraction)
MANIKONDA_DEPT_CODE = "MCMKONDA"
RANGAREDDY_DIST_CODE = "DARRD"
RANGAREDDY_DIST_NUM  = "151"
