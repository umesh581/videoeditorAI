"""
Grievance Lifecycle Engine
- Aging tracker with multi-tier escalation logic
- Political opportunity scoring
- RDO / Collector escalation letter generator
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    ESCALATION_THRESHOLD_URGENT,
    ESCALATION_THRESHOLD_POLITICAL,
    ESCALATION_THRESHOLD_CRITICAL,
    ERA_BRS, ERA_CONGRESS,
)


@dataclass
class EscalationFlag:
    grievance_id: int
    location: str
    category: str
    days_pending: int
    families_affected: int
    petition_no: str
    tier: str           # "URGENT" | "POLITICAL" | "CRITICAL"
    action: str
    opportunity_score: float = 0.0


def classify_escalation(row: pd.Series) -> str:
    d = row["days_pending"]
    if d >= ESCALATION_THRESHOLD_CRITICAL:
        return "CRITICAL"
    elif d >= ESCALATION_THRESHOLD_POLITICAL:
        return "POLITICAL"
    elif d >= ESCALATION_THRESHOLD_URGENT:
        return "URGENT"
    return "MONITOR"


def compute_opportunity_score(row: pd.Series) -> float:
    """
    0–100 score combining:
      - Aging weight   (50%)
      - Families hit   (30%)
      - BRS-era origin (20% bonus — stronger contrast narrative)
    """
    age_score  = min(row["days_pending"] / 100, 1.0) * 50
    fam_score  = min(row["families_affected"] / 300, 1.0) * 30
    era_bonus  = 20 if row["era"] == ERA_BRS else 0
    return round(age_score + fam_score + era_bonus, 1)


def _action_for_tier(tier: str, category: str, agency: str) -> str:
    actions = {
        "CRITICAL": f"Escalate to District Collector with written representation. "
                    f"Demand written response within 7 days. Copy: {agency}, MLA office.",
        "POLITICAL": f"Raise at next Prajavani camp. Publish status publicly. "
                     f"File RTI with {agency} if no response in 5 days.",
        "URGENT":   f"Call {agency} helpline today. Visit RDO office with petition copy. "
                     f"Post update on ward WhatsApp group.",
    }
    return actions.get(tier, "Monitor — no action required yet.")


def enrich_grievances(df: pd.DataFrame) -> pd.DataFrame:
    """Add escalation tier, opportunity score, and recommended action."""
    df = df.copy()
    df["escalation_tier"]    = df.apply(classify_escalation, axis=1)
    df["opportunity_score"]  = df.apply(compute_opportunity_score, axis=1)
    df["recommended_action"] = df.apply(
        lambda r: _action_for_tier(r["escalation_tier"], r["category"], r["agency"]),
        axis=1
    )
    return df.sort_values("opportunity_score", ascending=False).reset_index(drop=True)


def get_escalation_flags(df: pd.DataFrame) -> List[EscalationFlag]:
    """Return structured flag objects for the escalation panel."""
    flags = []
    actionable = df[df["escalation_tier"].isin(["CRITICAL", "POLITICAL", "URGENT"])]
    for _, row in actionable.iterrows():
        flags.append(EscalationFlag(
            grievance_id    = int(row["id"]),
            location        = row["location"],
            category        = row["category"],
            days_pending    = int(row["days_pending"]),
            families_affected=int(row["families_affected"]),
            petition_no     = row["petition_no"],
            tier            = row["escalation_tier"],
            action          = row["recommended_action"],
            opportunity_score=row["opportunity_score"],
        ))
    return sorted(flags, key=lambda x: x.opportunity_score, reverse=True)


def generate_collector_letter(flag: EscalationFlag, candidate_name: str) -> str:
    """Generate a formal escalation letter draft for the District Collector."""
    return f"""
TO,
The District Collector,
Rangareddy District, Telangana.

SUB: Urgent Representation — Civic Grievance Pending for {flag.days_pending} Days
      Petition No: {flag.petition_no} | Location: {flag.location}

Respected Sir/Ma'am,

I, {candidate_name}, write on behalf of {flag.families_affected} families
residing in {flag.location}, who have been suffering due to the unresolved
**{flag.category}** issue for the past **{flag.days_pending} days**.

The matter was duly filed under Prajavani (Petition: {flag.petition_no})
and routed to the concerned agency. Despite the passage of over
{flag.days_pending} days, no meaningful resolution has been communicated
to the affected residents.

I respectfully request:
1. An immediate status update on Petition {flag.petition_no}.
2. A written action plan with a timeline within 7 working days.
3. Coordination with {flag.category}-specific agency for on-ground resolution.

Failure to resolve this within the stipulated period will necessitate
escalation to the Hon'ble Chief Minister's Grievance Cell.

Thanking you,

{candidate_name}
People's Representative, {flag.location} Area
Date: {pd.Timestamp.today().strftime("%d %B %Y")}
""".strip()


def aging_summary(df: pd.DataFrame) -> dict:
    """High-level KPIs for the dashboard header."""
    total     = len(df)
    critical  = len(df[df["escalation_tier"] == "CRITICAL"])
    political = len(df[df["escalation_tier"] == "POLITICAL"])
    urgent    = len(df[df["escalation_tier"] == "URGENT"])
    resolved  = len(df[df["status"] == "Resolved"])
    avg_days  = df["days_pending"].mean()
    families  = df["families_affected"].sum()

    return {
        "total_grievances":    total,
        "critical_count":      critical,
        "political_count":     political,
        "urgent_count":        urgent,
        "resolved_count":      resolved,
        "pending_count":       total - resolved,
        "avg_days_pending":    round(avg_days, 1),
        "families_affected":   int(families),
        "top_opportunity":     df.iloc[0]["location"] if total else "—",
    }
