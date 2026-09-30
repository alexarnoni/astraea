"""Guarda o passo de limpeza do pipeline contra a quebra por versao nao fixada.

Em 2026-09 a limpeza passou a falhar com "No module named 'psycopg'" porque o
container instalava sqlalchemy sem versao e recebeu uma major que usa psycopg v3
como driver padrao. Estes testes leem os arquivos, nao abrem banco nem Docker.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CLEANUP_SH = ROOT / "scripts" / "cleanup_old_records.sh"
CLEANUP_PY = ROOT / "scripts" / "cleanup_runner.py"
PIPELINE_SH = ROOT / "scripts" / "run_pipeline.sh"
ML_REQUIREMENTS = ROOT / "ml" / "requirements.txt"


def _pinned(text: str, package: str) -> str | None:
    m = re.search(rf"{re.escape(package)}==([0-9][^\s\\\"']*)", text)
    return m.group(1) if m else None


def test_cleanup_pip_install_pins_sqlalchemy_and_psycopg2():
    text = CLEANUP_SH.read_text(encoding="utf-8")
    assert _pinned(text, "sqlalchemy") is not None, "sqlalchemy sem versao fixa na limpeza"
    assert _pinned(text, "psycopg2-binary") is not None, "psycopg2-binary sem versao fixa na limpeza"


def test_cleanup_pins_match_ml_step_and_requirements():
    cleanup = CLEANUP_SH.read_text(encoding="utf-8")
    pipeline = PIPELINE_SH.read_text(encoding="utf-8")
    reqs = ML_REQUIREMENTS.read_text(encoding="utf-8")
    for pkg in ("sqlalchemy", "psycopg2-binary"):
        assert _pinned(cleanup, pkg) == _pinned(pipeline, pkg) == _pinned(reqs, pkg), pkg


def test_cleanup_message_matches_sql_retention():
    sql = CLEANUP_PY.read_text(encoding="utf-8")
    days_sql = re.search(r"INTERVAL '(\d+) days'", sql)
    assert days_sql, "intervalo de retencao nao encontrado no SQL"
    message = CLEANUP_SH.read_text(encoding="utf-8")
    assert f"hoje - {days_sql.group(1)} dias" in message
