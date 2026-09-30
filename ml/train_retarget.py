"""
ml/train_retarget.py, fase 1 do retarget: mede e propoe, nao toca em producao.

Alvo: is_potentially_hazardous (flag da NASA), com as features
relative_velocity_km_s, miss_distance_lunar, absolute_magnitude_h.

Todas as saidas vao para ml/artifacts_retarget/ e docs/. Nada em ml/models/.

Decisoes de configuracao (fixadas ANTES de rodar, proibido ajustar depois):
  - RandomForestClassifier com os mesmos hiperparametros do train.py atual
    (n_estimators=100, random_state=42, class_weight="balanced")
  - threshold fixo de 0.5 (predict_proba[:, 1] >= 0.5)
  - StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42), grupos = neo_id
  - temporal: 80% das datas distintas de feed_date para treino, 20% mais recentes
    para teste; variante sem neo_id sobrepostos so e reportada com >= 10 positivos
  - permutation importance: n_repeats=10, scoring=average_precision, random_state=42
  - linhas com nulo em qualquer uma das 3 features sao descartadas (contadas)

Uso:
    python ml/train_retarget.py                       (le DATABASE_URL do .env)
    python ml/train_retarget.py --input-csv dump.csv  (export local de mart_asteroids)
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.stats import spearmanr
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_ML_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _ML_DIR.parent
_DOTENV_PATH = _ROOT_DIR / ".env"
ARTIFACTS_DIR = _ML_DIR / "artifacts_retarget"
DOCS_DIR = _ROOT_DIR / "docs"

TARGET_COLUMN = "is_potentially_hazardous"
FEATURE_COLUMNS = [
    "relative_velocity_km_s",
    "miss_distance_lunar",
    "absolute_magnitude_h",
]
DIAMETER_COLUMN = "diameter_avg_km"

MODEL_VERSION = "2.0.0"  # esquema semver do metadata.json atual (1.0.0), alvo novo = major
SEED = 42
N_SPLITS = 5
THRESHOLD = 0.5
TEMPORAL_TRAIN_FRACTION = 0.80
MIN_POSITIVES_FOR_VARIANT = 10
PERM_REPEATS = 10

RF_PARAMS = {"n_estimators": 100, "random_state": 42, "class_weight": "balanced"}

METRICS_JSON_KEYS = [
    "status",
    "model_version",
    "trained_at",
    "target",
    "features",
    "validation",
    "n_samples",
    "n_asteroids",
    "baselines",
    "metrics",
    "feature_importances",
    "notes",
]


# ---------------------------------------------------------------- dados

def _make_engine(database_url: str):
    from sqlalchemy import create_engine

    url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
    url = url.replace("postgresql+psycopg2://", "postgresql+pg8000://", 1)
    return create_engine(url)


def load_from_db(database_url: str) -> pd.DataFrame:
    from sqlalchemy import text

    query = text(
        "SELECT neo_id, feed_date, miss_distance_lunar, relative_velocity_km_s, "
        "estimated_diameter_min_km, estimated_diameter_max_km, "
        "absolute_magnitude_h, is_potentially_hazardous "
        "FROM mart.mart_asteroids"
    )
    with _make_engine(database_url).connect() as conn:
        return pd.read_sql(query, conn)


def _to_flag(col: pd.Series) -> pd.Series:
    """Converte bool ou texto (t/f, true/false, 1/0) em 0/1. Falha em valor desconhecido."""
    if col.dtype == bool:
        return col.astype(int)
    mapping = {"t": 1, "true": 1, "1": 1, "f": 0, "false": 0, "0": 0}
    out = col.astype(str).str.strip().str.lower().map(mapping)
    if out.isna().any():
        raise ValueError("valores inesperados em is_potentially_hazardous")
    return out.astype(int)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if DIAMETER_COLUMN not in df.columns:
        df[DIAMETER_COLUMN] = (
            df["estimated_diameter_min_km"] + df["estimated_diameter_max_km"]
        ) / 2
    for col in FEATURE_COLUMNS + [DIAMETER_COLUMN]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    df[TARGET_COLUMN] = _to_flag(df[TARGET_COLUMN])
    df["feed_date"] = pd.to_datetime(df["feed_date"])
    df["neo_id"] = df["neo_id"].astype(str)
    return df


def data_checks(df: pd.DataFrame) -> dict:
    """Verificacoes (a) a (d) pedidas antes do treino, sobre os dados brutos."""
    per_asteroid = df.groupby("neo_id")[TARGET_COLUMN].agg(["nunique", "max", "mean"])
    n_varies = int((per_asteroid["nunique"] > 1).sum())
    return {
        "n_rows_raw": int(len(df)),
        "n_asteroids_raw": int(df["neo_id"].nunique()),
        "flag_varies_within_asteroid": n_varies,
        "flag_constant_per_asteroid": bool(n_varies == 0),
        "prevalence_rows": float(df[TARGET_COLUMN].mean()),
        "n_positive_rows": int(df[TARGET_COLUMN].sum()),
        "prevalence_asteroids_ever_positive": float(per_asteroid["max"].mean()),
        "n_positive_asteroids_ever": int(per_asteroid["max"].sum()),
        "nulls": {c: int(df[c].isna().sum()) for c in FEATURE_COLUMNS + [DIAMETER_COLUMN]},
        "feed_date_min": str(df["feed_date"].min().date()),
        "feed_date_max": str(df["feed_date"].max().date()),
    }


# ---------------------------------------------------------------- modelos

def make_rf() -> RandomForestClassifier:
    return RandomForestClassifier(**RF_PARAMS)


def make_majority() -> DummyClassifier:
    return DummyClassifier(strategy="most_frequent")


def make_logreg() -> Pipeline:
    return Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression())])


def _score(model, X: pd.DataFrame) -> np.ndarray:
    proba = model.predict_proba(X)
    classes = list(model.classes_)
    if 1 not in classes:
        return np.zeros(len(X))
    return proba[:, classes.index(1)]


def evaluate(model, X_tr, y_tr, X_te, y_te) -> dict:
    """Ajusta e avalia no teste com threshold fixo 0.5. Classe positiva = 1."""
    model.fit(X_tr, y_tr)
    score = _score(model, X_te)
    pred = (score >= THRESHOLD).astype(int)
    cm = confusion_matrix(y_te, pred, labels=[0, 1])
    n_pos = int(y_te.sum())
    return {
        "precision": float(precision_score(y_te, pred, zero_division=0)),
        "recall": float(recall_score(y_te, pred, zero_division=0)),
        "f1": float(f1_score(y_te, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_te, score)) if n_pos > 0 else float("nan"),
        "prevalence": float(y_te.mean()),
        "n_test": int(len(y_te)),
        "n_test_positive": n_pos,
        "confusion_matrix": cm.tolist(),  # [[tn, fp], [fn, tp]]
        "_fitted": model,
        "_score": score,
    }


def _public(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _mean_std(rows: list[dict], keys=("precision", "recall", "f1", "pr_auc")) -> dict:
    out = {}
    for k in keys:
        vals = np.array([r[k] for r in rows], dtype=float)
        out[k] = float(np.nanmean(vals))
        out[k + "_std"] = float(np.nanstd(vals, ddof=0))
    return out


# ---------------------------------------------------------------- validacao

def make_folds(df: pd.DataFrame, seed: int = SEED) -> list[tuple[np.ndarray, np.ndarray]]:
    sgkf = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=seed)
    return list(sgkf.split(df[FEATURE_COLUMNS], df[TARGET_COLUMN], groups=df["neo_id"]))


def check_folds(df: pd.DataFrame, folds, warns: list[str]) -> None:
    for i, (tr, te) in enumerate(folds, start=1):
        overlap = set(df["neo_id"].iloc[tr]) & set(df["neo_id"].iloc[te])
        if overlap:
            raise AssertionError(f"fold {i}: {len(overlap)} neo_id em treino e teste")
        if int(df[TARGET_COLUMN].iloc[te].sum()) == 0:
            warns.append(f"fold {i}: teste sem positivos")


def run_cv(df: pd.DataFrame, folds, warns: list[str]) -> dict:
    y = df[TARGET_COLUMN]
    X3 = df[FEATURE_COLUMNS]
    X4 = df[FEATURE_COLUMNS + [DIAMETER_COLUMN]]

    per = {"rf": [], "majority": [], "logreg": [], "rf_with_diameter": []}
    fi_rows, perm_rows = [], []

    for i, (tr, te) in enumerate(folds, start=1):
        y_tr, y_te = y.iloc[tr], y.iloc[te]
        if y_tr.nunique() < 2:
            warns.append(f"fold {i}: treino com uma unica classe")

        rf = evaluate(make_rf(), X3.iloc[tr], y_tr, X3.iloc[te], y_te)
        per["rf"].append(rf)
        per["majority"].append(evaluate(make_majority(), X3.iloc[tr], y_tr, X3.iloc[te], y_te))
        per["logreg"].append(evaluate(make_logreg(), X3.iloc[tr], y_tr, X3.iloc[te], y_te))
        per["rf_with_diameter"].append(
            evaluate(make_rf(), X4.iloc[tr], y_tr, X4.iloc[te], y_te)
        )

        fitted = rf["_fitted"]
        fi_rows.append(dict(zip(FEATURE_COLUMNS, fitted.feature_importances_)))
        if int(y_te.sum()) > 0:
            pi = permutation_importance(
                fitted, X3.iloc[te], y_te, scoring="average_precision",
                n_repeats=PERM_REPEATS, random_state=SEED, n_jobs=1,
            )
            perm_rows.append(dict(zip(FEATURE_COLUMNS, pi.importances_mean)))

    fi_mean = {c: float(np.mean([r[c] for r in fi_rows])) for c in FEATURE_COLUMNS}
    perm_mean = {c: float(np.mean([r[c] for r in perm_rows])) for c in FEATURE_COLUMNS}
    perm_std = {c: float(np.std([r[c] for r in perm_rows])) for c in FEATURE_COLUMNS}

    total_cm = {
        name: np.sum([r["confusion_matrix"] for r in rows], axis=0).tolist()
        for name, rows in per.items()
    }
    oof = {}
    for name in ("rf", "logreg"):
        arr = np.full(len(df), np.nan)
        for (_, te), r in zip(folds, per[name]):
            arr[te] = r["_score"]
        oof[name] = arr

    return {
        "_oof": oof,
        "per_fold": {k: [_public(r) for r in v] for k, v in per.items()},
        "summary": {k: _mean_std(v) for k, v in per.items()},
        "confusion_total": total_cm,
        "feature_importances": fi_mean,
        "permutation_importance_mean": perm_mean,
        "permutation_importance_std": perm_std,
    }


def run_temporal(df: pd.DataFrame, warns: list[str]) -> dict:
    dates = np.sort(df["feed_date"].unique())
    cut_idx = int(len(dates) * TEMPORAL_TRAIN_FRACTION)
    if cut_idx >= len(dates) or cut_idx == 0:
        return {"available": False, "reason": "datas distintas insuficientes"}
    cutoff = dates[cut_idx]
    train = df[df["feed_date"] < cutoff]
    test = df[df["feed_date"] >= cutoff]
    out = {
        "available": True,
        "cutoff_date": str(pd.Timestamp(cutoff).date()),
        "n_dates_train": int(cut_idx),
        "n_dates_test": int(len(dates) - cut_idx),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "n_test_positive": int(test[TARGET_COLUMN].sum()),
    }
    if train[TARGET_COLUMN].nunique() < 2 or test[TARGET_COLUMN].sum() == 0:
        warns.append("temporal: treino sem duas classes ou teste sem positivos")
        out["available"] = False
        out["reason"] = "sem positivos suficientes no corte temporal"
        return out

    train_ids = set(train["neo_id"])
    overlap_mask = test["neo_id"].isin(train_ids)
    out["n_test_asteroids"] = int(test["neo_id"].nunique())
    out["n_test_asteroids_in_train"] = int(test.loc[overlap_mask, "neo_id"].nunique())
    out["n_test_rows_in_train_asteroids"] = int(overlap_mask.sum())

    def run(test_df: pd.DataFrame, keep: dict | None = None) -> dict:
        res = {}
        for name, factory in (("rf", make_rf), ("majority", make_majority), ("logreg", make_logreg)):
            r = evaluate(factory(), train[FEATURE_COLUMNS], train[TARGET_COLUMN],
                         test_df[FEATURE_COLUMNS], test_df[TARGET_COLUMN])
            res[name] = _public(r)
            if keep is not None:
                keep[name] = r["_score"]
        return res

    kept: dict = {}
    out["all_test_rows"] = run(test, kept)
    out["_test_scores"] = kept
    out["_test_index"] = test.index.to_numpy()
    new_only = test[~overlap_mask]
    out["n_test_new_only"] = int(len(new_only))
    out["n_test_new_only_positive"] = int(new_only[TARGET_COLUMN].sum())
    if out["n_test_new_only_positive"] >= MIN_POSITIVES_FOR_VARIANT:
        out["new_asteroids_only"] = run(new_only)
    else:
        out["new_asteroids_only"] = None
        out["new_only_reason"] = (
            f"apenas {out['n_test_new_only_positive']} positivos "
            f"(minimo {MIN_POSITIVES_FOR_VARIANT})"
        )
    return out


def diameter_analysis(df: pd.DataFrame, cv: dict) -> dict:
    sub = df[["absolute_magnitude_h", DIAMETER_COLUMN]].dropna()
    rho, p = spearmanr(sub["absolute_magnitude_h"], sub[DIAMETER_COLUMN])
    return {
        "spearman_rho_diameter_vs_h": float(rho),
        "spearman_p": float(p),
        "n_pairs": int(len(sub)),
        "without_diameter": {k: cv["summary"]["rf"][k] for k in ("precision", "recall", "f1", "pr_auc")},
        "with_diameter": {k: cv["summary"]["rf_with_diameter"][k] for k in ("precision", "recall", "f1", "pr_auc")},
    }


# ---------------------------------------------------------------- referencia H <= 22

# Referencia acrescentada DEPOIS da primeira execucao. Sem ajuste: o corte 22 foi
# dado, nao escolhido a partir dos dados. Nao entra em metrics nem em baselines.
REFERENCE_H_CUTOFF = 22.0


def _rule_eval(sub: pd.DataFrame) -> dict:
    y = sub[TARGET_COLUMN]
    pred = (sub["absolute_magnitude_h"] <= REFERENCE_H_CUTOFF).astype(int)
    return {
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }


def run_reference_rule(df: pd.DataFrame, folds, temporal: dict) -> dict:
    per_fold = [_rule_eval(df.iloc[te]) for _, te in folds]
    keys = ("precision", "recall", "f1")
    summary = {}
    for k in keys:
        vals = np.array([r[k] for r in per_fold])
        summary[k] = float(vals.mean())
        summary[k + "_std"] = float(vals.std(ddof=0))
    out = {
        "cutoff": REFERENCE_H_CUTOFF,
        "per_fold": per_fold,
        "summary": summary,
        "confusion_total": np.sum([r["confusion_matrix"] for r in per_fold], axis=0).tolist(),
        "temporal": None,
        "temporal_new_only": None,
    }
    if temporal.get("available"):
        cutoff = pd.Timestamp(temporal["cutoff_date"])
        test = df[df["feed_date"] >= cutoff]
        train_ids = set(df.loc[df["feed_date"] < cutoff, "neo_id"])
        out["temporal"] = _rule_eval(test)
        new_only = test[~test["neo_id"].isin(train_ids)]
        if int(new_only[TARGET_COLUMN].sum()) >= MIN_POSITIVES_FOR_VARIANT:
            out["temporal_new_only"] = _rule_eval(new_only)
    return out


# ---------------------------------------------------------------- exploratoria posterior

# Analise exploratoria acrescentada depois da primeira execucao. Nao altera nenhuma
# metrica publicada: apenas rele as pontuacoes fora da amostra ja geradas.
EXPLORATORY_RECALLS = (0.95, 0.99)


def _operating_point(y: np.ndarray, score: np.ndarray, min_recall: float) -> dict:
    """Maior precisao com recall >= min_recall na curva precisao-recall.

    Empate de precisao: fica o maior threshold. Threshold so descreve o ponto.
    """
    prec, rec, thr = precision_recall_curve(y, score)
    prec, rec = prec[:-1], rec[:-1]  # alinha com thr
    ok = rec >= min_recall
    if not ok.any():
        return {"min_recall": min_recall, "reachable": False}
    best = prec[ok].max()
    cand = np.where(ok & (prec == best))[0]
    i = cand[np.argmax(thr[cand])]
    pred = (score >= thr[i]).astype(int)
    return {
        "min_recall": min_recall,
        "reachable": True,
        "precision": float(prec[i]),
        "recall": float(rec[i]),
        "threshold": float(thr[i]),
        "n_flagged": int(pred.sum()),
        "n_positive": int(np.sum(y)),
    }


def _score_block(y: np.ndarray, scores: dict) -> dict:
    out = {}
    for name, sc in scores.items():
        out[name] = {
            "pr_auc": float(average_precision_score(y, sc)),
            "points": [_operating_point(y, sc, r) for r in EXPLORATORY_RECALLS],
        }
    return out


def run_exploratory(df: pd.DataFrame, cv: dict, temporal: dict) -> dict:
    y = df[TARGET_COLUMN].to_numpy()
    h_score = -df["absolute_magnitude_h"].to_numpy()
    oof = cv["_oof"]
    assert not np.isnan(oof["rf"]).any() and not np.isnan(oof["logreg"]).any()
    out = {
        "pooled": _score_block(
            y, {"rf": oof["rf"], "logreg": oof["logreg"], "neg_h": h_score}
        ),
        "pooled_rule_precision": float(_rule_eval(df)["precision"]),
        "temporal": None,
    }
    if temporal.get("available") and "_test_scores" in temporal:
        idx = temporal["_test_index"]
        ty = df.loc[idx, TARGET_COLUMN].to_numpy()
        ts = dict(temporal["_test_scores"])
        ts["neg_h"] = -df.loc[idx, "absolute_magnitude_h"].to_numpy()
        out["temporal"] = _score_block(ty, ts)
        out["temporal"]["rule_precision"] = float(_rule_eval(df.loc[idx])["precision"])
    return out


# ---------------------------------------------------------------- experimento

def run_experiment(df_raw: pd.DataFrame, seed: int = SEED) -> dict:
    warns: list[str] = []
    df = prepare(df_raw)
    checks = data_checks(df)

    df = df.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
    checks["n_rows_dropped_null_features"] = checks["n_rows_raw"] - len(df)
    n_samples, n_asteroids = int(len(df)), int(df["neo_id"].nunique())

    prev = float(df[TARGET_COLUMN].mean())
    if prev < 0.2 or prev > 0.8:
        warns.append(f"desbalanceamento: prevalencia da classe positiva = {prev:.4f}")
    if not checks["flag_constant_per_asteroid"]:
        warns.append(
            f"a flag varia dentro do mesmo asteroide em {checks['flag_varies_within_asteroid']} neo_id"
        )
    if n_samples < N_SPLITS * 20:
        warns.append(f"poucas amostras: {n_samples}")

    folds = make_folds(df, seed)
    check_folds(df, folds, warns)

    cv = run_cv(df, folds, warns)
    temporal = run_temporal(df, warns)
    diam = diameter_analysis(df, cv)
    reference = run_reference_rule(df, folds, temporal)
    exploratory = run_exploratory(df, cv, temporal)

    return {
        "df": df,
        "checks": checks,
        "n_samples": n_samples,
        "n_asteroids": n_asteroids,
        "cv": cv,
        "temporal": temporal,
        "diameter": diam,
        "reference": reference,
        "exploratory": exploratory,
        "warnings": warns,
        "seed": seed,
    }


# ---------------------------------------------------------------- artefatos

def _f(x: float, nd: int = 4) -> str:
    return "nan" if x != x else f"{x:.{nd}f}"


def build_notes(res: dict) -> str:
    s = res["cv"]["summary"]
    t = res["temporal"]
    d = res["diameter"]
    parts = [
        "Threshold fixo 0.5, sem tuning.",
        "Hiperparametros do RandomForest herdados do train.py atual "
        "(n_estimators=100, random_state=42, class_weight=balanced), so o alvo mudou.",
        f"Diametro: Spearman entre diameter_avg_km e absolute_magnitude_h = "
        f"{_f(d['spearman_rho_diameter_vs_h'])}. F1 sem diameter {_f(d['without_diameter']['f1'])}, "
        f"com diameter {_f(d['with_diameter']['f1'])}; PR-AUC sem {_f(d['without_diameter']['pr_auc'])}, "
        f"com {_f(d['with_diameter']['pr_auc'])}. Conjunto final segue sem diameter_avg_km.",
    ]
    if t.get("available"):
        rf = t["all_test_rows"]["rf"]
        txt = (
            f"Temporal (corte em {t['cutoff_date']}): F1 {_f(rf['f1'])}, PR-AUC {_f(rf['pr_auc'])}, "
            f"prevalencia no teste {_f(rf['prevalence'])}; "
            f"{t['n_test_asteroids_in_train']} de {t['n_test_asteroids']} neo_id do teste tambem aparecem no treino."
        )
        if t.get("new_asteroids_only"):
            n = t["new_asteroids_only"]["rf"]
            txt += f" Sem neo_id sobrepostos: F1 {_f(n['f1'])}, PR-AUC {_f(n['pr_auc'])}."
        else:
            txt += f" Variante sem neo_id sobrepostos nao reportada: {t.get('new_only_reason', 'indisponivel')}."
        parts.append(txt)
    else:
        parts.append(f"Avaliacao temporal indisponivel: {t.get('reason')}.")
    parts.append(
        "Limitacao: a flag da NASA e definida por H (absolute_magnitude_h) e pela MOID "
        "(distancia minima de intersecao orbital, limite de 0,05 UA); a MOID nao e feature, "
        "entao o modelo aproxima a flag sem ver o determinante orbital."
    )
    parts.append(
        "miss_distance_lunar e a distancia de uma aproximacao especifica, nao a MOID nem uma "
        "propriedade estavel do asteroide."
    )
    parts.append("Unidade de avaliacao: linha (aproximacao), o que aproxima a avaliacao por asteroide.")
    r = res["reference"]
    rs = r["summary"]
    ref_txt = (
        f"Referencia acrescentada depois da primeira execucao, sem ajuste: regra "
        f"absolute_magnitude_h <= {r['cutoff']:g} como preditor da flag, nos mesmos folds: "
        f"precisao {_f(rs['precision'])}, recall {_f(rs['recall'])}, F1 {_f(rs['f1'])}"
    )
    if r["temporal"]:
        t_ = r["temporal"]
        ref_txt += (
            f"; no teste temporal: precisao {_f(t_['precision'])}, recall {_f(t_['recall'])}, "
            f"F1 {_f(t_['f1'])}"
        )
    parts.append(ref_txt + ".")
    e = res["exploratory"]["pooled"]
    p95, p99 = e["rf"]["points"]
    parts.append(
        "Analise exploratoria posterior, fora do plano original, sobre as probabilidades "
        f"fora da amostra agrupadas: PR-AUC de -H sem treino {_f(e['neg_h']['pr_auc'])} "
        f"(RF agrupado {_f(e['rf']['pr_auc'])}); precisao maxima do RF com recall >= 0.95: "
        f"{_f(p95['precision'])}, com recall >= 0.99: {_f(p99['precision'])} "
        "(regra H <= 22: 0.3900)."
    )
    if res["warnings"]:
        parts.append("Avisos: " + "; ".join(res["warnings"]) + ".")
    return " ".join(parts)


def build_metrics_json(res: dict, trained_at: str) -> dict:
    s = res["cv"]["summary"]
    keys = ("precision", "recall", "f1", "pr_auc")
    return {
        "status": "retargeted",
        "model_version": MODEL_VERSION,
        "trained_at": trained_at,
        "target": TARGET_COLUMN,
        "features": list(FEATURE_COLUMNS),
        "validation": (
            f"StratifiedGroupKFold({N_SPLITS}) por neo_id, shuffle, seed {res['seed']}; "
            "media entre folds; unidade de avaliacao: linha"
        ),
        "n_samples": res["n_samples"],
        "n_asteroids": res["n_asteroids"],
        "baselines": {
            "majority": {k: s["majority"][k] for k in keys},
            "logistic_regression": {k: s["logreg"][k] for k in keys},
        },
        "metrics": {
            **{k: s["rf"][k] for k in keys},
            "std_between_folds": s["rf"]["f1_std"],
        },
        "feature_importances": res["cv"]["feature_importances"],
        "notes": build_notes(res),
    }


def _cm_text(cm) -> str:
    (tn, fp), (fn, tp) = cm
    return f"tn={tn} fp={fp} fn={fn} tp={tp}"


def build_report(res: dict, trained_at: str) -> str:
    c, cv, t, d = res["checks"], res["cv"], res["temporal"], res["diameter"]
    L = []
    L.append("Astraea, relatorio do retarget do ML (fase 1)")
    L.append("=" * 46)
    L.append(f"Gerado em {trained_at}. Alvo: {TARGET_COLUMN}. Features: {', '.join(FEATURE_COLUMNS)}.")
    L.append("Nada aqui foi ajustado para melhorar metrica. Configuracao fixada antes da execucao.")
    L.append("")
    L.append("1. Dados e prevalencia")
    L.append(f"- linhas brutas: {c['n_rows_raw']}, asteroides (neo_id) distintos: {c['n_asteroids_raw']}")
    L.append(f"- linhas usadas (sem nulos nas features): {res['n_samples']}, asteroides: {res['n_asteroids']}")
    L.append(f"- periodo: {c['feed_date_min']} a {c['feed_date_max']}")
    L.append(f"- flag constante por neo_id: {'sim' if c['flag_constant_per_asteroid'] else 'nao'} "
             f"({c['flag_varies_within_asteroid']} neo_id com valores diferentes)")
    L.append(f"- prevalencia por linha: {_f(c['prevalence_rows'])} ({c['n_positive_rows']} linhas positivas)")
    L.append(f"- prevalencia por asteroide (ja positivo em alguma linha): "
             f"{_f(c['prevalence_asteroids_ever_positive'])} ({c['n_positive_asteroids_ever']} asteroides)")
    L.append(f"- nulos: {json.dumps(c['nulls'])}; linhas descartadas por nulo: {c['n_rows_dropped_null_features']}")
    L.append("")
    L.append("2. Metricas por fold (classe positiva, threshold 0.5)")
    names = {"rf": "RandomForest", "logreg": "Regressao logistica", "majority": "Classe majoritaria"}
    for key, title in names.items():
        L.append(f"{title}:")
        for i, r in enumerate(cv["per_fold"][key], start=1):
            L.append(f"  fold {i}: P={_f(r['precision'])} R={_f(r['recall'])} F1={_f(r['f1'])} "
                     f"PR-AUC={_f(r['pr_auc'])} n_teste={r['n_test']} positivos={r['n_test_positive']} "
                     f"| {_cm_text(r['confusion_matrix'])}")
        s = cv["summary"][key]
        L.append(f"  media (desvio): P={_f(s['precision'])} ({_f(s['precision_std'])}) "
                 f"R={_f(s['recall'])} ({_f(s['recall_std'])}) F1={_f(s['f1'])} ({_f(s['f1_std'])}) "
                 f"PR-AUC={_f(s['pr_auc'])} ({_f(s['pr_auc_std'])})")
        L.append(f"  matriz agregada (soma dos folds): {_cm_text(cv['confusion_total'][key])}")
    mean_prev = float(np.mean([r["prevalence"] for r in cv["per_fold"]["majority"]]))
    L.append(f"Nota: para o majoritario o score e constante, entao PR-AUC = prevalencia do fold "
             f"(media {_f(mean_prev)}; PR-AUC medio medido {_f(cv['summary']['majority']['pr_auc'])}).")
    L.append("")
    L.append("3. Avaliacao temporal")
    if t.get("available"):
        L.append(f"- corte por data: {t['cutoff_date']} (treino {t['n_dates_train']} datas, "
                 f"teste {t['n_dates_test']} datas); linhas treino {t['n_train']}, teste {t['n_test']}, "
                 f"positivos no teste {t['n_test_positive']}")
        L.append(f"- neo_id do teste tambem presentes no treino: {t['n_test_asteroids_in_train']} de "
                 f"{t['n_test_asteroids']} ({t['n_test_rows_in_train_asteroids']} de {t['n_test']} linhas)")

        def block(label, blk):
            L.append(label)
            for k, title in names.items():
                r = blk[k]
                L.append(f"  {title}: P={_f(r['precision'])} R={_f(r['recall'])} F1={_f(r['f1'])} "
                         f"PR-AUC={_f(r['pr_auc'])} prevalencia={_f(r['prevalence'])} "
                         f"| {_cm_text(r['confusion_matrix'])}")

        block("- todas as linhas do teste:", t["all_test_rows"])
        if t.get("new_asteroids_only"):
            L.append(f"- teste sem neo_id vistos no treino: {t['n_test_new_only']} linhas, "
                     f"{t['n_test_new_only_positive']} positivos")
            block("  resultado:", t["new_asteroids_only"])
        else:
            L.append(f"- variante sem neo_id sobrepostos nao reportada: {t.get('new_only_reason')}")
    else:
        L.append(f"- indisponivel: {t.get('reason')}")
    L.append("")
    L.append("4. diameter_avg_km versus absolute_magnitude_h")
    L.append(f"- Spearman: rho={_f(d['spearman_rho_diameter_vs_h'])} (p={d['spearman_p']:.3g}, n={d['n_pairs']})")
    L.append("- RF sem diameter (3 features): "
             + " ".join(f"{k}={_f(v)}" for k, v in d["without_diameter"].items()))
    L.append("- RF com diameter (4 features): "
             + " ".join(f"{k}={_f(v)}" for k, v in d["with_diameter"].items()))
    L.append("- decisao registrada: conjunto final permanece sem diameter_avg_km.")
    L.append("")
    L.append("5. Importancias (RF, media entre folds)")
    L.append("Impurity:")
    for k, v in cv["feature_importances"].items():
        L.append(f"  {k}: {_f(v)}")
    L.append("Permutation (queda de PR-AUC no teste, media entre folds, desvio entre folds):")
    for k in FEATURE_COLUMNS:
        L.append(f"  {k}: {_f(cv['permutation_importance_mean'][k])} ({_f(cv['permutation_importance_std'][k])})")
    L.append("")
    L.append("6. Referencia: regra H <= 22 (acrescentada depois da primeira execucao, sem ajuste)")
    ref = res["reference"]
    L.append("Regra binaria: prediz positivo quando absolute_magnitude_h <= 22. PR-AUC nao se aplica.")
    for i, r in enumerate(ref["per_fold"], start=1):
        L.append(f"  fold {i}: P={_f(r['precision'])} R={_f(r['recall'])} F1={_f(r['f1'])} "
                 f"| {_cm_text(r['confusion_matrix'])}")
    rs = ref["summary"]
    L.append(f"  media (desvio): P={_f(rs['precision'])} ({_f(rs['precision_std'])}) "
             f"R={_f(rs['recall'])} ({_f(rs['recall_std'])}) F1={_f(rs['f1'])} ({_f(rs['f1_std'])})")
    L.append(f"  matriz agregada (soma dos folds): {_cm_text(ref['confusion_total'])}")
    if ref["temporal"]:
        r = ref["temporal"]
        L.append(f"- temporal, todas as linhas do teste: P={_f(r['precision'])} R={_f(r['recall'])} "
                 f"F1={_f(r['f1'])} | {_cm_text(r['confusion_matrix'])}")
        if ref["temporal_new_only"]:
            r = ref["temporal_new_only"]
            L.append(f"- temporal, sem neo_id vistos no treino: P={_f(r['precision'])} "
                     f"R={_f(r['recall'])} F1={_f(r['f1'])} | {_cm_text(r['confusion_matrix'])}")
    L.append("")
    L.append("7. Avisos")
    if res["warnings"]:
        L.extend(f"- {w}" for w in res["warnings"])
    else:
        L.append("- nenhum")
    L.append("")
    L.append("8. Limitacoes")
    L.append("- A flag da NASA depende de H e da MOID (0,05 UA); a MOID nao e feature.")
    L.append("- miss_distance_lunar e a distancia de uma aproximacao especifica.")
    L.append("- Unidade de avaliacao e a linha; o mesmo asteroide tem varias linhas, "
             "por isso os folds agrupam por neo_id.")
    ex = res["exploratory"]
    L.append("")
    L.append("9. Analise exploratoria posterior (nao fez parte do plano original)")
    L.append("Acrescentada depois da primeira execucao. Nao altera nenhuma metrica das secoes 1 a 8.")
    L.append("Usa as probabilidades fora da amostra (out-of-fold) dos mesmos 5 folds (mesma seed), juntas em um conjunto.")
    L.append("Cada fold vem de um modelo diferente, entao o conjunto agrupado nao e o mesmo que a media dos folds.")
    L.append("Pontuacao -H: pontuacao = -absolute_magnitude_h, sem treinar nada.")
    labels = {"rf": "RandomForest", "logreg": "Regressao logistica", "neg_h": "-H (sem treino)"}

    def expl_block(title, blk, extra):
        L.append(title)
        for k, lab in labels.items():
            L.append(f"  {lab}: PR-AUC={_f(blk[k]['pr_auc'])}")
            for pt in blk[k]["points"]:
                if not pt["reachable"]:
                    L.append(f"    recall >= {pt['min_recall']}: inalcancavel")
                    continue
                L.append(f"    recall >= {pt['min_recall']}: maior precisao={_f(pt['precision'])} "
                         f"(recall={_f(pt['recall'])}, threshold={_f(pt['threshold'], 4)}, "
                         f"{pt['n_flagged']} sinalizados para {pt['n_positive']} positivos)")
        L.append(extra)

    expl_block(
        "9.1 e 9.2 Conjunto agrupado dos 5 folds:", ex["pooled"],
        f"  Regra H <= 22 no conjunto agrupado: precisao={_f(ex['pooled_rule_precision'])} "
        "(a media entre folds publicada e 0.3900).",
    )
    L.append(f"  Para comparar: PR-AUC do RF (media entre folds) = {_f(cv['summary']['rf']['pr_auc'])}, "
             f"regressao logistica = {_f(cv['summary']['logreg']['pr_auc'])}.")
    if ex["temporal"]:
        te = dict(ex["temporal"])
        rule_p = te.pop("rule_precision")
        expl_block("9.3 Split temporal (treino antigo, teste recente):", te,
                   f"  Regra H <= 22 no teste temporal: precisao={_f(rule_p)}.")
    else:
        L.append("9.3 Split temporal: indisponivel.")
    oof_rf = res["cv"]["_oof"]["rf"]
    y_all = res["df"][TARGET_COLUMN].to_numpy()
    n_zero_pos = int(((oof_rf == 0) & (y_all == 1)).sum())
    L.append(f"Nota sobre o RF com recall >= 0.99: no conjunto agrupado, {n_zero_pos} de {int(y_all.sum())} "
             "positivos recebem probabilidade exatamente 0 do RF. Alcancar esse recall exige incluir todo "
             "o conjunto (threshold 0), e a precisao cai para a prevalencia. Isso descreve a granularidade "
             "das probabilidades do RF, nao um ajuste.")
    L.append("Leitura: descricao apenas. Thresholds dos pontos de operacao sao lidos da curva e nao foram "
             "usados para escolher nem ajustar modelo. Com poucas centenas de positivos, as diferencas "
             "pequenas de precisao entre pontos vizinhos da curva sao instaveis.")
    return "\n".join(L) + "\n"


def write_artifacts(res: dict, out_docs: Path = DOCS_DIR, out_art: Path = ARTIFACTS_DIR) -> dict:
    trained_at = datetime.now(timezone.utc).isoformat()
    metrics = build_metrics_json(res, trained_at)
    out_docs.mkdir(parents=True, exist_ok=True)
    out_art.mkdir(parents=True, exist_ok=True)
    (out_docs / "ml-metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_docs / "ml-report.md").write_text(build_report(res, trained_at), encoding="utf-8")

    # Modelo final (todos os dados) apenas para o rollout futuro, fora de ml/models/
    df = res["df"]
    final = make_rf().fit(df[FEATURE_COLUMNS], df[TARGET_COLUMN])
    joblib.dump(final, out_art / "pha_classifier.joblib")
    meta = {
        "model_version": MODEL_VERSION,
        "trained_at": trained_at,
        "sklearn_version": sklearn.__version__,
        "feature_columns": list(FEATURE_COLUMNS),
        "target": TARGET_COLUMN,
        "threshold": THRESHOLD,
        "training_data_range": {
            "start": res["checks"]["feed_date_min"],
            "end": res["checks"]["feed_date_max"],
        },
        "total_samples": res["n_samples"],
    }
    (out_art / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def print_summary(res: dict, metrics: dict) -> None:
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print("\nAvisos:")
    for w in res["warnings"] or ["nenhum"]:
        print(f"  - {w}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-csv", help="export local de mart.mart_asteroids (opcional)")
    args = ap.parse_args()

    if args.input_csv:
        df = pd.read_csv(args.input_csv)
    else:
        from dotenv import load_dotenv

        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                load_dotenv(dotenv_path=_DOTENV_PATH, encoding=enc, override=False)
                break
            except UnicodeDecodeError:
                continue
        url = os.getenv("DATABASE_URL")
        if not url:
            raise EnvironmentError("DATABASE_URL nao esta definida (ou use --input-csv).")
        df = load_from_db(url)

    warnings.filterwarnings("default")
    res = run_experiment(df)
    metrics = write_artifacts(res)
    print_summary(res, metrics)


if __name__ == "__main__":
    try:
        main()
    except EnvironmentError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
