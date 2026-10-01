"""Fase 6: campos pha_* aditivos nos endpoints de asteroides e CORS do site do autor.

Nenhum banco real: a dependencia get_db e trocada por uma sessao falsa que registra o SQL.
"""

import importlib.util
import os
import sys
from datetime import date
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main  # noqa: E402
from database import get_db  # noqa: E402
from routers.asteroids import _row_to_asteroid  # noqa: E402

ALLOWED = [
    "https://astraea.alexarnoni.com",
    "https://alexarnoni.com",
    "https://www.alexarnoni.com",
]


def _row(**extra):
    base = dict(
        neo_id="2000001",
        name="Test",
        feed_date=date(2026, 10, 1),
        close_approach_date=date(2026, 10, 2),
        miss_distance_lunar=10.5,
        miss_distance_km=4000000.0,
        relative_velocity_km_s=15.0,
        velocity_km_per_h=54000.0,
        estimated_diameter_min_km=0.1,
        estimated_diameter_max_km=0.3,
        absolute_magnitude_h=20.0,
        is_potentially_hazardous=True,
        risk_label="alto",
        risk_proba_baixo=0.1,
        risk_proba_medio=0.2,
        risk_proba_alto=0.7,
        risk_label_ml="alto",
        orbit_class=None,
        is_sentry_object=None,
        first_observation_date=None,
        nasa_jpl_url=None,
    )
    base.update(extra)
    return SimpleNamespace(**base)


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.sql = []

    def execute(self, stmt, params=None):
        self.sql.append(str(stmt))
        rows = self.rows

        class Result:
            def fetchall(_self):
                return rows

            def fetchone(_self):
                return rows[0] if rows else None

        return Result()


@pytest.fixture
def client_and_db():
    def make(rows):
        db = FakeSession(rows)
        main.app.dependency_overrides[get_db] = lambda: db
        return TestClient(main.app), db

    yield make
    main.app.dependency_overrides.clear()


# ------------------------------------------------------------------ campos pha_*

def test_row_mapper_maps_pha_fields():
    out = _row_to_asteroid(_row(pha_probability=0.42, pha_model_version="2.0.0"))
    assert out.pha_probability == pytest.approx(0.42)
    assert out.pha_model_version == "2.0.0"


def test_row_mapper_pha_fields_default_to_none_when_absent_or_null():
    assert _row_to_asteroid(_row()).pha_probability is None
    assert _row_to_asteroid(_row()).pha_model_version is None
    out = _row_to_asteroid(_row(pha_probability=None, pha_model_version=None))
    assert out.pha_probability is None and out.pha_model_version is None


@pytest.mark.parametrize("path", ["/v1/asteroids", "/v1/asteroids/upcoming", "/v1/asteroids/2000001"])
def test_endpoints_select_and_return_pha_fields(client_and_db, path):
    client, db = client_and_db([_row(pha_probability=0.81, pha_model_version="2.0.0")])
    resp = client.get(path)
    assert resp.status_code == 200
    body = resp.json()
    item = body[0] if isinstance(body, list) else body
    assert item["pha_probability"] == pytest.approx(0.81)
    assert item["pha_model_version"] == "2.0.0"
    assert "m.pha_probability" in db.sql[0] and "m.pha_model_version" in db.sql[0]


def test_contract_is_additive_legacy_fields_unchanged(client_and_db):
    client, _ = client_and_db([_row(pha_probability=0.5, pha_model_version="2.0.0")])
    item = client.get("/v1/asteroids/upcoming").json()[0]
    for key in (
        "risk_label", "risk_proba_baixo", "risk_proba_medio", "risk_proba_alto",
        "risk_label_ml", "model_version", "model_trained_at",
    ):
        assert key in item
    assert item["risk_label_ml"] == "alto" and item["risk_label"] == "alto"


def test_unscored_asteroid_returns_null_pha_fields(client_and_db):
    client, _ = client_and_db([_row(pha_probability=None, pha_model_version=None)])
    item = client.get("/v1/asteroids/upcoming").json()[0]
    assert item["pha_probability"] is None and item["pha_model_version"] is None


# ------------------------------------------------------------------ CORS

def test_default_origins_include_author_sites():
    for origin in ALLOWED:
        assert origin in main.CORS_ALLOW_ORIGINS


@pytest.mark.parametrize("origin", ALLOWED)
def test_cors_allows_author_sites(origin):
    client = TestClient(main.app)
    resp = client.get("/health", headers={"Origin": origin})
    assert resp.headers.get("access-control-allow-origin") == origin


def test_cors_does_not_echo_unknown_origin():
    client = TestClient(main.app)
    resp = client.get("/health", headers={"Origin": "https://evil.example"})
    assert resp.headers.get("access-control-allow-origin") is None


def test_cors_env_override_is_respected(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://only.example")
    spec = importlib.util.spec_from_file_location("main_cors_override", main.__file__)
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert fresh.CORS_ALLOW_ORIGINS == ["https://only.example"]


# ------------------------------------------------------------------ SQL real (SQLite com schema mart)

def test_real_sql_of_the_three_endpoints_executes_and_returns_pha_fields():
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS mart")

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE mart.mart_asteroids (neo_id TEXT, name TEXT, feed_date TEXT, close_approach_date TEXT, "
            "miss_distance_lunar REAL, miss_distance_km REAL, relative_velocity_km_s REAL, velocity_km_per_h REAL, "
            "estimated_diameter_min_km REAL, estimated_diameter_max_km REAL, absolute_magnitude_h REAL, "
            "is_potentially_hazardous INTEGER, risk_label TEXT)"
        ))
        conn.execute(text(
            "CREATE TABLE mart.mart_asteroids_ml (neo_id TEXT, feed_date TEXT, risk_proba_baixo REAL, "
            "risk_proba_medio REAL, risk_proba_alto REAL, risk_label_ml TEXT, pha_probability REAL, "
            "pha_model_version TEXT)"
        ))
        conn.execute(text(
            "INSERT INTO mart.mart_asteroids VALUES ('1', 'a', '2099-01-01', '2099-01-02', 1.0, 384400.0, 10.0, "
            "36000.0, 0.1, 0.2, 20.0, 1, 'alto'), ('2', 'b', '2099-01-01', '2099-01-03', 2.0, 768800.0, 11.0, "
            "39600.0, 0.1, 0.2, 25.0, 0, 'baixo')"
        ))
        conn.execute(text(
            "INSERT INTO mart.mart_asteroids_ml VALUES ('1', '2099-01-01', 0.1, 0.2, 0.7, 'alto', 0.83, '2.0.0')"
        ))

    def override():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_db] = override
    try:
        client = TestClient(main.app)
        for path in ("/v1/asteroids", "/v1/asteroids/upcoming"):
            items = {i["neo_id"]: i for i in client.get(path).json()}
            assert items["1"]["pha_probability"] == pytest.approx(0.83)
            assert items["1"]["pha_model_version"] == "2.0.0"
            assert items["2"]["pha_probability"] is None  # sem linha de scoring: LEFT JOIN
            assert items["2"]["pha_model_version"] is None
        one = client.get("/v1/asteroids/1").json()
        assert one["pha_model_version"] == "2.0.0"
    finally:
        main.app.dependency_overrides.clear()
