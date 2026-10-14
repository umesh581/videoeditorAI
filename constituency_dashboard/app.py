"""
Constituency Grievance & Accountability Dashboard
Manikonda – Neknampur | Rangareddy District, Telangana

Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_folium import st_folium

# ── Start background scheduler (runs scrapers every 30 min) ───────────────────
from modules.scheduler import start_scheduler, get_status, run_all_scrapers
start_scheduler()

# ── Local modules ──────────────────────────────────────────────────────────────
from modules.mock_data       import (get_grievances as get_mock_grievances,
                                     get_sentiment_data as get_mock_sentiment,
                                     get_brs_projects, get_congress_actions)
from modules.database        import (get_grievances_db, get_articles, get_sentiment_db,
                                     get_scrape_log, db_counts, get_last_scrape)
from modules.grievance_engine import enrich_grievances, aging_summary, get_escalation_flags, generate_collector_letter
from modules.data_ingestion  import sentiment_summary, classify_sentiment
from modules.visualizations  import (
    build_heatmap, build_sentiment_map,
    grievance_aging_bar, category_donut,
    sentiment_donut, brs_vs_congress_chart,
    opportunity_score_scatter,
)
from modules.outreach import (
    generate_whatsapp_brief,
    generate_field_visit_plan,
    generate_rti_draft,
    generate_social_media_post,
)
from modules.form_config import (
    LOCATIONS, CPGRAMS_CATEGORIES, CIVIC_SUBCATEGORIES, URGENCY_LEVELS
)
from modules.google_sheets import fetch_sheet_responses, transform_responses
from modules.content_strategy import (
    rank_grievance_opportunities, rank_news_opportunities,
    grievance_to_tweet, grievance_to_thread, news_to_reaction_tweet,
    analyze_candidate_voice, content_gap_recommendations,
)
from config import CONSTITUENCY, CANDIDATE_NAME, CANDIDATE_HANDLE, CANDIDATE_ROLE, COLORS

# ── Page configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{CONSTITUENCY} Accountability Dashboard",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Force legible text in ALL custom cards regardless of theme ── */
  .metric-card, .critical-card, .political-card, .urgent-card,
  .whatsapp-box, .quote-angry, .quote-hopeful, .quote-neutral,
  .news-card, .section-header, .brs-card, .congress-card {{
    color: #1A1A2E !important;
  }}
  .metric-card {{
    background: #FFFFFF;
    border-left: 5px solid {COLORS['primary']};
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    color: #1A1A2E !important;
  }}
  .metric-card b {{ color: {COLORS['primary']} !important; }}

  .critical-card {{
    background: #FFF0F0;
    border-left: 6px solid {COLORS['danger']};
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 10px;
    box-shadow: 0 2px 6px rgba(231,76,60,0.12);
    color: #1A1A2E !important;
  }}
  .critical-card b {{ color: #C0392B !important; }}

  .political-card {{
    background: #FFF5EC;
    border-left: 6px solid {COLORS['accent']};
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 10px;
    box-shadow: 0 2px 6px rgba(255,107,53,0.12);
    color: #1A1A2E !important;
  }}
  .political-card b {{ color: #C05000 !important; }}

  .urgent-card {{
    background: #FFFBEA;
    border-left: 6px solid {COLORS['warning']};
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 10px;
    box-shadow: 0 2px 6px rgba(243,156,18,0.12);
    color: #1A1A2E !important;
  }}
  .urgent-card b {{ color: #B7770D !important; }}

  .whatsapp-box {{
    background: #F0FDF4;
    border: 2px solid #86EFAC;
    padding: 18px 20px;
    border-radius: 12px;
    font-family: 'Courier New', monospace;
    font-size: 13.5px;
    line-height: 1.7;
    white-space: pre-wrap;
    color: #1A2E1A !important;
  }}

  .section-header {{
    font-size: 22px;
    font-weight: 800;
    color: {COLORS['primary']} !important;
    border-bottom: 3px solid {COLORS['accent']};
    padding-bottom: 8px;
    margin-bottom: 20px;
    letter-spacing: -0.3px;
  }}

  /* ── Quote cards ── */
  .quote-angry {{
    background: #FFF0F0;
    border-left: 4px solid {COLORS['danger']};
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
    color: #1A1A2E !important;
  }}
  .quote-hopeful {{
    background: #F0FDF4;
    border-left: 4px solid {COLORS['success']};
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
    color: #1A1A2E !important;
  }}
  .quote-neutral {{
    background: #F7F8FA;
    border-left: 4px solid {COLORS['neutral']};
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
    color: #1A1A2E !important;
  }}
  .quote-angry i, .quote-hopeful i, .quote-neutral i {{
    color: #333333 !important;
    font-style: italic;
  }}
  .quote-angry small, .quote-hopeful small, .quote-neutral small {{
    color: #555555 !important;
    font-size: 12px;
  }}

  /* ── News cards ── */
  .news-card {{
    background: #FFFFFF;
    border-left: 5px solid {COLORS['primary']};
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    color: #1A1A2E !important;
  }}
  .news-card b  {{ color: {COLORS['primary']} !important; }}
  .news-card small {{ color: #555555 !important; }}

  /* ── BRS / Congress comparison cards ── */
  .brs-card {{
    background: #FFF0F5;
    border-left: 6px solid {COLORS['brs']};
    padding: 13px 16px;
    border-radius: 10px;
    margin-bottom: 10px;
    color: #1A1A2E !important;
  }}
  .brs-card b {{ color: #880E4F !important; }}

  .congress-card {{
    background: #EFF6FF;
    border-left: 6px solid {COLORS['congress']};
    padding: 13px 16px;
    border-radius: 10px;
    margin-bottom: 10px;
    color: #1A1A2E !important;
  }}
  .congress-card b {{ color: #0D47A1 !important; }}

  /* ── Escalation tier badges ── */
  .badge-CRITICAL  {{ background:{COLORS['danger']};  color:#fff !important; padding:2px 9px; border-radius:12px; font-size:12px; font-weight:700; }}
  .badge-POLITICAL {{ background:{COLORS['accent']};  color:#fff !important; padding:2px 9px; border-radius:12px; font-size:12px; font-weight:700; }}
  .badge-URGENT    {{ background:{COLORS['warning']}; color:#fff !important; padding:2px 9px; border-radius:12px; font-size:12px; font-weight:700; }}

  /* ── Streamlit dataframe text fix ── */
  .stDataFrame {{ font-size: 13px; }}

  /* ── General body polish ── */
  h1, h2, h3 {{ color: {COLORS['primary']} !important; }}
</style>
""", unsafe_allow_html=True)


# ── Data status badge helper ──────────────────────────────────────────────────
def data_badge(status: str, source: str, last_run: str = "", count=None):
    """Render a coloured pill showing whether this page is on LIVE or SAMPLE data."""
    palette = {
        "live":    ("#16A34A", "🟢 LIVE DATA"),
        "partial": ("#D97706", "🟡 PARTIAL LIVE"),
        "sample":  ("#DC2626", "🔴 SAMPLE / DEMO DATA"),
    }
    color, label = palette.get(status, palette["sample"])
    count_str = f" · {count} records" if count is not None else ""
    last_str  = f" · last refresh {last_run[:16]}" if last_run else ""
    st.markdown(f"""
    <div style="
        display:inline-block;
        background:{color};
        color:#fff;
        padding:6px 14px;
        border-radius:20px;
        font-size:13px;
        font-weight:700;
        margin-bottom:14px;
        box-shadow:0 1px 3px rgba(0,0,0,0.12);">
      {label} &nbsp;·&nbsp; {source}{count_str}{last_str}
    </div>
    """, unsafe_allow_html=True)


def grievances_status():
    """Return (status, source, last_run, count) for grievance-derived pages."""
    live = get_grievances_db()
    if live.empty:
        return ("sample", "Hardcoded seed records (Google Form not yet receiving submissions)", "", 15)
    last = get_last_scrape("google_sheets") or get_last_scrape("news_sites") or ""
    return ("live", "Google Form + news-site grievance extraction", last, len(live))


def news_status():
    c = db_counts().get("news", 0)
    last = get_last_scrape("google_news_rss") or ""
    if c == 0:
        return ("sample", "Scraping in progress", "", 0)
    return ("live", "Google News RSS + Telugu papers + X/Twitter", last, c)


def sentiment_status():
    live = get_sentiment_db()
    if live.empty:
        return ("sample", "Hardcoded voter quotes (real sentiment builds as news + X feed grows)", "", 0)
    return ("live", "News headlines + tweets + form submissions", get_last_scrape("google_news_rss") or "", len(live))


# ── Data loading — real DB first, mock fallback ───────────────────────────────
@st.cache_data(ttl=120, show_spinner="Loading live data...")
def load_data():
    # Grievances: prefer live DB, fall back to mock seed
    live_df = get_grievances_db()
    if live_df.empty:
        raw_df = get_mock_grievances()
    else:
        raw_df = live_df
        if "escalation_tier" not in raw_df.columns:
            raw_df = enrich_grievances(raw_df)

    enriched_df = enrich_grievances(raw_df) if "opportunity_score" not in raw_df.columns else raw_df

    # Sentiment: prefer live DB
    live_sent = get_sentiment_db()
    sentiment_df = live_sent if not live_sent.empty else get_mock_sentiment()

    brs_df     = get_brs_projects()
    congress_df= get_congress_actions()
    kpis       = aging_summary(enriched_df)
    flags      = get_escalation_flags(enriched_df)
    return enriched_df, sentiment_df, brs_df, congress_df, kpis, flags


@st.cache_data(ttl=120, show_spinner="Loading news feed...")
def load_news():
    live = get_articles(limit=80)
    return live if not live.empty else pd.DataFrame()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/200px-Emblem_of_India.svg.png", width=60)
    st.markdown(f"## {CONSTITUENCY}")
    st.markdown("**Accountability Dashboard**")
    st.caption("Rangareddy District, Telangana")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "📊 Executive Summary",
            "🗺️ Voter Pain Heatmap",
            "⚠️ Escalation Engine",
            "⚖️ BRS vs. Congress Tracker",
            "💬 Voter Sentiment",
            "📰 News Intelligence",
            "📱 Smart Outreach",
            "🎯 Content Opportunities (Jithender)",
            "📋 Field Intake Form",
            "🔧 Data Sources",
        ],
    )
    st.divider()

    # ── Live data status ───────────────────────────────────────────────────────
    counts = db_counts()
    sched  = get_status()
    st.markdown("**Live Data Feed**")
    col_a, col_b = st.columns(2)
    col_a.metric("Articles", counts["news"])
    col_b.metric("Grievances", counts["grievances"])

    last_rss = get_last_scrape("google_news_rss")
    if last_rss:
        st.caption(f"Last scraped: {last_rss[:16]}")
    else:
        st.caption("First scrape in progress...")

    status_dot = "🟢" if sched["running"] else "🔴"
    st.caption(f"{status_dot} Scheduler: {'running' if sched['running'] else 'stopped'}")

    if st.button("⚡ Scrape Now", use_container_width=True):
        with st.spinner("Scraping all sources..."):
            run_all_scrapers()
        st.cache_data.clear()
        st.success("Done! Data refreshed.")
        st.rerun()

    if st.button("🔄 Reload Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"Candidate: **{CANDIDATE_NAME}**")
    st.caption("Auto-refresh: every 30 min")


# ── Load data ──────────────────────────────────────────────────────────────────
df, sentiment_df, brs_df, congress_df, kpis, flags = load_data()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Executive Summary
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Executive Summary":
    st.markdown(f"# 🗳️ {CONSTITUENCY} — Constituency Dashboard")
    st.markdown("*Real-time civic intelligence for people-first representation*")
    s, src, last, cnt = grievances_status()
    data_badge(s, f"Grievances: {src}", last, cnt)
    st.divider()

    # ── KPI strip ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Grievances",   kpis["total_grievances"])
    c2.metric("🔴 Critical",         kpis["critical_count"],
              delta=f"+{kpis['critical_count']} need DC",  delta_color="inverse")
    c3.metric("🟠 Political Opps",   kpis["political_count"])
    c4.metric("🟡 Urgent",           kpis["urgent_count"])
    c5.metric("Avg Days Pending",    f"{kpis['avg_days_pending']}d",
              delta="Too long", delta_color="inverse")
    c6.metric("Families Affected",   f"{kpis['families_affected']:,}")

    st.divider()

    # ── Priority alert ─────────────────────────────────────────────────────────
    top = df.iloc[0]
    st.markdown(f"""
    <div class="critical-card">
    🚨 <b>Highest Opportunity Today:</b> {top['location']} — {top['category']}<br/>
    ⏱️ <b>{top['days_pending']} days pending</b> &nbsp;|&nbsp;
    👥 {top['families_affected']} families affected &nbsp;|&nbsp;
    📄 {top['petition_no']}<br/>
    ✅ <i>{top['recommended_action'][:140]}...</i>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Charts row ─────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.plotly_chart(grievance_aging_bar(df), use_container_width=True)
    with col_right:
        st.plotly_chart(category_donut(df), use_container_width=True)

    st.plotly_chart(opportunity_score_scatter(df), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Voter Pain Heatmap
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Voter Pain Heatmap":
    st.markdown('<div class="section-header">🗺️ Voter Pain Heatmap</div>', unsafe_allow_html=True)
    st.markdown("*Red zones = highest civic distress. Size = opportunity score. Click markers for details.*")
    s, src, last, cnt = grievances_status()
    data_badge(s, f"Heatmap built from: {src}", last, cnt)

    tab1, tab2 = st.tabs(["🔥 Grievance Intensity", "😠 Voter Sentiment"])

    with tab1:
        heatmap = build_heatmap(df)
        st_folium(heatmap, width=None, height=520, returned_objects=[])

    with tab2:
        sent_map = build_sentiment_map(sentiment_df)
        st_folium(sent_map, width=None, height=520, returned_objects=[])

        s_counts = sentiment_df["sentiment"].value_counts()
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("😠 Angry / Frustrated", s_counts.get("Angry / Frustrated", 0))
        cc2.metric("😐 Neutral",             s_counts.get("Neutral", 0))
        cc3.metric("🌟 Hopeful",             s_counts.get("Hopeful", 0))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Escalation Engine
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚠️ Escalation Engine":
    st.markdown('<div class="section-header">⚠️ Grievance Escalation Engine</div>', unsafe_allow_html=True)
    st.markdown("Issues flagged for candidate intervention. Sorted by opportunity score.")
    s, src, last, cnt = grievances_status()
    data_badge(s, f"Escalation tiers from: {src}", last, cnt)

    tier_filter = st.multiselect(
        "Filter by Escalation Tier",
        ["CRITICAL", "POLITICAL", "URGENT"],
        default=["CRITICAL", "POLITICAL", "URGENT"],
    )

    filtered_flags = [f for f in flags if f.tier in tier_filter]

    if not filtered_flags:
        st.info("No issues match the selected filters.")
    else:
        for flag in filtered_flags:
            card_class = {
                "CRITICAL": "critical-card", "POLITICAL": "political-card",
            }.get(flag.tier, "urgent-card")

            tier_badge = {
                "CRITICAL":  "🔴 CRITICAL — Escalate to District Collector",
                "POLITICAL": "🟠 POLITICAL OPPORTUNITY — File at Prajavani camp",
                "URGENT":    "🟡 URGENT — Contact RDO today",
            }.get(flag.tier, "")

            with st.container():
                st.markdown(f"""
                <div class="{card_class}">
                  <b>{tier_badge}</b><br/>
                  📍 <b>{flag.location}</b> &nbsp;·&nbsp; {flag.category}<br/>
                  ⏱️ <b>{flag.days_pending} days pending</b> &nbsp;·&nbsp;
                  👥 {flag.families_affected} families &nbsp;·&nbsp;
                  📄 {flag.petition_no}<br/>
                  🏛️ Agency: {df[df['id']==flag.grievance_id]['agency'].values[0]}<br/>
                  🎯 Score: <b>{flag.opportunity_score}/100</b>
                </div>
                """, unsafe_allow_html=True)

            with st.expander(f"📋 Recommended Action & Letter Draft — {flag.location}"):
                st.info(flag.action)
                row = df[df["id"] == flag.grievance_id].iloc[0]
                if flag.tier == "CRITICAL":
                    letter = generate_collector_letter(flag, CANDIDATE_NAME)
                    st.text_area("District Collector Letter Draft", letter, height=380)
                    st.download_button(
                        "📥 Download Letter (.txt)",
                        letter,
                        file_name=f"DC_Letter_{flag.petition_no}.txt",
                    )
                social = generate_social_media_post(row)
                st.text_area("WhatsApp / Social Post", social["whatsapp"], height=160)

    st.divider()
    st.markdown("### 📊 Full Grievance Table")
    display_cols = ["location", "category", "days_pending", "families_affected",
                    "escalation_tier", "opportunity_score", "petition_no", "era", "agency"]
    st.dataframe(
        df[display_cols].style
          .background_gradient(subset=["days_pending"], cmap="Reds")
          .background_gradient(subset=["opportunity_score"], cmap="YlOrRd"),
        use_container_width=True,
        height=400,
    )
    st.download_button(
        "📥 Export Grievances CSV",
        df.to_csv(index=False),
        file_name="constituency_grievances.csv",
        mime="text/csv",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BRS vs. Congress Tracker
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚖️ BRS vs. Congress Tracker":
    st.markdown('<div class="section-header">⚖️ BRS Failures vs. Congress Interventions</div>',
                unsafe_allow_html=True)
    st.markdown("*A factual accountability record — what was promised, abandoned, and now being addressed.*")

    # ── Live news split by era keyword ────────────────────────────────────────
    all_news = get_articles(limit=400)
    brs_live  = all_news[all_news["keyword"].fillna("").str.contains("BRS Era", case=False)] if not all_news.empty else pd.DataFrame()
    cong_live = all_news[all_news["keyword"].fillna("").str.contains("Congress Era", case=False)] if not all_news.empty else pd.DataFrame()

    has_live = (len(brs_live) + len(cong_live)) > 0
    if has_live:
        data_badge("live", f"Google News RSS — BRS/Congress keyword filters · {len(brs_live)} BRS + {len(cong_live)} Congress articles",
                   get_last_scrape("brs_congress") or "", len(brs_live) + len(cong_live))
    else:
        data_badge("sample", "Curated seed list (live news appears after first BRS/Congress scrape)", "", len(brs_df) + len(congress_df))

    st.plotly_chart(brs_vs_congress_chart(brs_df, congress_df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🩸 BRS Era — Unfinished Projects")
        st.markdown(f"*{len(brs_df)} projects abandoned or stalled*")
        for _, row in brs_df.iterrows():
            st.markdown(f"""
            <div class="brs-card">
              <b>{row['project']}</b> <span style="color:#888;font-size:12px">({row['year']})</span><br/>
              <span style="font-size:13px">
                💰 {row['allocation']} &nbsp;|&nbsp;
                📊 Completion: <b>{row['completion']}</b>
              </span><br/>
              <span style="font-size:12px;color:#666;">⚠️ {row['status_note']}</span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"### 🔵 Congress Era — Interventions")
        st.markdown(f"*{len(congress_df)} initiatives taken since 2024*")
        for _, row in congress_df.iterrows():
            st.markdown(f"""
            <div class="congress-card">
              <b>{row['initiative']}</b> <span style="color:#888;font-size:12px">({row['year']})</span><br/>
              <span style="font-size:13px">
                📋 {row['action_taken']} &nbsp;|&nbsp;
                📊 Status: <b>{row['status']}</b>
              </span><br/>
              <span style="font-size:12px;color:#555;">📝 {row['note']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.info(
        "💡 **Candidate Talking Point:** "
        f"The BRS government left {len(brs_df)} key infrastructure projects incomplete "
        f"across {CONSTITUENCY}. The Congress administration has initiated "
        f"{len(congress_df)} corrective actions in 18 months — but {kpis['pending_count']} "
        f"grievances remain open. Our role is to bridge that gap."
    )

    # ── Live news feed split by era ───────────────────────────────────────────
    if has_live:
        st.divider()
        st.markdown("### 📡 Live Press Coverage (last 90 min refresh)")
        lcol, rcol = st.columns(2)
        with lcol:
            st.markdown(f"#### 🩸 BRS-era coverage ({len(brs_live)})")
            for _, row in brs_live.head(8).iterrows():
                st.markdown(f"""
                <div class="brs-card">
                  <b>{row['title'][:160]}</b><br/>
                  <span style="font-size:12px;color:#555;">📰 {row['source']} · 📅 {row.get('published','')}</span><br/>
                  <a href="{row['url']}" target="_blank" style="font-size:12px;color:#880E4F;">↗ Read article</a>
                </div>
                """, unsafe_allow_html=True)
        with rcol:
            st.markdown(f"#### 🔵 Congress-era coverage ({len(cong_live)})")
            for _, row in cong_live.head(8).iterrows():
                st.markdown(f"""
                <div class="congress-card">
                  <b>{row['title'][:160]}</b><br/>
                  <span style="font-size:12px;color:#555;">📰 {row['source']} · 📅 {row.get('published','')}</span><br/>
                  <a href="{row['url']}" target="_blank" style="font-size:12px;color:#0D47A1;">↗ Read article</a>
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Voter Sentiment
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬 Voter Sentiment":
    st.markdown('<div class="section-header">💬 Voter Sentiment Analysis</div>', unsafe_allow_html=True)
    st.markdown("*Sentiment towards the Congress administration's delivery on promises.*")
    s, src, last, cnt = sentiment_status()
    data_badge(s, f"Sentiment: {src}", last, cnt)

    news_df       = load_news()
    sent_summary  = sentiment_summary(news_df)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(sentiment_donut(sent_summary), use_container_width=True)
        total = sum(sent_summary.values())
        for label, count in sent_summary.items():
            pct = round(count / total * 100) if total else 0
            st.metric(label, f"{count} mentions ({pct}%)")

    with col2:
        st.markdown("#### Ground-Level Quotes (Manikonda / Neknampur)")
        for _, row in sentiment_df.iterrows():
            icon = {"Angry / Frustrated": "😠", "Neutral": "😐", "Hopeful": "🌟"}.get(
                row["sentiment"], "💬"
            )
            css_class = {
                "Angry / Frustrated": "quote-angry",
                "Neutral":            "quote-neutral",
                "Hopeful":            "quote-hopeful",
            }.get(row["sentiment"], "quote-neutral")
            badge_color = {
                "Angry / Frustrated": "#E74C3C",
                "Neutral":            "#7F8C8D",
                "Hopeful":            "#27AE60",
            }.get(row["sentiment"], "#7F8C8D")
            st.markdown(f"""
            <div class="{css_class}">
              <span style="font-size:16px">{icon}</span>
              <span style="font-style:italic;color:#2C2C2C;">&nbsp;"{row['text']}"</span><br/>
              <span style="font-size:12px;color:#555555;">
                📍 {row['location']} &nbsp;·&nbsp;
                <span style="background:{badge_color};color:#fff;padding:1px 8px;
                  border-radius:10px;font-size:11px;font-weight:600;">
                  {row['sentiment']}
                </span>
              </span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🎙️ Analyze Custom Text")
    custom_text = st.text_area("Paste a voter quote or news excerpt to classify:", height=100)
    if custom_text:
        result = classify_sentiment(custom_text)
        icon = {"Angry / Frustrated": "😠", "Neutral": "😐", "Hopeful": "🌟"}.get(result, "💬")
        st.success(f"Sentiment: **{result}** {icon}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: News Intelligence
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📰 News Intelligence":
    st.markdown('<div class="section-header">📰 Live News Intelligence</div>', unsafe_allow_html=True)
    s, src, last, cnt = news_status()
    data_badge(s, src, last, cnt)

    news_df = load_news()
    if news_df.empty:
        st.warning("Scraping in progress — check back in 60 seconds or click ⚡ Scrape Now in the sidebar.")
    else:
        pub_col  = "published" if "published" in news_df.columns else "date"
        src_col  = "source"    if "source"    in news_df.columns else "source"
        kw_col   = "keyword"   if "keyword"   in news_df.columns else "keyword"

        s = news_df["sentiment"].value_counts().to_dict()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Articles",       len(news_df))
        col2.metric("😠 Angry Coverage",    s.get("Angry / Frustrated", 0))
        col3.metric("😐 Neutral",           s.get("Neutral", 0))
        col4.metric("🌟 Positive Coverage", s.get("Hopeful", 0))

        st.divider()

        sentiment_filter = st.multiselect(
            "Filter by Sentiment",
            ["Angry / Frustrated", "Neutral", "Hopeful"],
            default=["Angry / Frustrated", "Neutral", "Hopeful"],
        )
        filtered_news = news_df[news_df["sentiment"].isin(sentiment_filter)]

        for _, row in filtered_news.iterrows():
            sent_emoji = {"Angry / Frustrated": "🔴", "Neutral": "⚪", "Hopeful": "🟢"}.get(
                row.get("sentiment", ""), "⚪"
            )
            border_color = {
                "Angry / Frustrated": COLORS["danger"],
                "Neutral":            COLORS["neutral"],
                "Hopeful":            COLORS["success"],
            }.get(row.get("sentiment", ""), COLORS["primary"])
            url     = row.get("url", "#")
            pub     = row.get(pub_col, "")
            source  = row.get(src_col, "")
            keyword = row.get(kw_col, "")
            summary = row.get("summary", "")
            title   = row.get("title", "")
            link_html = f'<a href="{url}" target="_blank" style="color:{COLORS["primary"]};text-decoration:none;">↗ Read article</a>' if url and url != "#" else ""

            st.markdown(f"""
            <div class="news-card" style="border-left-color:{border_color};">
              <span style="font-size:14px;">{sent_emoji}</span>
              <b style="color:#1A1A2E;font-size:14px;">&nbsp;{title}</b><br/>
              <span style="font-size:12px;color:#444;line-height:1.6;">
                {summary[:180] + '...' if len(summary) > 180 else summary}
              </span><br/>
              <span style="font-size:11px;color:#666;">
                📰 {source} &nbsp;·&nbsp; 🏷️ {keyword} &nbsp;·&nbsp; 📅 {pub}
                &nbsp;&nbsp;{link_html}
              </span>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Smart Outreach
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📱 Smart Outreach":
    st.markdown('<div class="section-header">📱 Smart Outreach Panel</div>', unsafe_allow_html=True)
    st.markdown("*Generate field-ready communication in one click.*")
    s, src, last, cnt = grievances_status()
    data_badge(s, f"Outreach copy generated from: {src}", last, cnt)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📲 WhatsApp Brief",
        "🚶 Field Visit Plan",
        "📜 RTI Generator",
        "📣 Social Media",
    ])

    # ── WhatsApp Brief ─────────────────────────────────────────────────────────
    with tab1:
        st.markdown("#### Today's WhatsApp Daily Brief")
        top_n = st.slider("Number of top issues to include", 1, 5, 3)
        brief = generate_whatsapp_brief(df, top_n=top_n)
        st.markdown(f'<div class="whatsapp-box">{brief}</div>', unsafe_allow_html=True)
        st.download_button(
            "📥 Copy / Download Brief",
            brief,
            file_name="daily_brief.txt",
            use_container_width=True,
        )

    # ── Field Visit Plan ───────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Today's Field Visit Plan")
        visit_date = st.date_input("Visit Date", value=pd.Timestamp.today())
        plan = generate_field_visit_plan(df, visit_date.strftime("%d %B %Y"))
        st.markdown(f'<div class="whatsapp-box">{plan}</div>', unsafe_allow_html=True)
        st.download_button(
            "📥 Download Visit Plan",
            plan,
            file_name="field_visit_plan.txt",
            use_container_width=True,
        )

    # ── RTI Generator ──────────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### RTI Application Generator")
        locations = df["location"].tolist()
        selected_loc = st.selectbox("Select Grievance Location", locations)
        row = df[df["location"] == selected_loc].iloc[0]
        rti = generate_rti_draft(row, CANDIDATE_NAME)
        st.text_area("RTI Application Draft", rti, height=400)
        st.download_button(
            "📥 Download RTI Draft (.txt)",
            rti,
            file_name=f"RTI_{row['petition_no']}.txt",
            use_container_width=True,
        )

    # ── Social Media ───────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### Social Media Post Generator")
        sel_loc = st.selectbox("Select Issue Location", df["location"].tolist(), key="sm_sel")
        row = df[df["location"] == sel_loc].iloc[0]
        posts = generate_social_media_post(row)

        st.markdown("**WhatsApp / Telegram**")
        st.text_area("", posts["whatsapp"], height=180, key="wa_post")

        st.markdown("**Twitter / X**")
        st.text_area("", posts["twitter"], height=100, key="tw_post")

        st.markdown("**Facebook**")
        st.text_area("", posts["facebook"], height=180, key="fb_post")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Data Sources
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔧 Data Sources":
    st.markdown('<div class="section-header">🔧 Live Data Sources & Scraper Status</div>',
                unsafe_allow_html=True)
    data_badge("live", "Scheduler telemetry from SQLite", "", None)

    counts = db_counts()
    sched  = get_status()

    # ── DB stats ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("News Articles",    counts["news"])
    c2.metric("Grievances",       counts["grievances"])
    c3.metric("Sentiment Records",counts["sentiment"])
    c4.metric("Scheduler",        "🟢 Running" if sched["running"] else "🔴 Stopped")

    st.divider()

    # ── Source table ───────────────────────────────────────────────────────────
    st.markdown("#### Connected Data Sources")
    sources = [
        ("Google News RSS",   "✅ Live",   "12 keywords · Manikonda, Neknampur, Puppalguda", "30 min",   get_last_scrape("google_news_rss") or "Pending"),
        ("Hyderabad Mail",    "✅ Live",   "hyderabadmail.com — Confirmed scrapeable",       "35 min",   get_last_scrape("news_sites") or "Pending"),
        ("Telangana Today",   "✅ Live",   "telanganatoday.com — Constituency coverage",     "35 min",   get_last_scrape("news_sites") or "Pending"),
        ("The Siasat Daily",  "✅ Live",   "siasat.com — Hyderabad civic news",              "35 min",   get_last_scrape("news_sites") or "Pending"),
        ("Reddit r/hyderabad","⚙️ Config", "Add Reddit API key in .streamlit/secrets.toml", "60 min",   get_last_scrape("reddit") or "Needs API key"),
        ("Prajavani Portal",  "⚠️ Probe",  "Attempting — may require session auth",          "120 min",  get_last_scrape("prajavani") or "Probing..."),
        ("Telugu Press (NT/Eenadu/Velugu/Sakshi)", "✅ Live", "Google News RSS filtered by Telugu source domains", "45 min", get_last_scrape("telugu_news") or "Pending"),
        ("X/Twitter (Manikonda handles)",          "✅ Live", "@ManaManikonda, @ManikondaMc, @MMRWA4, @CongressManiko1, @shrikantkovela, @Hyderabadrains via Nitter RSS", "40 min", get_last_scrape("twitter") or "Pending"),
        ("Google Form (Field Intake)",             "✅ Live", "Sheet ID configured in .streamlit/secrets.toml [google]", "10 min", get_last_scrape("google_sheets") or "Pending"),
        ("Firecrawl (JS-rendered scraping)",       "⚙️ Config" if not __import__("modules.firecrawl_client", fromlist=["is_available"]).is_available() else "✅ Live",
         "Bypasses anti-bot on news sites + scrapes @JITHUINC profile · add api_key to [firecrawl] in secrets.toml",
         "60 min", get_last_scrape("firecrawl") or "Needs API key"),
    ]
    src_df = pd.DataFrame(sources, columns=["Source","Status","Notes","Refresh","Last Run"])
    st.dataframe(src_df, use_container_width=True, hide_index=True)

    # ── Firecrawl setup instructions ──────────────────────────────────────────
    with st.expander("⚙️ How to enable Firecrawl (JS-rendered scraping for news + @JITHUINC)"):
        st.markdown("""
Firecrawl gives us **citable, real-time scrapes** from sites that block normal requests
(Eenadu, Telangana Today, Siasat, NT News, x.com). Every record carries a source URL,
which is what the Content Opportunities page requires.

**Setup (2 minutes):**
1. Go to **https://www.firecrawl.dev** → Sign up (free tier: 500 credits/mo)
2. Copy your API key (starts with `fc-...`)
3. Add to `.streamlit/secrets.toml`:

```toml
[firecrawl]
api_key = "fc-xxxxxxxxxxxxxxxxxxxxxxxxxx"
```

4. Click **⚡ Scrape Now** in the sidebar.

**What it unlocks:**
- Live local news from 6+ Telugu + English papers
- @JITHUINC profile capture (X requires JS — Firecrawl renders it)
- Auto-extracted civic grievances with verifiable source URLs
- Bypasses the anti-bot blocks that kill our direct scrapers

**Cost:** Free tier (500 credits) covers ~7 days of every-hour scraping.
Paid Hobby plan: $19/mo for 3,000 credits.
        """)

    # ── Reddit setup instructions ──────────────────────────────────────────────
    with st.expander("⚙️ How to enable Reddit scraping (free, 5 min setup)"):
        st.markdown("""
1. Go to **https://www.reddit.com/prefs/apps**
2. Click **"Create another app"** → choose **script**
3. Name it anything, redirect URI = `http://localhost:8080`
4. Copy your `client_id` (under the app name) and `client_secret`
5. Create or edit `.streamlit/secrets.toml` in the dashboard folder:

```toml
[reddit]
client_id     = "paste_your_client_id_here"
client_secret = "paste_your_client_secret_here"
user_agent    = "ConstituencyBot/1.0"
```

6. Click **⚡ Scrape Now** in the sidebar — Reddit data will appear automatically.
        """)

    # ── Prajavani status ───────────────────────────────────────────────────────
    with st.expander("⚠️ Prajavani Portal — Manual Data Entry (until API access is granted)"):
        st.markdown("""
The Prajavani portal (`prajavani.telangana.gov.in`) requires a session login
to view petition details. Until official API access is granted, you can:

1. Download your ward's pending petition CSV from the portal manually
2. Upload it here:
        """)
        uploaded = st.file_uploader("Upload Prajavani CSV export", type=["csv"])
        if uploaded:
            try:
                up_df = pd.read_csv(uploaded)
                st.dataframe(up_df.head(10), use_container_width=True)
                st.success(f"Loaded {len(up_df)} records. "
                           "Map columns below and click Import.")
            except Exception as e:
                st.error(f"Could not parse file: {e}")

    st.divider()

    # ── Scrape log ─────────────────────────────────────────────────────────────
    st.markdown("#### Scrape Activity Log")
    log_df = get_scrape_log()
    if not log_df.empty:
        st.dataframe(log_df[["source","status","records","error","ran_at"]],
                     use_container_width=True, hide_index=True, height=300)
    else:
        st.info("No scrape activity yet. Click ⚡ Scrape Now to begin.")

    # ── Manual trigger ─────────────────────────────────────────────────────────
    st.divider()
    if st.button("⚡ Run All Scrapers Now", use_container_width=True, type="primary"):
        with st.spinner("Running all scrapers... (may take 30–60 seconds)"):
            run_all_scrapers()
        st.cache_data.clear()
        st.success("All scrapers completed. Refresh dashboard to see new data.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Field Intake Form
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Content Opportunities (Jithender)":
    st.markdown(f'<div class="section-header">🎯 Content Opportunities — {CANDIDATE_NAME} ({CANDIDATE_HANDLE})</div>',
                unsafe_allow_html=True)
    st.markdown(f"*{CANDIDATE_ROLE}. Ready-to-post drafts based on live news, voter grievances, and his own posting style.*")

    news_df_all = load_news()
    own_tweets  = news_df_all[news_df_all["source"].fillna("").str.contains("@JITHUINC", case=False, na=False)] if not news_df_all.empty else pd.DataFrame()
    has_own = not own_tweets.empty

    if has_own:
        data_badge("live", f"{len(own_tweets)} of Jithender's own tweets + {len(news_df_all)} news items",
                   get_last_scrape("twitter") or "", len(own_tweets))
    else:
        data_badge("partial", "X scanner running — @JITHUINC tweets not yet captured (Nitter mirrors flaky). News + grievance data is live.",
                   get_last_scrape("twitter") or "", 0)

    # ── Voice analysis ────────────────────────────────────────────────────────
    voice = analyze_candidate_voice(news_df_all)
    st.markdown("### 🗣️ Your Current Voice Analysis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tweets analyzed", voice["tweet_count"])
    c2.metric("Cadence", voice["cadence"])
    c3.metric("Top topic", voice["topics"][0][0] if voice["topics"] else "—")
    st.info(voice["summary"])

    if has_own:
        with st.expander(f"🐦 Recent @JITHUINC tweets ({len(own_tweets)})"):
            for _, row in own_tweets.head(10).iterrows():
                st.markdown(f"""
                <div class="news-card">
                  <b>{row['title']}</b><br/>
                  <span style="font-size:11px;color:#666;">📅 {row.get('published','')} · <a href="{row['url']}" target="_blank">↗ View</a></span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── Content gap analysis ──────────────────────────────────────────────────
    st.markdown("### 🎯 Content Gaps — What voters care about but you're not posting on")
    st.caption("⚠️ Drafts are only generated from grievances with a verifiable source URL. No invented issues.")
    gaps = content_gap_recommendations(voice, df)
    if not gaps:
        st.warning("No gaps shown — either your topic mix already aligns, OR we don't have enough sourced grievances yet. "
                   "As Google Form submissions + news scraping accumulate sourced records, gaps will appear here.")
    else:
        for g in gaps:
            with st.container():
                st.markdown(f"""
                <div class="urgent-card">
                  <b>📌 Gap: {g['topic']}</b><br/>
                  <span style="font-size:13px;">{g['voter_complaints']} sourced voter grievances · 0 of your recent tweets cover this</span><br/>
                  <span style="font-size:12px;color:#555;">💡 {g['why']}</span>
                </div>
                """, unsafe_allow_html=True)
                st.text_area(f"Tweet draft · {g['topic']}", g["tweet"], height=130, key=f"gap_{g['topic']}")
                st.markdown(f"📎 **Reference:** [{g['source']['label']}]({g['source']['url']})")

    st.divider()

    # ── Top local grievance opportunities ────────────────────────────────────
    st.markdown("### 🔥 Top Sourced Local Issues — Highest Tweet Opportunity Score")
    st.caption("⚠️ Only grievances with a verifiable source URL are shown. No imagined issues.")
    top5 = rank_grievance_opportunities(df, n=5)
    if top5.empty:
        st.warning("No sourced grievances available yet. Drafts will appear here as the Google Form, "
                   "news-site scrapers, and X scanner ingest real records with URLs. "
                   "Until then, do NOT post — every claim needs a citable source.")
    else:
        for i, (_, row) in enumerate(top5.iterrows(), 1):
            with st.expander(f"#{i} · {row['location']} — {row['category']}  ·  {int(row.get('days_pending',0) or 0)}d pending · score {row.get('opportunity_score','—')}"):
                src_url   = row.get("source_url") or ""
                src_type  = row.get("source_type") or "unknown"
                reported  = row.get("reported_date") or row.get("scraped_at") or ""
                st.markdown(f"📎 **Reference:** [{src_type} · reported {str(reported)[:10]}]({src_url})")
                st.caption(f"Read the underlying report BEFORE posting. Description excerpt: _{str(row.get('description',''))[:240]}_")

                tab_a, tab_b = st.tabs(["🐦 Single tweet", "🧵 3-tweet thread"])
                with tab_a:
                    out = grievance_to_tweet(row)
                    st.text_area("Tweet draft", out["tweet"], height=140, key=f"gtw_{i}")
                    st.caption(f"Length: {len(out['tweet'])} chars · post as @JITHUINC")
                with tab_b:
                    out = grievance_to_thread(row, CANDIDATE_NAME)
                    for j, t in enumerate(out["thread"], 1):
                        st.text_area(f"Tweet {j}/3", t, height=120, key=f"gth_{i}_{j}")

    st.divider()

    # ── News reaction opportunities ──────────────────────────────────────────
    st.markdown("### 📰 React to Trending News — Posts in Voters' Feeds Right Now")
    st.caption("⚠️ Every draft references the actual article URL. Read the article before posting.")
    if news_df_all.empty:
        st.info("News scraping in progress.")
    else:
        reactable = news_df_all[~news_df_all["source"].fillna("").str.contains("@JITHUINC", case=False, na=False)]
        hot_news  = rank_news_opportunities(reactable, n=5)
        if hot_news.empty:
            st.warning("No articles with verifiable URLs yet. Click ⚡ Scrape Now in the sidebar.")
        else:
            for i, (_, row) in enumerate(hot_news.iterrows(), 1):
                sent_color = {"Angry / Frustrated": COLORS["danger"], "Hopeful": COLORS["success"]}.get(row.get("sentiment"), COLORS["neutral"])
                st.markdown(f"""
                <div class="news-card" style="border-left-color:{sent_color};">
                  <b>{row.get('title','')}</b><br/>
                  <span style="font-size:11px;color:#666;">📰 {row.get('source','')} · 📅 {row.get('published','')} · sentiment: {row.get('sentiment','')}</span>
                </div>
                """, unsafe_allow_html=True)
                out = news_to_reaction_tweet(row, CANDIDATE_NAME)
                st.text_area("Reaction tweet draft", out["tweet"], height=140, key=f"react_{i}")
                st.markdown(f"📎 **Reference:** [{out['source']['label']}]({out['source']['url']})")

    st.divider()
    st.markdown("### 📅 Weekly Posting Playbook")
    st.markdown("""
    **Mon** — Local grievance highlight (use #1 above) + tag the right agency
    **Tue** — Field-visit photo + 3-tweet thread (use thread tab)
    **Wed** — React to one trending news item (use reaction tweets above)
    **Thu** — BRS-vs-Congress contrast post (pull a "BRS-era" headline from the Tracker page)
    **Fri** — Voter quote of the week (from Voter Sentiment page) + commitment to action
    **Sat** — Constituency walk recap (Smart Outreach → Field Visit Plan)
    **Sun** — Weekly accountability scorecard: "X issues raised, Y escalated to DC, Z resolved"
    """)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Field Intake Form
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Field Intake Form":
    st.markdown('<div class="section-header">📋 Field Grievance Intake</div>', unsafe_allow_html=True)
    data_badge("live", "Submissions write directly into SQLite + Google Form pipeline", "", None)

    tab_form, tab_setup, tab_responses = st.tabs([
        "📝 Submit Grievance",
        "⚙️ Google Form Setup",
        "📊 View Responses",
    ])

    # ── Tab 1: Direct Streamlit intake form ───────────────────────────────────
    with tab_form:
        st.markdown("#### Submit a Grievance Directly")
        st.caption("For desktop submission by the candidate or volunteers. "
                   "For field workers on phones, use the Google Form (Setup tab).")

        with st.form("grievance_intake", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                reporter_name  = st.text_input("Your Name (optional)")
                reporter_phone = st.text_input("Phone Number (optional)")
            with col2:
                location = st.selectbox("Location *", LOCATIONS)
                custom_loc = st.text_input("Custom location (if 'Other')")

            ward = st.text_input("Ward Number (optional)", placeholder="e.g. 127")

            col3, col4 = st.columns(2)
            with col3:
                cat_label = st.selectbox(
                    "Grievance Category (CPGRAMS) *",
                    list(CPGRAMS_CATEGORIES.values())
                )
            with col4:
                civic_sub = st.selectbox(
                    "Civic Sub-category (if applicable)",
                    ["— Not applicable —"] + CIVIC_SUBCATEGORIES
                )

            description = st.text_area(
                "Issue Description *",
                placeholder="Describe the problem: How long? How many households? Previous complaints?",
                height=130,
            )

            col5, col6 = st.columns(2)
            with col5:
                families = st.number_input("Families Affected (approx.)", min_value=0, value=0)
            with col6:
                urgency = st.selectbox("Urgency Level *", URGENCY_LEVELS)

            evidence_link = st.text_input(
                "Photo / Evidence Link (optional)",
                placeholder="Google Drive / WhatsApp photo link"
            )
            prev_ref = st.text_input(
                "Previous Complaint Reference (optional)",
                placeholder="CPGRAMS / GHMC 311 / HMWSSB reference number"
            )

            submitted = st.form_submit_button("📤 Submit Grievance", type="primary",
                                              use_container_width=True)

        if submitted:
            if not description or len(description.strip()) < 10:
                st.error("Please provide a description of at least 10 characters.")
            else:
                from modules.database import upsert_grievances, init_db
                from modules.grievance_engine import enrich_grievances
                from modules.form_config import AGENCY_MAP
                from datetime import datetime

                init_db()
                loc = custom_loc.strip() if "Other" in location and custom_loc else location
                cat_code = {v: k for k, v in CPGRAMS_CATEGORIES.items()}.get(cat_label, "002")
                sub = civic_sub if civic_sub != "— Not applicable —" else ""
                cat_display = sub if sub and cat_code == "002" else cat_label
                today = datetime.today().strftime("%Y-%m-%d")

                tier = ("CRITICAL"  if "Critical" in urgency else
                        "POLITICAL" if "High"     in urgency else
                        "URGENT"    if "Medium"   in urgency else "MONITOR")

                g = {
                    "location":          loc,
                    "lat":               17.4065,
                    "lon":               78.3772,
                    "category":          cat_display,
                    "description":       (f"[{sub}] " if sub else "") + description,
                    "reported_date":     today,
                    "status":            "Pending",
                    "era":               "Congress Era (2024–Present)",
                    "families_affected": int(families),
                    "petition_no":       f"FIELD-{today[:7].replace('-','')}-{abs(hash(description))%9999:04d}",
                    "agency":            AGENCY_MAP.get(cat_code, "GHMC"),
                    "source_url":        evidence_link,
                    "source_type":       "direct_intake",
                    "days_pending":      0,
                    "escalation_tier":   tier,
                    "opportunity_score": 20 + (int(families) / 10),
                }
                n = upsert_grievances([g])
                st.cache_data.clear()
                st.success(f"✅ Grievance submitted! Reference: {g['petition_no']}")
                st.info(f"**Category:** {cat_display}  |  **Agency:** {g['agency']}  |  **Tier:** {tier}")

    # ── Tab 2: Google Form setup guide ─────────────────────────────────────────
    with tab_setup:
        st.markdown("#### Google Form Setup — One-Time, 5 Minutes")
        st.markdown(
            "This creates a **phone-friendly Google Form** your ward volunteers "
            "can fill from WhatsApp without any app or login."
        )

        with st.expander("📋 Step 1 — Run the Apps Script (creates Form + Sheet automatically)", expanded=True):
            st.markdown("""
1. Open **[Google Apps Script](https://script.google.com)** → click **New Project**
2. Delete the default code. Paste the contents of `create_form.gs` (in the dashboard folder)
3. Click **▶ Run** → select function `createGrievanceForm`
4. Grant permissions when prompted (Google needs access to Forms + Sheets)
5. Click **Execution log** — copy the **Form URL** and **Sheet ID** shown
""")
            with open(os.path.join(os.path.dirname(__file__), "create_form.gs")) as f:
                gs_code = f.read()
            st.code(gs_code[:800] + "\n... (truncated — open create_form.gs for full code)", language="javascript")
            st.download_button("📥 Download create_form.gs", gs_code, "create_form.gs",
                               use_container_width=True)

        with st.expander("🔑 Step 2 — Get a Google API Key (2 minutes)"):
            st.markdown("""
1. Go to **[Google Cloud Console](https://console.cloud.google.com)**
2. Create a project (or use existing) → **APIs & Services → Enable APIs**
3. Enable **Google Sheets API**
4. **Credentials → Create Credentials → API Key**
5. Copy the key
6. Restrict it: **API restrictions → Google Sheets API**
""")

        with st.expander("⚙️ Step 3 — Add to secrets.toml"):
            st.markdown("Create or edit `.streamlit/secrets.toml` in the dashboard folder:")
            st.code("""
[google]
sheet_id = "paste_your_sheet_id_here"
api_key  = "paste_your_api_key_here"
""", language="toml")
            st.info("After saving, click **🔄 Reload Dashboard** in the sidebar.")

        with st.expander("📱 Step 4 — Share the form with volunteers"):
            st.markdown("""
Once the form is created, copy its **short URL** from the Apps Script log.

**Share via WhatsApp:**
```
📋 Grievance Report Form — Manikonda / Neknampur
Fill this form to report any civic issue (water, roads,
power, drainage, encroachment) in our constituency.
Takes 2 minutes. No login needed.

👉 [paste form short URL here]

Your report goes directly to our People's Representative.
🙏 Thank you!
```

**Set a reminder** — send this message to all ward WhatsApp groups every Monday morning.
""")

        # Check current connection status
        st.divider()
        st.markdown("**Current Connection Status:**")
        try:
            import streamlit as st2
            cfg = st2.secrets.get("google", {})
            if cfg.get("sheet_id"):
                st.success(f"✅ Connected to Sheet ID: `{cfg['sheet_id'][:20]}...`")
                raw = fetch_sheet_responses()
                st.metric("Responses in Sheet", len(raw))
            else:
                st.warning("⚠️ Not connected — complete Steps 1–3 above.")
        except Exception:
            st.warning("⚠️ Not connected — complete Steps 1–3 above.")

    # ── Tab 3: View responses ──────────────────────────────────────────────────
    with tab_responses:
        st.markdown("#### Google Form Responses")
        try:
            raw = fetch_sheet_responses()
            if raw.empty:
                st.info("No responses yet, or Google Sheets not connected. "
                        "Complete setup in the ⚙️ Setup tab.")
            else:
                st.metric("Total Responses", len(raw))
                st.dataframe(raw, use_container_width=True, height=400)

                grievances = transform_responses(raw)
                if grievances:
                    gdf = pd.DataFrame(grievances)
                    st.divider()
                    st.markdown("#### Auto-classified Grievances")
                    display_cols = ["location", "category", "description",
                                    "families_affected", "urgency_level" if "urgency_level" in gdf.columns else "days_pending",
                                    "escalation_tier", "opportunity_score"]
                    available = [c for c in display_cols if c in gdf.columns]
                    st.dataframe(gdf[available], use_container_width=True)

                    st.download_button(
                        "📥 Download as CSV",
                        gdf.to_csv(index=False),
                        file_name="form_grievances.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
        except Exception as e:
            st.error(f"Could not load responses: {e}")


# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
last_rss = get_last_scrape("google_news_rss")
last_str  = f"Last scraped: {last_rss[:16]}" if last_rss else "Scraping..."
st.markdown(
    f"<center><small>🗳️ {CONSTITUENCY} Accountability Dashboard &nbsp;|&nbsp; "
    f"Powered by Streamlit + Plotly + Folium &nbsp;|&nbsp; "
    f"🔴 Live &nbsp;|&nbsp; {last_str} &nbsp;|&nbsp; "
    f"Auto-refresh: every 30 min</small></center>",
    unsafe_allow_html=True,
)
