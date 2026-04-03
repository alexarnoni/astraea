"""
ml/schedule.py — Wrapper para o APScheduler chamar o scoring de risco ML.

Uso via APScheduler:
    from ml.schedule import run_scoring
    scheduler.add_job(run_scoring, "cron", hour=3)

Uso direto:
    python ml/schedule.py
"""

import logging

from predict import run_scoring as _run_scoring

logger = logging.getLogger(__name__)


def run_scoring() -> None:
    """Executa o scoring batch de risco ML, capturando qualquer exceção."""
    try:
        _run_scoring()
    except Exception:
        logger.exception("Erro durante o scoring de risco ML")


if __name__ == "__main__":
    run_scoring()
