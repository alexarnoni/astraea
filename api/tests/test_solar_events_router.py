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

from routers.solar_events import _row_to_solar


def make_solar_row(**kwargs):
    """Cria um mock de row com valores padrão para campos de evento solar."""
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
