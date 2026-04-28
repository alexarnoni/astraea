# Feature: asteroid-new-fields — property tests para _row_to_asteroid
# Property 3: Round-trip do Row_Mapper
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from types import SimpleNamespace
from hypothesis import given, settings
from hypothesis import strategies as st

from routers.asteroids import _row_to_asteroid


def make_row(**kwargs):
    """Cria um mock de row com valores padrão para campos obrigatórios."""
    defaults = dict(
        neo_id="2000001",
        name="Test Asteroid",
        feed_date=date(2024, 1, 1),
        close_approach_date=date(2024, 6, 1),
        miss_distance_lunar=10.5,
        miss_distance_km=4000000.0,
        relative_velocity_km_s=15.0,
        velocity_km_per_h=54000.0,
        estimated_diameter_min_km=0.1,
        estimated_diameter_max_km=0.3,
        absolute_magnitude_h=20.0,
        is_potentially_hazardous=False,
        risk_label="baixo",
        risk_proba_baixo=0.85,
        risk_proba_medio=0.10,
        risk_proba_alto=0.05,
        risk_label_ml="baixo",
        orbit_class=None,
        is_sentry_object=None,
        first_observation_date=None,
        nasa_jpl_url=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


orbit_class_st = st.one_of(st.none(), st.text(min_size=1, max_size=50))
is_sentry_st = st.one_of(st.none(), st.booleans())
first_obs_st = st.one_of(st.none(), st.dates().map(str))
jpl_url_st = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=200).map(lambda s: "https://ssd.jpl.nasa.gov/" + s),
)


@given(
    orbit_class=orbit_class_st,
    is_sentry_object=is_sentry_st,
    first_observation_date=first_obs_st,
    nasa_jpl_url=jpl_url_st,
)
@settings(max_examples=100)
def test_row_mapper_round_trip(orbit_class, is_sentry_object, first_observation_date, nasa_jpl_url):
    """
    Feature: asteroid-new-fields, Property 3: Round-trip do Row_Mapper
    Para qualquer combinação de valores (incluindo None) nos quatro novos campos,
    _row_to_asteroid deve produzir um AsteroidResponse com os mesmos valores.
    """
    row = make_row(
        orbit_class=orbit_class,
        is_sentry_object=is_sentry_object,
        first_observation_date=first_observation_date,
        nasa_jpl_url=nasa_jpl_url,
    )
    result = _row_to_asteroid(row)

    assert result.orbit_class == orbit_class
    assert result.is_sentry_object == is_sentry_object
    assert result.nasa_jpl_url == nasa_jpl_url

    if first_observation_date is None:
        assert result.first_observation_date is None
    else:
        assert result.first_observation_date == str(first_observation_date)


# Feature: ml-risk-probabilities — property test P4
# Property 4: Round-trip do Row Mapper com probabilidades
# Validates: Requirements 6.1, 6.2, 6.3, 6.5, 7.3

proba_st = st.one_of(
    st.none(),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)


@given(
    risk_proba_baixo=proba_st,
    risk_proba_medio=proba_st,
    risk_proba_alto=proba_st,
)
@settings(max_examples=100)
def test_row_mapper_round_trip_probabilities(risk_proba_baixo, risk_proba_medio, risk_proba_alto):
    """
    Feature: ml-risk-probabilities, Property 4: Round-trip do Row Mapper com probabilidades
    **Validates: Requirements 6.1, 6.2, 6.3, 6.5, 7.3**

    Para qualquer combinação de (float | None) nos campos risk_proba_baixo,
    risk_proba_medio, risk_proba_alto, _row_to_asteroid produz um AsteroidResponse
    com os mesmos valores de probabilidade (float preservado, None preservado).
    """
    row = make_row(
        risk_proba_baixo=risk_proba_baixo,
        risk_proba_medio=risk_proba_medio,
        risk_proba_alto=risk_proba_alto,
    )
    result = _row_to_asteroid(row)

    assert result.risk_proba_baixo == risk_proba_baixo
    assert result.risk_proba_medio == risk_proba_medio
    assert result.risk_proba_alto == risk_proba_alto
