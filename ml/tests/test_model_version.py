import warnings
import pytest
from pathlib import Path
import joblib
import sklearn

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "risk_classifier.joblib"


def test_model_loads_without_version_warning():
    """Falha se o modelo foi treinado com versão diferente do sklearn instalado."""
    if not MODEL_PATH.exists():
        pytest.skip("Modelo não encontrado — rode train.py primeiro")
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        joblib.load(MODEL_PATH)
    
    version_warnings = [
        x for x in w 
        if issubclass(x.category, UserWarning) 
        and "InconsistentVersionWarning" in str(x.message)
    ]
    assert len(version_warnings) == 0, (
        f"Modelo treinado com sklearn diferente do instalado ({sklearn.__version__}). "
        "Retreine o modelo com a versão atual."
    )
