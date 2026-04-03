"""
ml/train.py — Treina e serializa o classificador de risco de asteroides.

Uso:
    python ml/train.py          (a partir da raiz do projeto)
    python train.py             (a partir de dentro de ml/)
"""

import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine, text

# Caminhos resolvidos de forma independente do diretório de execução
_ML_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _ML_DIR.parent
_DOTENV_PATH = _ROOT_DIR / ".env"
_MODELS_DIR = _ML_DIR / "models"
_MODEL_PATH = _MODELS_DIR / "risk_classifier.joblib"

FEATURE_COLUMNS = [
    "miss_distance_lunar",
    "relative_velocity_km_s",
    "diameter_avg_km",
    "absolute_magnitude_h",
    "is_potentially_hazardous",
]
TARGET_COLUMN = "risk_label"
ACCURACY_THRESHOLD = 0.85


def _make_engine(database_url: str):
    # Troca o driver para pg8000 (Python puro) para evitar UnicodeDecodeError
    # do psycopg2 nativo no Windows PT-BR (CP1252)
    url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
    url = url.replace("postgresql+psycopg2://", "postgresql+pg8000://", 1)
    return create_engine(url)


def load_data(database_url: str) -> pd.DataFrame:
    """Consulta mart.mart_asteroids e retorna o DataFrame com features + target."""
    engine = _make_engine(database_url)
    query = text(
        "SELECT neo_id, miss_distance_lunar, relative_velocity_km_s, "
        "estimated_diameter_min_km, estimated_diameter_max_km, "
        "absolute_magnitude_h, is_potentially_hazardous, risk_label "
        "FROM mart.mart_asteroids"
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    df["diameter_avg_km"] = (
        df["estimated_diameter_min_km"] + df["estimated_diameter_max_km"]
    ) / 2
    return df


def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Extrai X e y, convertendo is_potentially_hazardous de bool para int."""
    df = df.copy()
    df["is_potentially_hazardous"] = df["is_potentially_hazardous"].astype(int)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y


def train(X: pd.DataFrame, y: pd.Series) -> tuple[RandomForestClassifier, dict]:
    """Treina o modelo e retorna (model, metrics_dict)."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_))

    metrics = {
        "accuracy": accuracy,
        "report": report,
        "importances": importances,
        "X_test": X_test,
        "y_test": y_test,
    }
    return model, metrics


def print_metrics(metrics: dict) -> None:
    """Imprime métricas para stdout."""
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print("Classification Report:")
    print(metrics["report"])
    print("Feature importances:")
    for col, imp in metrics["importances"].items():
        print(f"  {col}: {imp:.4f}")

    if metrics["accuracy"] < ACCURACY_THRESHOLD:
        print(
            f"[WARNING] Accuracy {metrics['accuracy']:.4f} below threshold "
            f"{ACCURACY_THRESHOLD}"
        )


def save_model(model: RandomForestClassifier) -> None:
    """Cria ml/models/ se necessário e serializa o modelo."""
    os.makedirs(_MODELS_DIR, exist_ok=True)
    joblib.dump(model, _MODEL_PATH)
    print(f"Model saved to {_MODEL_PATH}")


def main() -> None:
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

    # 2. Carregar e pré-processar dados
    df = load_data(database_url)
    X, y = preprocess(df)

    # 3. Treinar modelo
    model, metrics = train(X, y)

    # 4. Imprimir métricas
    print_metrics(metrics)

    # 5. Persistir modelo
    save_model(model)


if __name__ == "__main__":
    try:
        main()
    except EnvironmentError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
