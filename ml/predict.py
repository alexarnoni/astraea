"""
ml/predict.py — Carrega o modelo treinado e executa scoring batch em mart.mart_asteroids.

Uso:
    python ml/predict.py          (a partir da raiz do projeto)
    python predict.py             (a partir de dentro de ml/)
"""

import os
import sys
import unicodedata
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


def _validate_and_map_classes(model) -> dict[str, int]:
    """Retorna mapeamento {'baixo': idx, 'medio': idx, 'alto': idx}.

    Normaliza acentos de ``model.classes_`` para encontrar os índices
    corretos independentemente de o modelo retornar 'médio' ou 'medio'.
    Lança ``ValueError`` se não houver exatamente 3 classes mapeáveis.
    """
    canonical = {"baixo", "medio", "alto"}
    mapping: dict[str, int] = {}

    for idx, cls in enumerate(model.classes_):
        # Remove acentos: NFD decompõe, depois filtra combining characters
        normalized = "".join(
            ch
            for ch in unicodedata.normalize("NFD", str(cls).lower())
            if unicodedata.category(ch) != "Mn"
        )
        if normalized in canonical:
            mapping[normalized] = idx

    if set(mapping.keys()) != canonical:
        found = list(model.classes_)
        raise ValueError(
            f"Esperadas exatamente 3 classes mapeáveis (baixo, medio, alto), "
            f"mas model.classes_ contém: {found}"
        )

    return mapping


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
        "SELECT neo_id, feed_date, miss_distance_lunar, relative_velocity_km_s, "
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

        # 5. Validar classes e obter índices
        class_map = _validate_and_map_classes(model)
        idx_baixo = class_map["baixo"]
        idx_medio = class_map["medio"]
        idx_alto = class_map["alto"]

        probas = model.predict_proba(X)
        predicted_classes = model.predict(X)

        risk_proba_baixo = probas[:, idx_baixo]
        risk_proba_medio = probas[:, idx_medio]
        risk_proba_alto = probas[:, idx_alto]
        risk_labels = predicted_classes

        # 6. Montar lista de dicts para batch update
        records = [
            {
                "neo_id": neo_id,
                "feed_date": feed_date,
                "risk_proba_baixo": float(pb),
                "risk_proba_medio": float(pm),
                "risk_proba_alto": float(pa),
                "risk_label_ml": str(label),
            }
            for neo_id, feed_date, pb, pm, pa, label in zip(
                df["neo_id"], df["feed_date"],
                risk_proba_baixo, risk_proba_medio, risk_proba_alto,
                risk_labels,
            )
        ]

        # 7. Executar UPDATE em batch
        conn.execute(
            text(
                "UPDATE mart.mart_asteroids "
                "SET risk_proba_baixo = :risk_proba_baixo, "
                "    risk_proba_medio = :risk_proba_medio, "
                "    risk_proba_alto = :risk_proba_alto, "
                "    risk_label_ml = :risk_label_ml "
                "WHERE neo_id = :neo_id AND feed_date = :feed_date"
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
