"""Central configuration for the Constituency Dashboard."""

CONSTITUENCY = "Manikonda–Neknampur"
CANDIDATE_NAME   = "Jithender Merugu"
CANDIDATE_HANDLE = "@JITHUINC"
CANDIDATE_ROLE   = "Congress Corporator Candidate · Manikonda–Neknampur Ward"
DISTRICT = "Rangareddy"
MANDAL = "Manikonda"

# Geographic center for maps (Manikonda, Telangana)
MAP_CENTER = [17.4065, 78.3772]
MAP_ZOOM = 14

# Escalation thresholds (days)
ESCALATION_THRESHOLD_POLITICAL = 30   # Flag as "Political Opportunity"
ESCALATION_THRESHOLD_CRITICAL  = 60   # Escalate to District Collector
ESCALATION_THRESHOLD_URGENT    = 15   # Raise with RDO immediately

# Scraper keywords
SEARCH_KEYWORDS = [
    "Manikonda water crisis",
    "Neknampur lake encroachment",
    "Prajavani pending Manikonda",
    "Manikonda GHMC complaint",
    "Puppalguda power cut",
    "Lanco Hills traffic",
    "Neknampur drainage flooding",
    "Manikonda sewage overflow",
]

# Sentiment labels
SENTIMENT_ANGRY     = "Angry / Frustrated"
SENTIMENT_NEUTRAL   = "Neutral"
SENTIMENT_HOPEFUL   = "Hopeful"

# Government eras
ERA_BRS       = "BRS Era (Pre-2023)"
ERA_CONGRESS  = "Congress Era (2024–Present)"

# Issue categories
CATEGORIES = [
    "Water Supply",
    "Lake Encroachment",
    "Drainage & Flooding",
    "Power / Electricity",
    "Roads & Traffic",
    "Prajavani Petition",
    "Sanitation",
    "Land Encroachment",
]

# Responsible agencies
AGENCIES = {
    "Water Supply":       "HMWSSB",
    "Lake Encroachment":  "HMDA / Revenue",
    "Drainage & Flooding":"GHMC",
    "Power / Electricity":"TSSPDCL",
    "Roads & Traffic":    "GHMC / NHAI",
    "Prajavani Petition": "District Collector",
    "Sanitation":         "GHMC",
    "Land Encroachment":  "Revenue / HMDA",
}

# Color scheme (professional blue-saffron palette)
COLORS = {
    "primary":   "#1E3A5F",
    "accent":    "#FF6B35",
    "success":   "#2ECC71",
    "warning":   "#F39C12",
    "danger":    "#E74C3C",
    "neutral":   "#95A5A6",
    "congress":  "#1565C0",
    "brs":       "#E91E63",
}
