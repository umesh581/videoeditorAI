"""
Content Opportunity engine for the candidate (Jithender Merugu / @JITHUINC).

DESIGN RULE — ZERO HALLUCINATION
Every draft this module produces must be tied to a verifiable source:
  • A grievance from the DB with a source_url and source_type
  • A news article with a real URL and source name
  • A tweet from a tracked X handle with its URL

If a record lacks a source, it is filtered out — we do not generate drafts
for issues the user can't independently verify. The UI must surface the
source URL alongside every draft so Jithender can read the underlying
article/petition before posting.
"""

import pandas as pd

AGENCY_TAGS = {
    "Water":     "@HMWSSBOnline @CMOTelangana",
    "Drainage":  "@GHMCOnline @CommissionrGHMC",
    "Road":      "@GHMCOnline @CommrRRDistrict",
    "Lake":      "@HYDRAA_Comm @CMOTelangana",
    "Encroach":  "@HYDRAA_Comm @CollectorRRD",
    "Power":     "@TSSPDCL",
    "Garbage":   "@GHMCOnline",
    "Sewage":    "@HMWSSBOnline",
}

HASHTAGS_CORE = ["#Manikonda", "#Neknampur", "#Rangareddy", "#GHMC"]


def _pick_tag(category: str) -> str:
    for k, v in AGENCY_TAGS.items():
        if k.lower() in (category or "").lower():
            return v
    return "@GHMCOnline @CMOTelangana"


def _has_source(row: pd.Series) -> bool:
    """A row is post-worthy only if it carries a real source we can cite."""
    url = str(row.get("source_url") or row.get("url") or "").strip()
    return url.startswith("http")


def _source_block(row: pd.Series) -> dict:
    """Standardized source metadata attached to every draft."""
    url = str(row.get("source_url") or row.get("url") or "").strip()
    src_type = row.get("source_type", "")
    src_name = row.get("source", "")
    reported = row.get("reported_date") or row.get("published") or row.get("scraped_at", "")
    label_parts = []
    if src_name:  label_parts.append(str(src_name))
    if src_type:  label_parts.append(str(src_type))
    if reported:  label_parts.append(f"as of {str(reported)[:10]}")
    return {
        "url":         url,
        "label":       " · ".join(label_parts) or "Source",
        "verifiable":  bool(url),
    }


def grievance_to_tweet(row: pd.Series) -> dict:
    """Return {'tweet': str, 'source': {...}} — NEVER bare strings."""
    cat   = row.get("category", "civic issue")
    loc   = row.get("location", "Manikonda")
    days  = int(row.get("days_pending", 0) or 0)
    fams  = int(row.get("families_affected", 0) or 0)
    tag   = _pick_tag(cat)
    hash_ = " ".join(HASHTAGS_CORE[:3])
    src   = _source_block(row)

    # Phrase facts conservatively — only state what we can cite
    fam_clause  = f"{fams}+ families affected per the report. " if fams > 0 else ""
    days_clause = f"Pending for {days} days. " if days > 0 else ""

    tweet = (
        f"🚨 {loc}: {cat}. {days_clause}{fam_clause}"
        f"{tag} — requesting action. "
        f"Source: {src['url']} {hash_}"
    )
    return {"tweet": tweet[:280], "source": src}


def grievance_to_thread(row: pd.Series, candidate: str) -> dict:
    cat  = row.get("category", "civic issue")
    loc  = row.get("location", "Manikonda")
    days = int(row.get("days_pending", 0) or 0)
    fams = int(row.get("families_affected", 0) or 0)
    pet  = row.get("petition_no", "")
    tag  = _pick_tag(cat)
    src  = _source_block(row)

    fam_clause = f"{fams}+ families are affected per the source report. " if fams > 0 else ""
    pet_clause = f"Petition ref: {pet}. " if pet else ""

    thread = [
        f"1/ Documented case in {loc} — {cat.lower()}. "
        f"This issue is on record (see source below). {fam_clause}🧵👇",

        f"2/ {pet_clause}The {days}-day delay on this category of issue is what "
        f"Prajavani was designed to fix — but execution is lagging on the ground.",

        f"3/ My commitment as your candidate: personally escalate this to the "
        f"RDO and District Collector within 7 days, with public follow-up.\n"
        f"📎 Source: {src['url']}\n"
        f"{tag} {' '.join(HASHTAGS_CORE)} — {candidate}",
    ]
    return {"thread": thread, "source": src}


def news_to_reaction_tweet(article: pd.Series, candidate: str) -> dict:
    title = (article.get("title") or "")[:140]
    sentiment = article.get("sentiment", "Neutral")
    src = _source_block(article)

    if sentiment == "Angry / Frustrated":
        opener = "This is exactly what residents have been telling me on the ground."
    elif sentiment == "Hopeful":
        opener = "Welcome news — but we must hold the line until delivery is verified."
    else:
        opener = "Sharing so every Manikonda–Neknampur voter sees this."

    tweet = (
        f"{opener}\n\n📰 {title}\n"
        f"Source: {src['url']}\n"
        f"{' '.join(HASHTAGS_CORE[:3])} — {candidate}"
    )
    return {"tweet": tweet[:280], "source": src}


def rank_grievance_opportunities(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Highest-scoring SOURCED grievances — drops anything without a URL."""
    if df.empty:
        return df
    if "source_url" in df.columns:
        df = df[df["source_url"].fillna("").str.startswith("http")]
    if df.empty:
        return df
    sort_cols = [c for c in ["opportunity_score", "days_pending", "families_affected"] if c in df.columns]
    return df.sort_values(by=sort_cols, ascending=False).head(n)


def rank_news_opportunities(news_df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Articles with real URLs — angry-sentiment prioritized."""
    if news_df.empty:
        return news_df
    sourced = news_df[news_df["url"].fillna("").str.startswith("http")]
    if sourced.empty:
        return sourced
    angry = sourced[sourced["sentiment"] == "Angry / Frustrated"]
    return (angry if len(angry) >= n else sourced).head(n)


def analyze_candidate_voice(tweets_df: pd.DataFrame) -> dict:
    if tweets_df.empty:
        return {
            "tweet_count": 0,
            "summary": "No tweets ingested yet. Once the X scanner finds a working Nitter mirror (or you wire a paid X API key), @JITHUINC's recent posts will appear here.",
            "topics": [],
            "cadence": "unknown",
            "samples": [],
        }

    own = tweets_df[tweets_df["source"].fillna("").str.contains("@JITHUINC", case=False, na=False)]
    if own.empty:
        return {
            "tweet_count": 0,
            "summary": "X scanner is running, but no @JITHUINC tweets captured yet. All Nitter mirrors are currently 403/down — recommend paid X API access.",
            "topics": [],
            "cadence": "unknown",
            "samples": [],
        }

    text_blob = " ".join(own["title"].fillna("").tolist()).lower()
    topic_map = {
        "Water/HMWSSB":  ["water", "hmwssb", "tap"],
        "Drainage":      ["drain", "sewage", "flood"],
        "Roads":         ["road", "pothole"],
        "Lakes":         ["lake", "neknampur", "encroach"],
        "Congress/Govt": ["congress", "revanth", "kcr", "brs"],
        "Local events":  ["meeting", "padayatra", "visit", "inaugurat"],
    }
    topics = []
    for label, keys in topic_map.items():
        c = sum(text_blob.count(k) for k in keys)
        if c:
            topics.append((label, c))
    topics.sort(key=lambda x: -x[1])

    samples = [
        {"title": r["title"], "url": r["url"], "date": r.get("published", "")}
        for _, r in own.head(5).iterrows()
    ]

    return {
        "tweet_count": len(own),
        "summary": f"Captured {len(own)} tweets. Top topics: " +
                   (", ".join(f"{t[0]} ({t[1]})" for t in topics[:3]) if topics else "general posts"),
        "topics": topics,
        "cadence": f"~{len(own)} posts in recent window",
        "samples": samples,
    }


def content_gap_recommendations(candidate_voice: dict, grievances_df: pd.DataFrame) -> list:
    """Suggest gap topics — ONLY where we have a sourced grievance to back the draft."""
    if grievances_df.empty:
        return []

    # Only use grievances with a real source URL
    sourced = grievances_df
    if "source_url" in grievances_df.columns:
        sourced = grievances_df[grievances_df["source_url"].fillna("").str.startswith("http")]
    if sourced.empty:
        return []

    voter_topics = sourced["category"].fillna("").str.lower().value_counts().to_dict()
    candidate_topics = {t[0].lower(): t[1] for t in candidate_voice.get("topics", [])}

    gaps = []
    topic_check = {
        "water": "Water/HMWSSB", "drainage": "Drainage", "road": "Roads",
        "lake": "Lakes", "encroach": "Lakes", "garbage": None,
        "sewage": "Drainage", "power": None,
    }
    for voter_topic, count in voter_topics.items():
        matched = False
        for key, cand_key in topic_check.items():
            if key in voter_topic:
                if cand_key and cand_key.lower() in candidate_topics:
                    matched = True
                break
        if not matched:
            row = sourced[sourced["category"].fillna("").str.lower()
                          .str.contains(voter_topic.split()[0] if voter_topic else "", na=False)]
            if row.empty:
                continue
            draft = grievance_to_tweet(row.iloc[0])
            gaps.append({
                "topic":            voter_topic.title(),
                "voter_complaints": int(count),
                "your_posts":       0,
                "why":              f"{count} sourced grievances on this — voters are searching for someone to speak about it.",
                "tweet":            draft["tweet"],
                "source":           draft["source"],
            })
    return gaps[:5]
