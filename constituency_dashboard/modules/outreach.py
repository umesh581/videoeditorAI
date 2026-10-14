"""
Smart Outreach Panel
- WhatsApp-ready daily briefing generator
- Field visit priority list
- RTI draft generator
- Prajavani petition summary
"""

import pandas as pd
from datetime import datetime
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CANDIDATE_NAME, CONSTITUENCY


def _today_str() -> str:
    return datetime.today().strftime("%d %B %Y")


def generate_whatsapp_brief(df: pd.DataFrame, top_n: int = 3) -> str:
    """
    Generate a WhatsApp-ready daily brief for the candidate.
    Targets the top N highest-opportunity grievances.
    """
    top = df[df["escalation_tier"].isin(["CRITICAL", "POLITICAL", "URGENT"])].head(top_n)

    lines = [
        f"🔔 *CONSTITUENCY DAILY BRIEF — {_today_str()}*",
        f"📍 {CONSTITUENCY} | Representative: {CANDIDATE_NAME}",
        "─────────────────────────────",
    ]

    for i, (_, row) in enumerate(top.iterrows(), 1):
        families = row["families_affected"]
        family_str = f"{families} families" if families > 0 else "multiple residents"
        tier_emoji = {"CRITICAL": "🔴", "POLITICAL": "🟠", "URGENT": "🟡"}.get(
            row["escalation_tier"], "⚪"
        )
        lines += [
            f"\n{tier_emoji} *Issue {i}: {row['category']}*",
            f"📌 Location: {row['location']}",
            f"👥 Affected: {family_str}",
            f"⏱️ Pending: *{row['days_pending']} days*",
            f"📄 Petition: {row['petition_no']}",
            f"✅ Action: {row['recommended_action'][:120]}...",
        ]

    lines += [
        "\n─────────────────────────────",
        f"📊 Dashboard: http://localhost:8501",
        f"📅 Generated: {_today_str()}",
    ]
    return "\n".join(lines)


def generate_field_visit_plan(df: pd.DataFrame, visit_date: str = None) -> str:
    """
    Generate a structured field visit plan for the day.
    Prioritizes by opportunity score and clusters by location proximity.
    """
    if visit_date is None:
        visit_date = _today_str()

    priority = df[df["escalation_tier"].isin(["CRITICAL", "POLITICAL", "URGENT"])].head(5)

    lines = [
        f"📋 *FIELD VISIT PLAN — {visit_date}*",
        f"Candidate: {CANDIDATE_NAME}",
        "═══════════════════════════════",
    ]

    times = ["9:00 AM", "10:30 AM", "12:00 PM", "3:00 PM", "5:00 PM"]
    for i, (_, row) in enumerate(priority.iterrows()):
        t = times[i] if i < len(times) else "TBD"
        lines += [
            f"\n⏰ {t} — *{row['location']}*",
            f"   Issue: {row['category']}",
            f"   Brief: {row['description'][:100]}...",
            f"   Talking Point: Pending {row['days_pending']} days. "
            f"{row['families_affected']} families impacted.",
            f"   Take: Copy of {row['petition_no']} + this data printout",
        ]

    lines += [
        "\n═══════════════════════════════",
        "💡 Tip: Record a 30-sec video at each site for social media.",
        "📱 Tag: @ManikondaGrievances | #PrajaBandham",
    ]
    return "\n".join(lines)


def generate_rti_draft(row: pd.Series, candidate_name: str = CANDIDATE_NAME) -> str:
    """RTI application draft targeting the relevant agency."""
    return f"""
RTI APPLICATION UNDER THE RIGHT TO INFORMATION ACT, 2005

TO,
The Public Information Officer,
{row['agency']},
Telangana State.

DATE: {_today_str()}

SUB: Information sought regarding Grievance / Petition No. {row['petition_no']}

Sir/Ma'am,

Under Section 6(1) of the RTI Act 2005, I hereby seek the following information
regarding civic grievance filed for {row['location']}:

1. Current status of Petition/Complaint No. {row['petition_no']}
2. Date on which the complaint was received at your office
3. Name and designation of the officer assigned to this complaint
4. Action taken to date, with supporting documents
5. Expected date of resolution / work completion
6. Reason for delay, if resolution has exceeded 30 days

The issue relates to: *{row['category']}* — {row['description'][:120]}

This complaint has been pending for {row['days_pending']} days and affects
{row['families_affected']} families.

Applicant: {candidate_name}
Address: {CONSTITUENCY}, Telangana
Phone: [Your Phone]
""".strip()


def generate_social_media_post(row: pd.Series) -> dict:
    """Return platform-specific social media post drafts."""
    base = (
        f"🚨 {row['days_pending']} days and counting.\n\n"
        f"{row['families_affected']} families in *{row['location']}* are still "
        f"suffering due to unresolved *{row['category']}* issues.\n\n"
        f"Petition {row['petition_no']} filed — NO response yet.\n\n"
        f"I am personally escalating this to the {row['agency']} today.\n\n"
        f"#Manikonda #Neknampur #Prajavani #PeopleFirst"
    )
    return {
        "whatsapp": base,
        "twitter":  f"🚨 {row['days_pending']}d pending. {row['location']} {row['category']} "
                    f"crisis — {row['families_affected']} families affected. "
                    f"Escalating to {row['agency']} now. Petition: {row['petition_no']} "
                    f"#Manikonda #Prajavani",
        "facebook": base + "\n\nTag your friends from this area. They deserve to know.",
    }
