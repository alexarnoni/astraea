"""
ml/predict.py — Carrega o modelo treinado e executa scoring batch em mart.mart_asteroids.

Uso:
    python ml/predict.py          (a partir da raiz do projeto)
    python predict.py             (a partir de dentro de ml/)
"""

import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Caminhos resolvidos de forma independente do diretório de execução
_ML_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _ML_DIR.parent
_DOTENV_PATH = _ROOT_DIR / ".env"
_MODEL_PATH = _ML_DIR / "models" / "risk_classifier.joblib"

FEATURE_COLUMNS = [
    "miss_distance_lunar",
    "relative_velocity_km_s",
    "diameter_avg_km",
    "absolute_magnitude_h",
    "is_potentially_hazardous",
]


def _make_engine(database_url: str):
    # Troca o driver para pg8000 (Python puro) para evitar UnicodeDecodeError
    # do psycopg2 nativo no Windows PT-BR (CP1252)
    url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
    url = url.replace("postgresql+psycopg2://", "postgresql+pg8000://", 1)
    return create_engine(url)


def run_scoring() -> None:
    """Carrega o modelo, gera predições e atualiza mart.mart_asteroids."""
    # 1. Carregar .env da raiz do projeto
    for enc in ("utf-8", "latin-1"):
        try:
            load_dotenv(dotenv_path=_DOTENV_PATH, encoding=enc, override=False)
            break
        except UnicodeDecodeError:
            continue

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise EnvironmentError(
            "DATABASE_URL não está definida. "
            "Verifique o arquivo .env na raiz do projeto."
        )

    # 2. Verificar e carregar o modelo
    if not _MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado em '{_MODEL_PATH}'. "
            "Execute 'python ml/train.py' para treinar o modelo antes de executar o scorer."
        )

    model = joblib.load(_MODEL_PATH)

    # 3. Consultar dados do mart
    engine = _make_engine(database_url)
    query = text(
        "SELECT neo_id, miss_distance_lunar, relative_velocity_km_s, "
        "estimated_diameter_min_km, estimated_diameter_max_km, "
        "absolute_magnitude_h, is_potentially_hazardous "
        "FROM mart.mart_asteroids"
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

        # 4. Pré-processar: calcular diameter_avg_km e bool → int
        df["diameter_avg_km"] = (
            df["estimated_diameter_min_km"] + df["estimated_diameter_max_km"]
        ) / 2
        df["is_potentially_hazardous"] = df["is_potentially_hazardous"].astype(int)

        X = df[FEATURE_COLUMNS]

        # 5. Gerar risk_score_ml: probabilidade da classe 'alto'
        alto_idx = list(model.classes_).index("alto")
        probas = model.predict_proba(X)
        risk_scores = probas[:, alto_idx]

        # 6. Gerar risk_label_ml: classe predita
        risk_labels = model.predict(X)

        # 7. Garantir que as colunas existam na tabela
        conn.execute(text(
            "ALTER TABLE mart.mart_asteroids "
            "ADD COLUMN IF NOT EXISTS risk_score_ml NUMERIC(6,4)"
        ))
        conn.execute(text(
            "ALTER TABLE mart.mart_asteroids "
            "ADD COLUMN IF NOT EXISTS risk_label_ml VARCHAR(10)"
        ))

        # 8. Montar lista de dicts para batch update
        records = [
            {
                "neo_id": neo_id,
                "risk_score_ml": float(score),
                "risk_label_ml": str(label),
            }
            for neo_id, score, label in zip(df["neo_id"], risk_scores, risk_labels)
        ]

        # 9. Executar UPDATE em batch
        conn.execute(
            text(
                "UPDATE mart.mart_asteroids "
                "SET risk_score_ml = :risk_score_ml, risk_label_ml = :risk_label_ml "
                "WHERE neo_id = :neo_id"
            ),
            records,
        )

        conn.commit()

    n = len(records)
    print(f"Updated {n} records.")


if __name__ == "__main__":
    try:
        run_scoring()
    except (EnvironmentError, FileNotFoundError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
