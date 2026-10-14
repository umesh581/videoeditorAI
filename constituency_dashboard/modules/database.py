"""
SQLite persistence layer.
Tables: news_articles, grievances, scrape_log, sentiment_records
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "constituency.db")


def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Create tables if they don't exist."""
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            source      TEXT,
            url         TEXT UNIQUE,
            published   TEXT,
            keyword     TEXT,
            sentiment   TEXT,
            summary     TEXT,
            scraped_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS grievances (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            location          TEXT NOT NULL,
            lat               REAL,
            lon               REAL,
            category          TEXT,
            description       TEXT,
            reported_date     TEXT,
            status            TEXT DEFAULT 'Pending',
            era               TEXT,
            families_affected INTEGER DEFAULT 0,
            petition_no       TEXT,
            agency            TEXT,
            source_url        TEXT,
            source_type       TEXT DEFAULT 'scraped',
            days_pending      INTEGER,
            escalation_tier   TEXT,
            opportunity_score REAL,
            scraped_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sentiment_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT NOT NULL,
            location    TEXT,
            lat         REAL,
            lon         REAL,
            sentiment   TEXT,
            source      TEXT,
            scraped_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scrape_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            status      TEXT,
            records     INTEGER DEFAULT 0,
            error       TEXT,
            ran_at      TEXT DEFAULT (datetime('now'))
        );
        """)


# ── News ──────────────────────────────────────────────────────────────────────

def upsert_articles(articles: list[dict]) -> int:
    """Insert new articles, skip duplicates by URL. Returns inserted count."""
    inserted = 0
    with _conn() as con:
        for a in articles:
            try:
                con.execute("""
                    INSERT OR IGNORE INTO news_articles
                        (title, source, url, published, keyword, sentiment, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    a.get("title", ""),
                    a.get("source", ""),
                    a.get("url", ""),
                    a.get("published", ""),
                    a.get("keyword", ""),
                    a.get("sentiment", ""),
                    a.get("summary", ""),
                ))
                if con.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
            except Exception:
                pass
    return inserted


def get_articles(limit: int = 100) -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql(
            "SELECT * FROM news_articles ORDER BY scraped_at DESC LIMIT ?",
            con, params=(limit,)
        )
    return df


# ── Grievances ────────────────────────────────────────────────────────────────

def upsert_grievances(grievances: list[dict]) -> int:
    inserted = 0
    with _conn() as con:
        for g in grievances:
            try:
                con.execute("""
                    INSERT OR IGNORE INTO grievances
                        (location, lat, lon, category, description, reported_date,
                         status, era, families_affected, petition_no, agency,
                         source_url, source_type, days_pending, escalation_tier,
                         opportunity_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    g.get("location", ""),
                    g.get("lat", 17.4065),
                    g.get("lon", 78.3772),
                    g.get("category", ""),
                    g.get("description", ""),
                    g.get("reported_date", datetime.today().strftime("%Y-%m-%d")),
                    g.get("status", "Pending"),
                    g.get("era", "Congress Era (2024–Present)"),
                    g.get("families_affected", 0),
                    g.get("petition_no", ""),
                    g.get("agency", ""),
                    g.get("source_url", ""),
                    g.get("source_type", "scraped"),
                    g.get("days_pending", 0),
                    g.get("escalation_tier", "MONITOR"),
                    g.get("opportunity_score", 0.0),
                ))
                if con.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
            except Exception:
                pass
    return inserted


def get_grievances_db() -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql(
            "SELECT * FROM grievances ORDER BY opportunity_score DESC",
            con
        )
    if not df.empty:
        df["reported_date"] = pd.to_datetime(df["reported_date"], errors="coerce")
    return df


# ── Sentiment ─────────────────────────────────────────────────────────────────

def upsert_sentiment(records: list[dict]) -> int:
    inserted = 0
    with _conn() as con:
        for r in records:
            try:
                con.execute("""
                    INSERT INTO sentiment_records (text, location, lat, lon, sentiment, source)
                    SELECT ?, ?, ?, ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM sentiment_records WHERE text = ?
                    )
                """, (
                    r.get("text", ""), r.get("location", ""),
                    r.get("lat", 17.4065), r.get("lon", 78.3772),
                    r.get("sentiment", ""), r.get("source", "scraped"),
                    r.get("text", ""),
                ))
                if con.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
            except Exception:
                pass
    return inserted


def get_sentiment_db() -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql(
            "SELECT * FROM sentiment_records ORDER BY scraped_at DESC LIMIT 50",
            con
        )
    return df


# ── Scrape log ────────────────────────────────────────────────────────────────

def log_scrape(source: str, status: str, records: int = 0, error: str = ""):
    with _conn() as con:
        con.execute(
            "INSERT INTO scrape_log (source, status, records, error) VALUES (?, ?, ?, ?)",
            (source, status, records, error)
        )


def get_last_scrape(source: str):
    with _conn() as con:
        row = con.execute(
            "SELECT ran_at FROM scrape_log WHERE source=? AND status='ok' ORDER BY ran_at DESC LIMIT 1",
            (source,)
        ).fetchone()
    return row[0] if row else None


def get_scrape_log() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM scrape_log ORDER BY ran_at DESC LIMIT 30", con
        )


def db_counts() -> dict:
    with _conn() as con:
        return {
            "news":        con.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0],
            "grievances":  con.execute("SELECT COUNT(*) FROM grievances").fetchone()[0],
            "sentiment":   con.execute("SELECT COUNT(*) FROM sentiment_records").fetchone()[0],
        }
