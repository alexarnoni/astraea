import json
import logging
import os
from datetime import date, timedelta

import httpx
from sqlalchemy import text

from db import SessionLocal

logger = logging.getLogger(__name__)

NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
DONKI_BASE = "https://api.nasa.gov/DONKI"


def _ensure_unique_constraint(session) -> None:
    """Add UNIQUE(event_id, event_type) to raw.solar_events if not present."""
    session.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_solar_events_event_id_type'
                ) THEN
                    ALTER TABLE raw.solar_events
                    ADD CONSTRAINT uq_solar_events_event_id_type
                    UNIQUE (event_id, event_type);
                END IF;
            END$$;
            """
        )
    )
    session.commit()


def _insert_events(session, events: list, event_type: str, id_field: str) -> tuple[int, int]:
    inserted = skipped = 0
    for event in events:
        event_id = event.get(id_field)
        if not event_id:
            logger.warning("DONKI %s: missing %s field, skipping", event_type, id_field)
            continue

        # startTime format: "2024-01-15T12:00Z" — take date part only
        start_time: str = event.get("startTime", "")
        event_date = start_time[:10] if start_time else None

        result = session.execute(
            text(
                """
                INSERT INTO raw.solar_events (event_id, event_type, raw_data, event_date)
                VALUES (:event_id, :event_type, cast(:raw_data as jsonb), :event_date)
                ON CONFLICT (event_id, event_type) DO NOTHING
                """
            ),
            {
                "event_id": event_id,
                "event_type": event_type,
                "raw_data": json.dumps(event),
                "event_date": event_date,
            },
        )
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def _fetch(endpoint: str, start_date: date, end_date: date) -> list:
    try:
        resp = httpx.get(
            f"{DONKI_BASE}/{endpoint}",
            params={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "api_key": NASA_API_KEY,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except httpx.HTTPError as exc:
        logger.error("DONKI %s: HTTP error — %s", endpoint, exc)
        return []


def collect_cme() -> None:
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    logger.info("DONKI CME: fetching %s → %s", start_date, end_date)

    events = _fetch("CME", start_date, end_date)
    if not events:
        logger.info("DONKI CME: no events returned")
        return

    with SessionLocal() as session:
        _ensure_unique_constraint(session)
        inserted, skipped = _insert_events(session, events, "CME", "activityID")
        session.commit()

    logger.info("DONKI CME: inserted=%d skipped=%d", inserted, skipped)


def collect_gst() -> None:
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    logger.info("DONKI GST: fetching %s → %s", start_date, end_date)

    events = _fetch("GST", start_date, end_date)
    if not events:
        logger.info("DONKI GST: no events returned")
        return

    with SessionLocal() as session:
        _ensure_unique_constraint(session)
        inserted, skipped = _insert_events(session, events, "GST", "gstID")
        session.commit()

    logger.info("DONKI GST: inserted=%d skipped=%d", inserted, skipped)
