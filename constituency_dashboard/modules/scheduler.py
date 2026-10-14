"""
Background scheduler — runs all scrapers automatically every 30 minutes.
Uses APScheduler with a thread pool executor so it doesn't block Streamlit.

Call start_scheduler() once at app boot; it's safe to call multiple times
(subsequent calls are no-ops if the scheduler is already running).
"""

import threading
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from modules.database import (
    init_db, upsert_articles, upsert_grievances, upsert_sentiment,
    log_scrape, db_counts,
)
from modules.grievance_engine import enrich_grievances
from modules.data_ingestion import classify_sentiment

import pandas as pd

log = logging.getLogger(__name__)
_scheduler = None  # type: BackgroundScheduler
_lock = threading.Lock()

REFRESH_MINUTES = 30


# ── Individual scrape jobs ────────────────────────────────────────────────────

def _job_news_rss():
    try:
        from modules.scrapers.news_rss import scrape_all
        articles = scrape_all()
        n = upsert_articles(articles)

        # Convert news articles into sentiment records
        sentiment_records = [
            {
                "text":      a["title"] + ". " + a.get("summary", ""),
                "location":  _infer_location(a["keyword"] + " " + a["title"]),
                "lat":       17.4065,
                "lon":       78.3772,
                "sentiment": a["sentiment"],
                "source":    a["source"],
            }
            for a in articles if a.get("title")
        ]
        upsert_sentiment(sentiment_records)
        log_scrape("google_news_rss", "ok", n)
        log.info(f"[RSS] +{n} new articles")
    except Exception as e:
        log_scrape("google_news_rss", "error", 0, str(e))
        log.error(f"[RSS] {e}")


def _job_news_sites():
    try:
        from modules.scrapers.news_sites import scrape_all_sites
        news, grievances = scrape_all_sites()

        n_news = upsert_articles(news)

        # Enrich grievances before inserting
        if grievances:
            gdf = pd.DataFrame(grievances)
            gdf["status"] = "Pending"
            gdf["era"]    = gdf.get("era", "Congress Era (2024–Present)")
            gdf["petition_no"] = ""
            enriched = enrich_grievances(gdf)
            g_dicts = enriched.to_dict("records")
            n_griev = upsert_grievances(g_dicts)
        else:
            n_griev = 0

        log_scrape("news_sites", "ok", n_news + n_griev)
        log.info(f"[Sites] +{n_news} news, +{n_griev} grievances")
    except Exception as e:
        log_scrape("news_sites", "error", 0, str(e))
        log.error(f"[Sites] {e}")


def _job_reddit():
    try:
        from modules.scrapers.reddit_scraper import scrape_reddit
        news, grievances = scrape_reddit()
        n_news = upsert_articles(news)
        if grievances:
            gdf = pd.DataFrame(grievances)
            gdf["status"] = "Pending"
            gdf["petition_no"] = ""
            enriched = enrich_grievances(gdf)
            n_griev = upsert_grievances(enriched.to_dict("records"))
        else:
            n_griev = 0
        log_scrape("reddit", "ok", n_news + n_griev)
        log.info(f"[Reddit] +{n_news} news, +{n_griev} grievances")
    except Exception as e:
        log_scrape("reddit", "error", 0, str(e))
        log.error(f"[Reddit] {e}")


def _job_prajavani():
    try:
        from modules.scrapers.prajavani import scrape_prajavani
        grievances = scrape_prajavani()
        if grievances:
            gdf = pd.DataFrame(grievances)
            gdf["status"] = "Pending"
            enriched = enrich_grievances(gdf)
            n = upsert_grievances(enriched.to_dict("records"))
            log_scrape("prajavani", "ok", n)
            log.info(f"[Prajavani] +{n} grievances")
        else:
            log_scrape("prajavani", "ok", 0)
            log.info("[Prajavani] Portal returned no data (may require auth)")
    except Exception as e:
        log_scrape("prajavani", "error", 0, str(e))
        log.error(f"[Prajavani] {e}")


def _infer_location(text: str) -> str:
    LOCS = ["Manikonda", "Neknampur", "Puppalguda", "Lanco Hills",
            "Khajaguda", "Nallagandla"]
    lower = text.lower()
    for loc in LOCS:
        if loc.lower() in lower:
            return loc
    return "Manikonda"


def _job_firecrawl():
    """Firecrawl-powered news + grievance scraper + @JITHUINC profile."""
    try:
        from modules.scrapers.firecrawl_news import (
            scrape_firecrawl_news, scrape_jithender_profile, is_available
        )
        if not is_available():
            log_scrape("firecrawl", "skip", 0, "API key not configured")
            return

        articles, griev = scrape_firecrawl_news()
        n_news = upsert_articles(articles)

        if griev:
            gdf = pd.DataFrame(griev)
            gdf["status"] = "Pending"
            gdf["era"]    = "Congress Era (2024–Present)"
            gdf["petition_no"] = ""
            enriched = enrich_grievances(gdf)
            n_griev = upsert_grievances(enriched.to_dict("records"))
        else:
            n_griev = 0

        tweets = scrape_jithender_profile()
        n_tw   = upsert_articles(tweets)

        log_scrape("firecrawl", "ok", n_news + n_griev + n_tw)
        log.info(f"[Firecrawl] +{n_news} news, +{n_griev} grievances, +{n_tw} @JITHUINC tweets")
    except Exception as e:
        log_scrape("firecrawl", "error", 0, str(e))
        log.error(f"[Firecrawl] {e}")


def _job_brs_congress():
    """Live news for the BRS-vs-Congress accountability page."""
    try:
        from modules.scrapers.brs_congress_live import scrape_brs_congress
        brs, cong = scrape_brs_congress()
        all_items = brs + cong
        n = upsert_articles(all_items)
        log_scrape("brs_congress", "ok", n)
        log.info(f"[BRS/Congress] +{n} articles ({len(brs)} BRS, {len(cong)} Congress)")
    except Exception as e:
        log_scrape("brs_congress", "error", 0, str(e))
        log.error(f"[BRS/Congress] {e}")


def _job_telugu_news():
    try:
        from modules.scrapers.telugu_news import scrape_telugu_news
        articles = scrape_telugu_news()
        n = upsert_articles(articles)
        sentiment_records = [
            {
                "text":      a["title"] + ". " + a.get("summary", ""),
                "location":  _infer_location(a["keyword"] + " " + a["title"]),
                "lat":       17.4065,
                "lon":       78.3772,
                "sentiment": a["sentiment"],
                "source":    a["source"],
            }
            for a in articles if a.get("title")
        ]
        upsert_sentiment(sentiment_records)
        log_scrape("telugu_news", "ok", n)
        log.info(f"[Telugu] +{n} articles")
    except Exception as e:
        log_scrape("telugu_news", "error", 0, str(e))
        log.error(f"[Telugu] {e}")


def _job_twitter():
    try:
        from modules.scrapers.twitter_scanner import scrape_twitter
        tweets = scrape_twitter()
        n = upsert_articles(tweets)
        sentiment_records = [
            {
                "text":      t["title"],
                "location":  _infer_location(t["title"] + " " + t.get("summary", "")),
                "lat":       17.4065,
                "lon":       78.3772,
                "sentiment": t["sentiment"],
                "source":    t["source"],
            }
            for t in tweets if t.get("title")
        ]
        upsert_sentiment(sentiment_records)
        log_scrape("twitter", "ok", n)
        log.info(f"[Twitter/X] +{n} tweets")
    except Exception as e:
        log_scrape("twitter", "error", 0, str(e))
        log.error(f"[Twitter/X] {e}")


def _job_google_sheets():
    """Sync Google Form responses into the grievance DB."""
    try:
        from modules.google_sheets import fetch_sheet_responses, transform_responses
        raw = fetch_sheet_responses()
        if raw.empty:
            log_scrape("google_sheets", "ok", 0)
            return
        grievances = transform_responses(raw)
        n = upsert_grievances(grievances)
        log_scrape("google_sheets", "ok", n)
        log.info(f"[Sheets] +{n} grievances from Google Form")
    except Exception as e:
        log_scrape("google_sheets", "error", 0, str(e))
        log.error(f"[Sheets] {e}")


def run_all_scrapers():
    """Run every scraper immediately (blocking). Called for manual refresh."""
    _job_news_rss()
    _job_news_sites()
    _job_reddit()
    _job_prajavani()
    _job_telugu_news()
    _job_twitter()
    _job_brs_congress()
    _job_firecrawl()
    _job_google_sheets()


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def start_scheduler():
    """
    Start the background scheduler. Safe to call multiple times —
    only one instance runs per process.
    """
    global _scheduler
    with _lock:
        if _scheduler and _scheduler.running:
            return

        init_db()

        # Run immediately on first start
        _first_run = threading.Thread(target=run_all_scrapers, daemon=True)
        _first_run.start()

        _scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1}
        )
        _scheduler.add_job(
            _job_news_rss,
            trigger=IntervalTrigger(minutes=REFRESH_MINUTES),
            id="news_rss", replace_existing=True,
        )
        _scheduler.add_job(
            _job_news_sites,
            trigger=IntervalTrigger(minutes=REFRESH_MINUTES + 5),
            id="news_sites", replace_existing=True,
        )
        _scheduler.add_job(
            _job_reddit,
            trigger=IntervalTrigger(minutes=60),
            id="reddit", replace_existing=True,
        )
        _scheduler.add_job(
            _job_prajavani,
            trigger=IntervalTrigger(minutes=120),
            id="prajavani", replace_existing=True,
        )
        _scheduler.add_job(
            _job_telugu_news,
            trigger=IntervalTrigger(minutes=45),
            id="telugu_news", replace_existing=True,
        )
        _scheduler.add_job(
            _job_twitter,
            trigger=IntervalTrigger(minutes=40),
            id="twitter", replace_existing=True,
        )
        _scheduler.add_job(
            _job_brs_congress,
            trigger=IntervalTrigger(minutes=90),
            id="brs_congress", replace_existing=True,
        )
        _scheduler.add_job(
            _job_firecrawl,
            trigger=IntervalTrigger(minutes=60),
            id="firecrawl", replace_existing=True,
        )
        _scheduler.add_job(
            _job_google_sheets,
            trigger=IntervalTrigger(minutes=10),
            id="google_sheets", replace_existing=True,
        )
        _scheduler.start()
        log.info(f"Scheduler started — refresh every {REFRESH_MINUTES} min")


def get_status() -> dict:
    return {
        "running":    _scheduler.running if _scheduler else False,
        "next_run":   str(_scheduler.get_job("news_rss").next_run_time) if _scheduler else "—",
        "db_counts":  db_counts(),
    }
