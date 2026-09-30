"""Testes da escrita dupla do predict.py: colunas legadas e colunas pha_*.

Usam modelos minusculos treinados na hora e SQLite em memoria (schema mart via ATTACH).
Nenhum banco real e aberto.
"""

import importlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

sys.modules.pop("predict", None)
predict = importlib.import_module("predict")

PHA_FEATURES = ["relative_velocity_km_s", "miss_distance_lunar", "absolute_magnitude_h"]


def _pha_model(seed: int = 0) -> RandomForestClassifier:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        {
            "relative_velocity_km_s": rng.uniform(3, 40, 300),
            "miss_distance_lunar": rng.uniform(1, 80, 300),
            "absolute_magnitude_h": rng.uniform(16, 30, 300),
        }
    )
    y = (X["absolute_magnitude_h"] < 22).astype(int)
    return RandomForestClassifier(n_estimators=10, random_state=0).fit(X, y)


def _legacy_model() -> RandomForestClassifier:
    rng = np.random.default_rng(1)
    X = pd.DataFrame(
        {
            "miss_distance_lunar": rng.uniform(1, 80, 300),
            "relative_velocity_km_s": rng.uniform(3, 40, 300),
            "diameter_avg_km": rng.uniform(0.01, 1.0, 300),
            "absolute_magnitude_h": rng.uniform(16, 30, 300),
            "is_potentially_hazardous": rng.integers(0, 2, 300),
        }
    )
    y = np.where(
        X["absolute_magnitude_h"] < 19,
        "alto",
        np.where(X["absolute_magnitude_h"] < 24, "médio", "baixo"),
    )
    return RandomForestClassifier(n_estimators=10, random_state=0).fit(X, y)


def _write_pha(dir_: Path, model=None, meta=None) -> None:
    joblib.dump(model or _pha_model(), dir_ / "pha_classifier.joblib")
    meta = meta if meta is not None else {
        "model_version": "2.0.0",
        "feature_columns": PHA_FEATURES,
    }
    (dir_ / "metadata_pha.json").write_text(json.dumps(meta), encoding="utf-8")


@pytest.fixture
def paths(tmp_path, monkeypatch):
    monkeypatch.setattr(predict, "_PHA_MODEL_PATH", tmp_path / "pha_classifier.joblib")
    monkeypatch.setattr(predict, "_PHA_METADATA_PATH", tmp_path / "metadata_pha.json")
    return tmp_path


# ------------------------------------------------------------------ carga do modelo

def test_load_returns_none_when_files_missing(paths):
    assert predict._load_pha_model() is None


def test_load_valid_model(paths):
    _write_pha(paths)
    model, version, features = predict._load_pha_model()
    assert version == "2.0.0"
    assert features == PHA_FEATURES
    assert list(model.classes_) == [0, 1]


def test_load_rejects_feature_mismatch(paths):
    _write_pha(paths, meta={"model_version": "2.0.0", "feature_columns": list(reversed(PHA_FEATURES))})
    assert predict._load_pha_model() is None


def test_load_rejects_missing_version(paths):
    _write_pha(paths, meta={"feature_columns": PHA_FEATURES})
    assert predict._load_pha_model() is None


def test_load_rejects_corrupt_model_file(paths):
    _write_pha(paths)
    (paths / "pha_classifier.joblib").write_bytes(b"not a joblib file")
    assert predict._load_pha_model() is None


def test_load_rejects_model_without_positive_class(paths):
    X = pd.DataFrame({c: np.arange(20.0) for c in PHA_FEATURES})
    one_class = RandomForestClassifier(n_estimators=3, random_state=0).fit(X, np.zeros(20, dtype=int))
    _write_pha(paths, model=one_class)
    assert predict._load_pha_model() is None


# ------------------------------------------------------------------ pontuacao

def test_score_pha_probabilities_in_range_and_none_for_missing_features():
    model = _pha_model()
    df = pd.DataFrame(
        {
            "neo_id": ["a", "b", "c"],
            "miss_distance_lunar": [5.0, 5.0, np.nan],
            "relative_velocity_km_s": [10.0, 10.0, 10.0],
            "absolute_magnitude_h": [18.0, 28.0, 18.0],
        }
    )
    out = predict._score_pha(df, model, PHA_FEATURES)
    assert len(out) == 3
    assert out[2] is None
    assert all(0.0 <= p <= 1.0 for p in out[:2])
    assert out[0] > out[1]  # H menor (mais brilhante) tem probabilidade maior de PHA


def test_score_pha_follows_feature_order_by_name_not_dataframe_order():
    model = _pha_model()
    df = pd.DataFrame(
        {
            "absolute_magnitude_h": [18.0],
            "miss_distance_lunar": [5.0],
            "relative_velocity_km_s": [10.0],
        }
    )
    a = predict._score_pha(df, model, PHA_FEATURES)
    b = predict._score_pha(df[list(reversed(df.columns))], model, PHA_FEATURES)
    assert a == b


def test_score_pha_all_rows_missing_returns_all_none():
    df = pd.DataFrame({c: [np.nan, np.nan] for c in PHA_FEATURES})
    assert predict._score_pha(df, _pha_model(), PHA_FEATURES) == [None, None]


def test_has_pha_columns_reads_information_schema():
    class Conn:
        def __init__(self, n):
            self.n = n

        def execute(self, _stmt):
            rows = [("pha_probability",), ("pha_model_version",)][: self.n]

            class R:
                def fetchall(_self):
                    return rows

            return R()

    assert predict._ml_table_has_pha_columns(Conn(2)) is True
    assert predict._ml_table_has_pha_columns(Conn(1)) is False
    assert predict._ml_table_has_pha_columns(Conn(0)) is False


# ------------------------------------------------------------------ run_scoring de ponta a ponta

def _engine(with_pha_columns: bool):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS mart")

    pha_cols = ", pha_probability REAL, pha_model_version TEXT" if with_pha_columns else ""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE mart.mart_asteroids (neo_id TEXT, feed_date TEXT, miss_distance_lunar REAL, "
            "relative_velocity_km_s REAL, estimated_diameter_min_km REAL, estimated_diameter_max_km REAL, "
            "absolute_magnitude_h REAL, is_potentially_hazardous INTEGER)"
        ))
        conn.execute(text(
            "CREATE TABLE mart.mart_asteroids_ml (neo_id TEXT, feed_date TEXT, risk_proba_baixo REAL, "
            f"risk_proba_medio REAL, risk_proba_alto REAL, risk_label_ml TEXT{pha_cols})"
        ))
        conn.execute(text(
            "INSERT INTO mart.mart_asteroids_ml (neo_id, feed_date, risk_label_ml) "
            "VALUES ('old', '2020-01-01', 'baixo')"
        ))
        rows = [
            ("n1", "2026-01-01", 5.0, 10.0, 0.4, 0.9, 18.0, 1),
            ("n2", "2026-01-01", 50.0, 10.0, 0.01, 0.02, 28.0, 0),
            ("n3", "2026-01-02", 50.0, 10.0, 0.01, 0.02, None, 0),
        ]
        for r in rows:
            conn.execute(
                text("INSERT INTO mart.mart_asteroids VALUES (:a, :b, :c, :d, :e, :f, :g, :h)"),
                dict(zip("abcdefgh", r)),
            )
    return engine


@pytest.fixture
def scoring_env(tmp_path, monkeypatch):
    joblib.dump(_legacy_model(), tmp_path / "risk_classifier.joblib")
    monkeypatch.setattr(predict, "_MODEL_PATH", tmp_path / "risk_classifier.joblib")
    monkeypatch.setattr(predict, "_METADATA_PATH", tmp_path / "metadata.json")
    monkeypatch.setattr(predict, "_PHA_MODEL_PATH", tmp_path / "pha_classifier.joblib")
    monkeypatch.setattr(predict, "_PHA_METADATA_PATH", tmp_path / "metadata_pha.json")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    monkeypatch.setattr(predict, "load_dotenv", lambda *a, **k: None)
    return tmp_path


def _run(monkeypatch, engine, has_pha_columns):
    monkeypatch.setattr(predict, "_make_engine", lambda _url: engine)
    monkeypatch.setattr(predict, "_ml_table_has_pha_columns", lambda _conn: has_pha_columns)
    predict.run_scoring()
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT * FROM mart.mart_asteroids_ml ORDER BY neo_id"), conn)


def test_run_scoring_writes_legacy_and_pha_columns(scoring_env, monkeypatch):
    _write_pha(scoring_env)
    out = _run(monkeypatch, _engine(True), True)
    assert list(out["neo_id"]) == ["n1", "n2", "n3"]  # DELETE + INSERT: linha antiga removida
    assert out["risk_label_ml"].notna().all()
    assert out[["risk_proba_baixo", "risk_proba_medio", "risk_proba_alto"]].notna().all().all()
    assert out.loc[out.neo_id == "n1", "pha_model_version"].iloc[0] == "2.0.0"
    assert 0.0 <= out.loc[out.neo_id == "n1", "pha_probability"].iloc[0] <= 1.0
    # sem H (feature nula): sem probabilidade e sem versao
    n3 = out[out.neo_id == "n3"].iloc[0]
    assert pd.isna(n3["pha_probability"]) and pd.isna(n3["pha_model_version"])


def test_run_scoring_without_pha_model_leaves_pha_null_and_keeps_legacy(scoring_env, monkeypatch):
    out = _run(monkeypatch, _engine(True), True)
    assert len(out) == 3
    assert out["risk_label_ml"].notna().all()
    assert out["pha_probability"].isna().all() and out["pha_model_version"].isna().all()


def test_run_scoring_falls_back_to_legacy_insert_when_columns_missing(scoring_env, monkeypatch):
    _write_pha(scoring_env)
    out = _run(monkeypatch, _engine(False), False)
    assert len(out) == 3
    assert out["risk_label_ml"].notna().all()
    assert "pha_probability" not in out.columns


def test_run_scoring_legacy_values_unchanged_by_pha_model(scoring_env, monkeypatch):
    without = _run(monkeypatch, _engine(True), True)
    _write_pha(scoring_env)
    with_pha = _run(monkeypatch, _engine(True), True)
    legacy = ["neo_id", "risk_proba_baixo", "risk_proba_medio", "risk_proba_alto", "risk_label_ml"]
    pd.testing.assert_frame_equal(without[legacy], with_pha[legacy])
