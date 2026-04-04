from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from models import AsteroidResponse

router = APIRouter()


def _row_to_asteroid(row) -> AsteroidResponse:
    return AsteroidResponse(
        neo_id=row.neo_id,
        name=row.name,
        feed_date=row.feed_date,
        close_approach_date=row.close_approach_date,
        miss_distance_lunar=float(row.miss_distance_lunar) if row.miss_distance_lunar is not None else None,
        miss_distance_km=float(row.miss_distance_km) if row.miss_distance_km is not None else None,
        relative_velocity_km_s=float(row.relative_velocity_km_s) if row.relative_velocity_km_s is not None else None,
        velocity_km_per_h=float(row.velocity_km_per_h) if row.velocity_km_per_h is not None else None,
        estimated_diameter_min_km=float(row.estimated_diameter_min_km) if row.estimated_diameter_min_km is not None else None,
        estimated_diameter_max_km=float(row.estimated_diameter_max_km) if row.estimated_diameter_max_km is not None else None,
        absolute_magnitude_h=float(row.absolute_magnitude_h) if row.absolute_magnitude_h is not None else None,
        is_potentially_hazardous=row.is_potentially_hazardous,
        risk_label=row.risk_label,
        risk_score_ml=float(row.risk_score_ml) if row.risk_score_ml is not None else None,
        risk_label_ml=row.risk_label_ml,
        orbit_class=row.orbit_class,
        is_sentry_object=row.is_sentry_object,
        first_observation_date=str(row.first_observation_date) if row.first_observation_date is not None else None,
        nasa_jpl_url=row.nasa_jpl_url,
    )


@router.get("/asteroids", response_model=List[AsteroidResponse])
def list_asteroids(
    limit: int = 50,
    offset: int = 0,
    hazardous: Optional[bool] = None,
    risk_label: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    filters = []
    params: dict = {"limit": limit, "offset": offset}

    if hazardous is not None:
        filters.append("is_potentially_hazardous = :hazardous")
        params["hazardous"] = hazardous
    if risk_label is not None:
        filters.append("risk_label_ml ILIKE :risk_label")
        params["risk_label"] = risk_label
    if start_date is not None:
        filters.append("feed_date >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        filters.append("feed_date <= :end_date")
        params["end_date"] = end_date

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = text(f"""
        SELECT * FROM mart.mart_asteroids
        {where}
        ORDER BY miss_distance_lunar ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(sql, params).fetchall()
    return [_row_to_asteroid(r) for r in rows]


@router.get("/asteroids/upcoming", response_model=List[AsteroidResponse])
def upcoming_asteroids(db: Session = Depends(get_db)):
    sql = text("""
        SELECT * FROM mart.mart_asteroids
        WHERE close_approach_date >= CURRENT_DATE
        ORDER BY close_approach_date ASC
        LIMIT 20
    """)
    rows = db.execute(sql).fetchall()
    return [_row_to_asteroid(r) for r in rows]


@router.get("/asteroids/{neo_id}", response_model=AsteroidResponse)
def get_asteroid(neo_id: str, db: Session = Depends(get_db)):
    sql = text("SELECT * FROM mart.mart_asteroids WHERE neo_id = :neo_id")
    row = db.execute(sql, {"neo_id": neo_id}).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Asteroid not found")
    return _row_to_asteroid(row)
