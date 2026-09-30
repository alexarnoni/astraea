"""Testes do retarget. Usam dados sinteticos: validam a mecanica, nao produzem metricas reais."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import train_retarget as tr  # noqa: E402


def _synthetic(n_asteroids: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    dates = pd.date_range("2025-01-01", periods=60)
    for i in range(n_asteroids):
        h = rng.uniform(16, 30)
        pha = int(h < 22 and rng.random() < 0.7)
        for _ in range(rng.integers(1, 5)):
            rows.append({
                "neo_id": str(1000 + i),
                "feed_date": rng.choice(dates),
                "miss_distance_lunar": rng.uniform(1, 80),
                "relative_velocity_km_s": rng.uniform(3, 40),
                "estimated_diameter_min_km": 10 ** (-0.2 * h + 3) / 1000,
                "estimated_diameter_max_km": 10 ** (-0.2 * h + 3) / 700,
                "absolute_magnitude_h": h,
                "is_potentially_hazardous": bool(pha),
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def result():
    return tr.run_experiment(_synthetic())


def test_no_neo_id_leak_between_train_and_test(result):
    df = result["df"]
    folds = tr.make_folds(df)
    assert len(folds) == tr.N_SPLITS
    for train_idx, test_idx in folds:
        assert not (set(df["neo_id"].iloc[train_idx]) & set(df["neo_id"].iloc[test_idx]))
        assert df[tr.TARGET_COLUMN].iloc[test_idx].sum() > 0


def test_metrics_json_has_exact_keys(result, tmp_path):
    metrics = tr.write_artifacts(result, out_docs=tmp_path / "docs", out_art=tmp_path / "art")
    on_disk = json.loads((tmp_path / "docs" / "ml-metrics.json").read_text(encoding="utf-8"))
    assert list(on_disk.keys()) == tr.METRICS_JSON_KEYS
    assert set(metrics) == set(tr.METRICS_JSON_KEYS)
    assert set(on_disk["baselines"]) == {"majority", "logistic_regression"}
    for b in on_disk["baselines"].values():
        assert set(b) == {"precision", "recall", "f1", "pr_auc"}
    assert set(on_disk["metrics"]) == {"precision", "recall", "f1", "pr_auc", "std_between_folds"}
    assert on_disk["status"] == "retargeted"
    assert on_disk["target"] == "is_potentially_hazardous"


def test_no_em_dash_in_generated_text(result, tmp_path):
    tr.write_artifacts(result, out_docs=tmp_path / "docs", out_art=tmp_path / "art")
    for name in ("ml-metrics.json", "ml-report.md"):
        text = (tmp_path / "docs" / name).read_text(encoding="utf-8")
        assert "\u2014" not in text and "\u2013" not in text


def test_target_flag_not_in_features():
    assert tr.TARGET_COLUMN not in tr.FEATURE_COLUMNS
    assert tr.FEATURE_COLUMNS == [
        "relative_velocity_km_s", "miss_distance_lunar", "absolute_magnitude_h",
    ]
    for banned in ("risk_score", "risk_label", "is_potentially_hazardous", "diameter_avg_km"):
        assert banned not in tr.FEATURE_COLUMNS


def test_majority_pr_auc_equals_prevalence(result):
    maj = result["cv"]["per_fold"]["majority"]
    for r in maj:
        assert r["pr_auc"] == pytest.approx(r["prevalence"])


@pytest.mark.parametrize(
    "raw, expected",
    [("t", 1), ("f", 0), ("true", 1), ("false", 0), ("1", 1), ("0", 0),
     ("T", 1), ("False", 0), (" t ", 1)],
)
def test_to_flag_accepts_csv_values(raw, expected):
    out = tr._to_flag(pd.Series([raw]))
    assert out.tolist() == [expected]


def test_to_flag_accepts_real_bool_and_keeps_false():
    assert tr._to_flag(pd.Series([True, False, True])).tolist() == [1, 0, 1]


@pytest.mark.parametrize("bad", ["yes", "no", "2", "", "nan", "tt"])
def test_to_flag_rejects_unknown_value(bad):
    with pytest.raises(ValueError):
        tr._to_flag(pd.Series(["t", bad]))


def test_prepare_does_not_turn_string_f_into_positive():
    df = _synthetic(20)
    df["is_potentially_hazardous"] = df["is_potentially_hazardous"].map({True: "t", False: "f"})
    out = tr.prepare(df)
    assert out["is_potentially_hazardous"].sum() == (df["is_potentially_hazardous"] == "t").sum()


def _shape(obj):
    """Estrutura do JSON: chaves e tipos, sem valores."""
    if isinstance(obj, dict):
        return {k: _shape(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [type(v).__name__ for v in obj]
    return type(obj).__name__


def test_metrics_json_format_stable_with_exploratory_note(result, tmp_path):
    tr.write_artifacts(result, out_docs=tmp_path / "docs", out_art=tmp_path / "art")
    on_disk = json.loads((tmp_path / "docs" / "ml-metrics.json").read_text(encoding="utf-8"))
    assert list(on_disk.keys()) == tr.METRICS_JSON_KEYS
    shape = _shape(on_disk)
    assert shape["baselines"] == {
        "majority": {k: "float" for k in ("precision", "recall", "f1", "pr_auc")},
        "logistic_regression": {k: "float" for k in ("precision", "recall", "f1", "pr_auc")},
    }
    assert shape["metrics"] == {
        k: "float" for k in ("precision", "recall", "f1", "pr_auc", "std_between_folds")
    }
    assert shape["feature_importances"] == {c: "float" for c in tr.FEATURE_COLUMNS}
    for key in ("status", "model_version", "trained_at", "target", "validation", "notes"):
        assert shape[key] == "str"
    assert shape["features"] == ["str", "str", "str"]
    assert shape["n_samples"] == "int" and shape["n_asteroids"] == "int"
    assert "exploratoria posterior" in on_disk["notes"].lower()


def test_exploratory_does_not_change_published_metrics(result):
    ex = result["exploratory"]["pooled"]
    for name in ("rf", "logreg", "neg_h"):
        assert 0.0 <= ex[name]["pr_auc"] <= 1.0
        assert len(ex[name]["points"]) == 2
    s = result["cv"]["summary"]["rf"]
    assert set(s) >= {"precision", "recall", "f1", "pr_auc", "f1_std"}
