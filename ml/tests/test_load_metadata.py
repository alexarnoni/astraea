"""
Testes unitários para ml/predict.py — _load_metadata.

Valida o carregamento gracioso de metadata.json no pipeline de scoring.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Garantir que ml/ está no path para importar predict
_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


def _ensure_predict_module():
    """Importa o módulo predict mockando dependências pesadas."""
    mocks = {}
    for mod_name in ("joblib", "pandas", "dotenv", "sqlalchemy"):
        if mod_name not in sys.modules:
            mocks[mod_name] = MagicMock()
            sys.modules[mod_name] = mocks[mod_name]
    for sub in ("sqlalchemy.engine", "sqlalchemy"):
        if sub not in sys.modules:
            mocks[sub] = MagicMock()
            sys.modules[sub] = mocks[sub]

    if "predict" in sys.modules:
        del sys.modules["predict"]

    import predict
    return predict


_predict_mod = _ensure_predict_module()


class TestLoadMetadataMissingFile:
    """Req 2.4 — fallback gracioso quando metadata.json não existe."""

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch, capsys):
        fake_path = tmp_path / "metadata.json"
        monkeypatch.setattr(_predict_mod, "_METADATA_PATH", fake_path)

        result = _predict_mod._load_metadata()

        assert result is None
        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "metadata.json" in captured.out


class TestLoadMetadataInvalidJSON:
    """Req 2.4 — fallback gracioso quando metadata.json contém JSON inválido."""

    def test_returns_none_on_invalid_json(self, tmp_path, monkeypatch, capsys):
        fake_path = tmp_path / "metadata.json"
        fake_path.write_text("not valid json {{{", encoding="utf-8")
        monkeypatch.setattr(_predict_mod, "_METADATA_PATH", fake_path)

        result = _predict_mod._load_metadata()

        assert result is None
        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out


class TestLoadMetadataSuccess:
    """Req 2.1, 2.2, 2.3 — carregamento bem-sucedido de metadata.json."""

    def test_returns_dict_on_valid_json(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "metadata.json"
        metadata = {
            "model_version": "1.0.0",
            "trained_at": "2024-01-15T10:30:00+00:00",
            "sklearn_version": "1.5.2",
            "feature_columns": ["col_a", "col_b"],
            "training_data_range": {"start": "2024-01-01", "end": "2024-01-14"},
            "total_samples": 100,
            "accuracy": 0.95,
        }
        fake_path.write_text(json.dumps(metadata), encoding="utf-8")
        monkeypatch.setattr(_predict_mod, "_METADATA_PATH", fake_path)

        result = _predict_mod._load_metadata()

        assert result == metadata
        assert result["model_version"] == "1.0.0"
        assert result["trained_at"] == "2024-01-15T10:30:00+00:00"
