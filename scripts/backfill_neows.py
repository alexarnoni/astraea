"""
Standalone backfill script for NASA NeoWs historical data.

Fetches 12 months of Near-Earth Object data from NASA's NeoWs API
in 7-day windows and inserts records into raw.neo_feeds.
"""

import json
import logging
import os
import sys
import time
from datetime import date, timedelta

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")
NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
NEOWS_URL = "https://api.nasa.gov/neo/rest/v1/feed"
REQUEST_TIMEOUT = 30
WINDOW_DAYS = 7
BACKFILL_DAYS = 365
RATE_LIMIT_DELAY = 1.0

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set. Exiting.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def generate_windows(
    start_date: date, end_date: date, step_days: int = 7
) -> list[tuple[date, date]]:
    """
    Generate contiguous date windows covering [start_date, end_date].

    Each window spans exactly `step_days` calendar days (inclusive on both ends),
    so window_end = window_start + timedelta(days=step_days - 1).

    The last window is clamped: if window_start + step_days - 1 > end_date,
    then window_end = end_date.
    """
    windows: list[tuple[date, date]] = []
    current = start_date
    while current <= end_date:
        window_end = current + timedelta(days=step_days - 1)
        if window_end > end_date:
            window_end = end_date
        windows.append((current, window_end))
        current = window_end + timedelta(days=1)
    return windows


def extract_records(response_json: dict) -> list[dict]:
    """
    Transform NeoWs API response into flat list of record dicts.

    Each record: {"neo_id", "name", "raw_data", "feed_date"}.
    """
    records: list[dict] = []
    neo_by_date = response_json.get("near_earth_objects", {})
    for date_key, objects in neo_by_date.items():
        for obj in objects:
            records.append(
                {
                    "neo_id": obj["id"],
                    "name": obj["name"],
                    "raw_data": json.dumps(obj),
                    "feed_date": date_key,
                }
            )
    return records


def process_window(
    session, client: httpx.Client, window_start: date, window_end: date
) -> tuple[int, int]:
    """
    Fetch NEO data for a single window and insert into DB.

    Returns (inserted_count, skipped_count).
    Raises httpx.HTTPError on request failure (caller handles).
    """
    resp = client.get(
        NEOWS_URL,
        params={
            "start_date": window_start.isoformat(),
            "end_date": window_end.isoformat(),
            "api_key": NASA_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    records = extract_records(resp.json())

    inserted = 0
    skipped = 0

    for record in records:
        result = session.execute(
            text(
                """
                INSERT INTO raw.neo_feeds (neo_id, name, raw_data, feed_date)
                VALUES (:neo_id, :name, cast(:raw_data as jsonb), :feed_date)
                ON CONFLICT (neo_id, feed_date) DO NOTHING
                """
            ),
            record,
        )
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1

    session.commit()
    return inserted, skipped


def run_backfill() -> None:
    """
    Main entry point. Orchestrates the full backfill:
    1. Calculate date range
    2. Generate windows
    3. Process each window with error handling
    4. Log summary
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=BACKFILL_DAYS)

    logger.info("Backfill range: %s → %s", start_date, end_date)

    windows = generate_windows(start_date, end_date, WINDOW_DAYS)
    logger.info("Total windows to process: %d", len(windows))

    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    with httpx.Client() as client:
        for i, (w_start, w_end) in enumerate(windows, 1):
            try:
                inserted, skipped = process_window(
                    SessionLocal(), client, w_start, w_end
                )
                total_inserted += inserted
                total_skipped += skipped
                logger.info(
                    "Window %d/%d [%s → %s]: inserted=%d skipped=%d",
                    i,
                    len(windows),
                    w_start,
                    w_end,
                    inserted,
                    skipped,
                )
            except httpx.HTTPError as exc:
                total_errors += 1
                logger.error(
                    "Window %d/%d [%s → %s]: HTTP error — %s",
                    i,
                    len(windows),
                    w_start,
                    w_end,
                    exc,
                )
            except Exception as exc:
                total_errors += 1
                logger.error(
                    "Window %d/%d [%s → %s]: unexpected error — %s",
                    i,
                    len(windows),
                    w_start,
                    w_end,
                    exc,
                )

            time.sleep(RATE_LIMIT_DELAY)

    logger.info(
        "Backfill complete: inserted=%d skipped=%d errors=%d",
        total_inserted,
        total_skipped,
        total_errors,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_backfill()
