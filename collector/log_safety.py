"""Evita que a chave da NASA apareca em log.

A chave vai na query string (api_key=...). Dois caminhos a vazavam:
  1. o logger do httpx, que registra a URL completa de cada requisicao em INFO;
  2. o str() de httpx.HTTPStatusError, que inclui a URL da requisicao.
"""

import logging
import re

import httpx

_API_KEY_RE = re.compile(r"(api_key=)[^&\s'\"]+", re.IGNORECASE)


def quiet_http_loggers() -> None:
    """httpx e httpcore so registram a partir de WARNING (sem a linha por requisicao)."""
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


class RedactApiKeyFilter(logging.Filter):
    """Rede de seguranca: mascara api_key=... em qualquer registro que passe pelo handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _API_KEY_RE.sub(r"\1***", message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_redaction() -> None:
    """Aplica o filtro em todos os handlers atuais do logger raiz."""
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactApiKeyFilter())


def describe_http_error(exc: httpx.HTTPError) -> str:
    """Tipo do erro e status_code, nunca a URL nem a mensagem original."""
    name = type(exc).__name__
    if isinstance(exc, httpx.HTTPStatusError):
        return f"{name} status_code={exc.response.status_code}"
    return name
