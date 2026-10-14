"""
Visualization Layer
- Folium heatmap: Voter Pain clusters
- Plotly: Grievance aging time-series, category breakdown, BRS vs Congress
- Sentiment donut chart
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
from folium.plugins import HeatMap, MarkerCluster
from typing import Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MAP_CENTER, MAP_ZOOM, COLORS, ERA_BRS, ERA_CONGRESS

# Shared layout defaults — explicit white background, dark text for all charts
_LAYOUT_BASE = dict(
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    font=dict(family="Inter, sans-serif", size=12, color="#1A1A2E"),
    title_font=dict(size=15, color="#1E3A5F", family="Inter, sans-serif"),
)


# ── Folium Voter-Pain Heatmap ─────────────────────────────────────────────────

def build_heatmap(df: pd.DataFrame) -> folium.Map:
    """
    Weighted heatmap: intensity = opportunity_score.
    Markers show top-10 issues with popup details.
    """
    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="CartoDB positron",
    )

    # Heatmap layer — weight by opportunity score
    heat_data = [
        [row["lat"], row["lon"], row["opportunity_score"] / 100]
        for _, row in df.iterrows()
    ]
    HeatMap(
        heat_data,
        min_opacity=0.4,
        max_zoom=17,
        radius=25,
        blur=20,
        gradient={0.2: "blue", 0.5: "orange", 0.8: "red"},
    ).add_to(m)

    # Marker cluster for top issues
    cluster = MarkerCluster(name="Grievance Hotspots").add_to(m)
    tier_colors = {"CRITICAL": "red", "POLITICAL": "orange", "URGENT": "beige", "MONITOR": "green"}

    for _, row in df.iterrows():
        color = tier_colors.get(row.get("escalation_tier", "MONITOR"), "blue")
        popup_html = f"""
        <div style='font-family:sans-serif;width:220px'>
          <b style='color:{COLORS["primary"]}'>{row['location']}</b><br/>
          <span style='color:gray;font-size:11px'>{row['category']}</span><br/>
          <hr style='margin:4px 0'/>
          <b>Pending:</b> {row['days_pending']} days<br/>
          <b>Families:</b> {row['families_affected']}<br/>
          <b>Petition:</b> {row['petition_no']}<br/>
          <b>Tier:</b> <span style='color:{COLORS["danger"]}'>{row.get('escalation_tier','—')}</span><br/>
          <b>Score:</b> {row.get('opportunity_score',0)}/100
        </div>"""
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"⚠ {row['location']} — {row['days_pending']}d pending",
            icon=folium.Icon(color=color, icon="exclamation-sign", prefix="glyphicon"),
        ).add_to(cluster)

    folium.LayerControl().add_to(m)
    return m


def build_sentiment_map(sentiment_df: pd.DataFrame) -> folium.Map:
    """Small map showing voter sentiment by location."""
    m = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM, tiles="CartoDB positron")
    color_map = {
        "Angry / Frustrated": "red",
        "Neutral":            "gray",
        "Hopeful":            "green",
    }
    for _, row in sentiment_df.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=10,
            color=color_map.get(row["sentiment"], "blue"),
            fill=True,
            fill_opacity=0.7,
            tooltip=f"{row['location']}: {row['sentiment']}",
            popup=folium.Popup(
                f"<b>{row['location']}</b><br/><i>\"{row['text'][:80]}...\"</i>",
                max_width=220
            ),
        ).add_to(m)
    return m


# ── Plotly Charts ─────────────────────────────────────────────────────────────

def grievance_aging_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar — each grievance, colored by escalation tier."""
    color_map = {
        "CRITICAL":  COLORS["danger"],
        "POLITICAL": COLORS["accent"],
        "URGENT":    COLORS["warning"],
        "MONITOR":   COLORS["neutral"],
    }
    df_sorted = df.sort_values("days_pending", ascending=True)
    colors = [color_map.get(t, COLORS["neutral"]) for t in df_sorted["escalation_tier"]]

    fig = go.Figure(go.Bar(
        x=df_sorted["days_pending"],
        y=df_sorted["location"],
        orientation="h",
        marker_color=colors,
        text=df_sorted["days_pending"].astype(str) + "d",
        textposition="outside",
        textfont=dict(color="#1A1A2E", size=11),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Days Pending: %{x}<br>"
            "Category: " + df_sorted["category"].astype(str) + "<extra></extra>"
        ),
    ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title="Grievance Aging — Days Since Reported",
        xaxis=dict(title="Days Pending", gridcolor="#E8ECF0", color="#1A1A2E"),
        yaxis=dict(title="", gridcolor="#E8ECF0", color="#1A1A2E", tickfont=dict(size=12)),
        height=520,
        margin=dict(l=170, r=80, t=60, b=40),
        shapes=[
            dict(type="line", x0=30, x1=30, y0=-0.5,
                 y1=len(df)-0.5, line=dict(color=COLORS["accent"], width=2, dash="dot")),
            dict(type="line", x0=60, x1=60, y0=-0.5,
                 y1=len(df)-0.5, line=dict(color=COLORS["danger"], width=2, dash="dot")),
        ],
        annotations=[
            dict(x=30, y=len(df)-0.5, text="30d", showarrow=False,
                 font=dict(color=COLORS["accent"], size=10, family="sans-serif")),
            dict(x=60, y=len(df)-0.5, text="60d critical", showarrow=False,
                 font=dict(color=COLORS["danger"], size=10, family="sans-serif")),
        ],
    )
    return fig


def category_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart — grievance count by category."""
    counts = df["category"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.55,
        marker_colors=px.colors.qualitative.Bold,
        textinfo="label+percent",
        textfont=dict(size=11, color="#1A1A2E"),
        hovertemplate="%{label}<br>Count: %{value}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title="Issues by Category",
        showlegend=False,
        height=380,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def sentiment_donut(summary: Dict[str, int]) -> go.Figure:
    labels = list(summary.keys())
    values = list(summary.values())
    colors = [COLORS["danger"], COLORS["neutral"], COLORS["success"]]
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color="#1A1A2E"),
        insidetextorientation="radial",
    ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title="Voter Sentiment — Congress Administration",
        height=380,
        legend=dict(
            orientation="v",
            x=0.75, y=0.5,
            font=dict(size=12, color="#1A1A2E"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#DDDDDD",
            borderwidth=1,
        ),
        margin=dict(l=20, r=20, t=55, b=20),
    )
    return fig


def brs_vs_congress_chart(brs_df: pd.DataFrame, congress_df: pd.DataFrame) -> go.Figure:
    """Side-by-side grouped bar comparing project counts and completion."""
    brs_pct = brs_df["completion"].str.replace("%", "").str.strip()
    brs_pct = pd.to_numeric(brs_pct, errors="coerce").fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="BRS Unfinished Projects",
        x=brs_df["project"],
        y=brs_pct,
        marker_color=COLORS["brs"],
        text=brs_df["completion"],
        textposition="outside",
        textfont=dict(size=11, color="#1A1A2E"),
    ))
    status_score = congress_df["status"].map(
        {"Planning": 10, "In Progress": 50, "Completed": 100, "Ongoing": 70}
    ).fillna(30)
    fig.add_trace(go.Bar(
        name="Congress Interventions (Progress %)",
        x=congress_df["initiative"],
        y=status_score,
        marker_color=COLORS["congress"],
        text=congress_df["status"],
        textposition="outside",
        textfont=dict(size=11, color="#1A1A2E"),
    ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title="BRS Unfinished Projects vs. Congress Interventions",
        barmode="group",
        yaxis=dict(title="Completion / Progress %", gridcolor="#E8ECF0", color="#1A1A2E"),
        xaxis=dict(tickangle=-30, tickfont=dict(size=10, color="#1A1A2E")),
        height=460,
        legend=dict(orientation="h", y=-0.3, font=dict(size=12, color="#1A1A2E")),
        margin=dict(l=50, r=40, t=65, b=140),
    )
    return fig


def opportunity_score_scatter(df: pd.DataFrame) -> go.Figure:
    """Bubble chart: X=days_pending, Y=families_affected, size=opportunity_score."""
    tier_color = {
        "CRITICAL":  COLORS["danger"],
        "POLITICAL": COLORS["accent"],
        "URGENT":    COLORS["warning"],
        "MONITOR":   COLORS["neutral"],
    }
    fig = go.Figure()
    for tier, grp in df.groupby("escalation_tier"):
        fig.add_trace(go.Scatter(
            x=grp["days_pending"],
            y=grp["families_affected"],
            mode="markers+text",
            name=tier,
            text=grp["location"],
            textposition="top center",
            textfont=dict(size=10, color="#1A1A2E"),
            marker=dict(
                size=grp["opportunity_score"] / 3,
                color=tier_color.get(tier, "gray"),
                opacity=0.80,
                line=dict(width=2, color="white"),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Days: %{x} | Families: %{y}<br>"
                "Score: " + grp["opportunity_score"].astype(str) + "<extra></extra>"
            ),
        ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title="Political Opportunity Matrix — Bubble Size = Opportunity Score",
        xaxis=dict(title="Days Pending  →", gridcolor="#E8ECF0", color="#1A1A2E"),
        yaxis=dict(title="Families Affected", gridcolor="#E8ECF0", color="#1A1A2E"),
        height=460,
        legend=dict(orientation="h", y=-0.2, font=dict(size=12, color="#1A1A2E")),
    )
    return fig
