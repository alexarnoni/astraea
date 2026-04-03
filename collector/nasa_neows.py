import logging
import os
from datetime import date, timedelta

import httpx
from sqlalchemy import text

from db import SessionLocal

logger = logging.getLogger(__name__)

NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
NEOWS_URL = "https://api.nasa.gov/neo/rest/v1/feed"


def collect_neows() -> None:
    start_date = date.today()
    end_date = start_date + timedelta(days=6)

    logger.info("NeoWs: fetching %s → %s", start_date, end_date)

    try:
        resp = httpx.get(
            NEOWS_URL,
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "api_key": NASA_API_KEY,
            },
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("NeoWs: HTTP error — %s", exc)
        return

    neo_by_date: dict = resp.json().get("near_earth_objects", {})

    inserted = 0
    skipped = 0

    with SessionLocal() as session:
        for feed_date_str, objects in neo_by_date.items():
            for obj in objects:
                result = session.execute(
                    text(
                        """
                        INSERT INTO raw.neo_feeds (neo_id, name, raw_data, feed_date)
                        VALUES (:neo_id, :name, cast(:raw_data as jsonb), :feed_date)
                        ON CONFLICT (neo_id, feed_date) DO NOTHING
                        """
                    ),
                    {
                        "neo_id": obj["id"],
                        "name": obj.get("name"),
                        "raw_data": __import__("json").dumps(obj),
                        "feed_date": feed_date_str,
                    },
                )
                if result.rowcount:
                    inserted += 1
                else:
                    skipped += 1
        session.commit()

    logger.info("NeoWs: inserted=%d skipped=%d", inserted, skipped)
