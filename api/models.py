from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AsteroidResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    neo_id: str
    name: Optional[str] = None
    feed_date: date
    close_approach_date: Optional[date] = None
    miss_distance_lunar: Optional[float] = None
    miss_distance_km: Optional[float] = None
    relative_velocity_km_s: Optional[float] = None
    velocity_km_per_h: Optional[float] = None
    estimated_diameter_min_km: Optional[float] = None
    estimated_diameter_max_km: Optional[float] = None
    absolute_magnitude_h: Optional[float] = None
    is_potentially_hazardous: Optional[bool] = None
    risk_label: Optional[str] = None
    risk_score_ml: Optional[float] = None
    risk_label_ml: Optional[str] = None
    orbit_class: Optional[str] = None
    is_sentry_object: Optional[bool] = None
    first_observation_date: Optional[str] = None
    nasa_jpl_url: Optional[str] = None


class SolarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    event_date: date
    start_time: Optional[str] = None
    speed_km_s: Optional[float] = None
    cme_type: Optional[str] = None
    half_angle_deg: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    kp_index_max: Optional[float] = None
    note: Optional[str] = None
    is_earth_directed: Optional[bool] = None
    intensity_label: Optional[str] = None


class StatsResponse(BaseModel):
    total_asteroids: int
    hazardous_count: int
    high_risk_ml: int
    medium_risk_ml: int
    low_risk_ml: int
    total_solar_events: int
    cme_count: int
    gst_count: int
    closest_approach_lunar: Optional[float] = None
    closest_asteroid_name: Optional[str] = None
