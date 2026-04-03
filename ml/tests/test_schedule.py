"""
Testes unitários para ml/schedule.py.
"""

import importlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Garantir que ml/ está no path para importar schedule
_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


def _import_schedule():
    """Importa schedule com predict mockado para evitar dependências externas."""
    mock_predict = MagicMock()
    mock_predict.run_scoring = MagicMock()
    with patch.dict("sys.modules", {"predict": mock_predict}):
        if "schedule" in sys.modules:
            del sys.modules["schedule"]
        import schedule as sched
        return sched, mock_predict


# ---------------------------------------------------------------------------
# 7.1 — run_scoring é callable sem argumentos
# ---------------------------------------------------------------------------

def test_run_scoring_is_callable():
    """run_scoring deve ser callable sem argumentos obrigatórios."""
    sched, mock_predict = _import_schedule()
    assert callable(sched.run_scoring)
    # Deve poder ser chamada sem argumentos
    sched.run_scoring()


# ---------------------------------------------------------------------------
# 7.2 — run_scoring não usa subprocess
# ---------------------------------------------------------------------------

def test_run_scoring_no_subprocess():
    """run_scoring não deve chamar subprocess em nenhum momento."""
    sched, mock_predict = _import_schedule()

    with patch("subprocess.run") as mock_run, \
         patch("subprocess.Popen") as mock_popen, \
         patch("subprocess.call") as mock_call:
        sched.run_scoring()
        mock_run.assert_not_called()
        mock_popen.assert_not_called()
        mock_call.assert_not_called()


# ---------------------------------------------------------------------------
# 7.3 — exceções são logadas e não propagadas
# ---------------------------------------------------------------------------

def test_run_scoring_logs_exception():
    """Quando o scorer lança exceção, deve ser logada e não propagada."""
    mock_predict = MagicMock()
    mock_predict.run_scoring.side_effect = RuntimeError("falha simulada")

    with patch.dict("sys.modules", {"predict": mock_predict}):
        if "schedule" in sys.modules:
            del sys.modules["schedule"]
        import schedule as sched

        with patch.object(sched.logger, "exception") as mock_log:
            # Não deve propagar a exceção
            sched.run_scoring()
            mock_log.assert_called_once()
            # Verificar que a mensagem de log está presente
            call_args = mock_log.call_args[0][0]
            assert "scoring" in call_args.lower() or "erro" in call_args.lower()
