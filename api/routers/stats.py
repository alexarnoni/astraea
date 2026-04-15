from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from models import StatsResponse
from limiter import limiter

router = APIRouter()


@router.get("/stats/summary", response_model=StatsResponse)
@limiter.limit("60/minute")
def stats_summary(request: Request, db: Session = Depends(get_db)):
    # Check which columns exist in mart_asteroids
    cols = db.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'mart' AND table_name = 'mart_asteroids'
    """)).fetchall()
    col_names = {r[0] for r in cols}
    has_ml = "risk_label_ml" in col_names

    if has_ml:
        ast = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE is_potentially_hazardous = true) AS hazardous,
                COUNT(*) FILTER (WHERE risk_label_ml ILIKE 'alto') AS high_risk,
                COUNT(*) FILTER (WHERE risk_label_ml ILIKE 'médio') AS medium_risk,
                COUNT(*) FILTER (WHERE risk_label_ml ILIKE 'baixo') AS low_risk,
                MIN(miss_distance_lunar) AS closest_lunar
            FROM mart.mart_asteroids
        """)).fetchone()
    else:
        ast = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE is_potentially_hazardous = true) AS hazardous,
                0 AS high_risk,
                0 AS medium_risk,
                0 AS low_risk,
                MIN(miss_distance_lunar) AS closest_lunar
            FROM mart.mart_asteroids
        """)).fetchone()

    closest_name = None
    if ast.closest_lunar is not None:
        row = db.execute(text("""
            SELECT name FROM mart.mart_asteroids
            ORDER BY miss_distance_lunar ASC NULLS LAST
            LIMIT 1
        """)).fetchone()
        if row:
            closest_name = row.name

    sol = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE event_type = 'CME') AS cme,
            COUNT(*) FILTER (WHERE event_type = 'GST') AS gst
        FROM mart.mart_solar_events
    """)).fetchone()

    return StatsResponse(
        total_asteroids=ast.total,
        hazardous_count=ast.hazardous,
        high_risk_ml=ast.high_risk,
        medium_risk_ml=ast.medium_risk,
        low_risk_ml=ast.low_risk,
        total_solar_events=sol.total,
        cme_count=sol.cme,
        gst_count=sol.gst,
        closest_approach_lunar=float(ast.closest_lunar) if ast.closest_lunar is not None else None,
        closest_asteroid_name=closest_name,
    )
