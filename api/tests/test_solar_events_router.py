# Feature: astraea-v1-1-solar-detail-and-filters — property tests para _row_to_solar
# Property 1: Round-trip do Row Mapper de eventos solares
# Validates: Requirements 1.1, 1.4

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from types import SimpleNamespace
from hypothesis import given, settings
from hypothesis import strategies as st

# Import model directly to avoid circular import through main.py -> routers
from models import SolarEventResponse


def _row_to_solar(row) -> SolarEventResponse:
    """Mirror of routers.solar_events._row_to_solar for isolated testing."""
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
        is_earth_directed=row.is_earth_directed,
    )


def make_solar_row(**kwargs):
    defaults = dict(
        event_id="2024-01-01T00:00:00-CME-001",
        event_type="CME",
        event_date=date(2024, 1, 1),
        start_time="2024-01-01T00:00Z",
        speed_km_s=500.0,
        cme_type="S",
        half_angle_deg=45.0,
        latitude=10.0,
        longitude=20.0,
        kp_index_max=None,
        note="Test event",
        intensity_label="moderado",
        is_earth_directed=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


event_type_st = st.sampled_from(["CME", "GST"])
speed_st = st.one_of(st.none(), st.floats(min_value=0, max_value=5000, allow_nan=False))
cme_type_st = st.one_of(st.none(), st.text(min_size=1, max_size=10))
angle_st = st.one_of(st.none(), st.floats(min_value=0, max_value=360, allow_nan=False))
coord_st = st.one_of(st.none(), st.floats(min_value=-90, max_value=90, allow_nan=False))
kp_st = st.one_of(st.none(), st.floats(min_value=0, max_value=9, allow_nan=False))
note_st = st.one_of(st.none(), st.text(min_size=1, max_size=200))
intensity_st = st.one_of(st.none(), st.sampled_from(["fraco", "moderado", "severo", "extremo"]))
earth_directed_st = st.one_of(st.none(), st.booleans())


@given(
    event_type=event_type_st,
    speed_km_s=speed_st,
    cme_type=cme_type_st,
    half_angle_deg=angle_st,
    latitude=coord_st,
    longitude=coord_st,
    kp_index_max=kp_st,
    note=note_st,
    intensity_label=intensity_st,
    is_earth_directed=earth_directed_st,
)
@settings(max_examples=100)
def test_row_to_solar_round_trip(
    event_type, speed_km_s, cme_type, half_angle_deg,
    latitude, longitude, kp_index_max, note,
    intensity_label, is_earth_directed,
):
    """
    Feature: astraea-v1-1-solar-detail-and-filters, Property 1: Round-trip do Row Mapper
    """
    row = make_solar_row(
        event_type=event_type,
        speed_km_s=speed_km_s,
        cme_type=cme_type,
        half_angle_deg=half_angle_deg,
        latitude=latitude,
        longitude=longitude,
        kp_index_max=kp_index_max,
        note=note,
        intensity_label=intensity_label,
        is_earth_directed=is_earth_directed,
    )
    result = _row_to_solar(row)

    assert result.event_type == event_type
    assert result.cme_type == cme_type
    assert result.note == note
    assert result.intensity_label == intensity_label
    assert result.is_earth_directed == is_earth_directed

    if speed_km_s is None:
        assert result.speed_km_s is None
    else:
        assert abs(result.speed_km_s - speed_km_s) < 1e-6

    if half_angle_deg is None:
        assert result.half_angle_deg is None
    else:
        assert abs(result.half_angle_deg - half_angle_deg) < 1e-6

    if latitude is None:
        assert result.latitude is None
    else:
        assert abs(result.latitude - latitude) < 1e-6

    if longitude is None:
        assert result.longitude is None
    else:
        assert abs(result.longitude - longitude) < 1e-6

    if kp_index_max is None:
        assert result.kp_index_max is None
    else:
        assert abs(result.kp_index_max - kp_index_max) < 1e-6
