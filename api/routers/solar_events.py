from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from models import SolarEventResponse

router = APIRouter()


def _row_to_solar(row) -> SolarEventResponse:
    return SolarEventResponse(
        event_id=row.event_id,
        event_type=row.event_type,
        event_date=row.event_date,
        start_time=row.start_time,
        speed_km_s=float(row.speed_km_s) if row.speed_km_s is not None else None,
        cme_type=row.cme_type,
        half_angle_deg=float(row.half_angle_deg) if row.half_angle_deg is not None else None,
        latitude=float(row.latitude) if row.latitude is not None else None,
        longitude=float(row.longitude) if row.longitude is not None else None,
        kp_index_max=float(row.kp_index_max) if row.kp_index_max is not None else None,
        note=row.note,
        intensity_label=row.intensity_label,
    )


@router.get("/solar-events", response_model=List[SolarEventResponse])
def list_solar_events(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    filters = []
    params: dict = {"limit": limit, "offset": offset}

    if event_type is not None:
        filters.append("event_type ILIKE :event_type")
        params["event_type"] = event_type
    if start_date is not None:
        filters.append("event_date >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        filters.append("event_date <= :end_date")
        params["end_date"] = end_date

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = text(f"""
        SELECT * FROM mart.mart_solar_events
        {where}
        ORDER BY event_date DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(sql, params).fetchall()
    return [_row_to_solar(r) for r in rows]


@router.get("/solar-events/earth-directed", response_model=List[SolarEventResponse])
def earth_directed_events(db: Session = Depends(get_db)):
    # sem coluna is_earth_directed: retorna CMEs com speed alta (proxy para impacto terrestre)
    sql = text("""
        SELECT * FROM mart.mart_solar_events
        WHERE event_type = 'CME'
        ORDER BY event_date DESC
    """)
    rows = db.execute(sql).fetchall()
    return [_row_to_solar(r) for r in rows]
