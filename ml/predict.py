"""
ml/predict.py — Carrega o modelo treinado e executa scoring batch em mart.mart_asteroids.

Uso:
    python ml/predict.py          (a partir da raiz do projeto)
    python predict.py             (a partir de dentro de ml/)
"""

import json
import os
import sys
import unicodedata
import warnings
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
_METADATA_PATH = _ML_DIR / "models" / "metadata.json"
# Modelo novo (alvo is_potentially_hazardous). Nomes proprios: nunca sobrescrevem o
# modelo legado nem o metadata.json, que a API le para informar o model_version.
_PHA_MODEL_PATH = _ML_DIR / "models" / "pha_classifier.joblib"
_PHA_METADATA_PATH = _ML_DIR / "models" / "metadata_pha.json"

FEATURE_COLUMNS = [
    "miss_distance_lunar",
    "relative_velocity_km_s",
    "diameter_avg_km",
    "absolute_magnitude_h",
    "is_potentially_hazardous",
]


def _load_pha_model():
    """Carrega o modelo PHA (2.0.0) e seu metadata.

    Retorna (model, model_version, feature_columns), ou None se os arquivos nao existem
    ou o modelo e invalido. Nunca levanta: o scoring legado nao pode depender dele.
    Avisos de versao do scikit-learn sao tratados como erro (modelo de outra versao
    pode prever errado em silencio).
    """
    if not _PHA_MODEL_PATH.exists() or not _PHA_METADATA_PATH.exists():
        print("[INFO] Modelo PHA nao encontrado. pha_probability e pha_model_version ficam NULL.")
        return None
    try:
        import joblib
        from sklearn.exceptions import InconsistentVersionWarning

        with open(_PHA_METADATA_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            model = joblib.load(_PHA_MODEL_PATH)

        features = list(meta["feature_columns"])
        version = meta["model_version"]
        if not isinstance(version, str) or not version:
            raise ValueError("model_version ausente no metadata_pha.json")
        if list(model.feature_names_in_) != features:
            raise ValueError("feature_columns do metadata difere das features do modelo")
        if 1 not in list(model.classes_):
            raise ValueError("o modelo nao tem a classe positiva 1")
    except Exception as exc:  # qualquer falha desliga so o modelo novo
        print(
            f"[ERROR] Modelo PHA invalido ({type(exc).__name__}: {exc}). "
            "Continuando sem pha_probability.",
            file=sys.stderr,
        )
        return None
    return model, version, features


def _score_pha(df, model, features) -> list:
    """Probabilidade da classe positiva por linha; None onde faltar alguma feature."""
    X = df[features].astype(float)
    ok = X.notna().all(axis=1).to_numpy()
    result: list = [None] * len(df)
    if ok.any():
        pos_idx = list(model.classes_).index(1)
        proba = model.predict_proba(X[ok])[:, pos_idx]
        it = iter(proba)
        result = [float(next(it)) if flag else None for flag in ok]
    return result


def _ml_table_has_pha_columns(conn) -> bool:
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'mart' AND table_name = 'mart_asteroids_ml' "
            "AND column_name IN ('pha_probability', 'pha_model_version')"
        )
    ).fetchall()
    return len(rows) == 2


_INSERT_LEGACY = """
    INSERT INTO mart.mart_asteroids_ml
        (neo_id, feed_date, risk_proba_baixo, risk_proba_medio, risk_proba_alto, risk_label_ml)
    VALUES (:neo_id, :feed_date, :risk_proba_baixo, :risk_proba_medio, :risk_proba_alto, :risk_label_ml)
"""

_INSERT_WITH_PHA = """
    INSERT INTO mart.mart_asteroids_ml
        (neo_id, feed_date, risk_proba_baixo, risk_proba_medio, risk_proba_alto, risk_label_ml,
         pha_probability, pha_model_version)
    VALUES (:neo_id, :feed_date, :risk_proba_baixo, :risk_proba_medio, :risk_proba_alto, :risk_label_ml,
            :pha_probability, :pha_model_version)
"""


def _make_engine(database_url: str):
    # Troca o driver para pg8000 (Python puro) para evitar UnicodeDecodeError
    # do psycopg2 nativo no Windows PT-BR (CP1252)
    url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
    url = url.replace("postgresql+psycopg2://", "postgresql+pg8000://", 1)
    return create_engine(url)


def _load_metadata() -> dict | None:
    """Carrega metadata.json. Retorna None se arquivo não existir ou JSON inválido."""
    if not _METADATA_PATH.exists():
        print("[WARNING] metadata.json não encontrado. Continuando sem metadados.")
        return None
    try:
        with open(_METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("[ERROR] metadata.json contém JSON inválido. Continuando sem metadados.")
        return None


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

    # 2b. Carregar e logar metadados do modelo
    metadata = _load_metadata()
    if metadata:
        print(f"[INFO] model_version: {metadata.get('model_version', 'N/A')}")
        print(f"[INFO] trained_at: {metadata.get('trained_at', 'N/A')}")

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

        # 5b. Modelo novo (opcional): probabilidade de a flag PHA ser positiva
        pha = _load_pha_model()
        if pha is not None:
            pha_model, pha_version, pha_features = pha
            print(f"[INFO] pha_model_version: {pha_version}")
            pha_probas = _score_pha(df, pha_model, pha_features)
        else:
            pha_version = None
            pha_probas = [None] * len(df)

        # 6. Montar lista de dicts para batch update
        records = [
            {
                "neo_id": neo_id,
                "feed_date": feed_date,
                "risk_proba_baixo": float(pb),
                "risk_proba_medio": float(pm),
                "risk_proba_alto": float(pa),
                "risk_label_ml": str(label),
                "pha_probability": pp,
                "pha_model_version": pha_version if pp is not None else None,
            }
            for neo_id, feed_date, pb, pm, pa, label, pp in zip(
                df["neo_id"], df["feed_date"],
                risk_proba_baixo, risk_proba_medio, risk_proba_alto,
                risk_labels, pha_probas,
            )
        ]

        # 7b. DELETE + INSERT em transação única.
        # Seguro porque o dbt recria mart_asteroids_ml a cada execução,
        # então a tabela sempre reflete o estado atual de mart_asteroids.
    with engine.begin() as conn:
        # Se as colunas pha_* ainda nao existem (migration 003 / dbt nao aplicados),
        # cai no INSERT legado em vez de quebrar o pipeline.
        has_pha = _ml_table_has_pha_columns(conn)
        if not has_pha:
            print("[WARNING] Colunas pha_* ausentes em mart.mart_asteroids_ml. Gravando so as colunas legadas.")
        conn.execute(text("DELETE FROM mart.mart_asteroids_ml"))
        conn.execute(text(_INSERT_WITH_PHA if has_pha else _INSERT_LEGACY), records)

    n = len(records)
    print(f"Updated {n} records.")


if __name__ == "__main__":
    try:
        run_scoring()
    except (EnvironmentError, FileNotFoundError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
