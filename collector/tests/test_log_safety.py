"""Garante que a chave da NASA nao vai para o log."""

import logging

import httpx
import pytest

import log_safety
import nasa_donki
import nasa_neows

SECRET = "SECRETKEY1234567890abcdef"


@pytest.fixture(autouse=True)
def _restore_loggers():
    names = ("httpx", "httpcore")
    before = {n: logging.getLogger(n).level for n in names}
    yield
    for n, level in before.items():
        logging.getLogger(n).setLevel(level)


def _status_error(status: int, url: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", url)
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"Client error for url '{url}'", request=request, response=response)


def test_describe_http_error_has_type_and_status_but_no_url():
    exc = _status_error(429, f"https://api.nasa.gov/neo/rest/v1/feed?api_key={SECRET}")
    text = log_safety.describe_http_error(exc)
    assert text == "HTTPStatusError status_code=429"
    assert SECRET not in text and "api.nasa.gov" not in text


def test_describe_http_error_non_status_error_is_only_the_type():
    exc = httpx.ConnectTimeout(f"timeout for https://x?api_key={SECRET}")
    assert log_safety.describe_http_error(exc) == "ConnectTimeout"


def test_neows_error_log_does_not_contain_the_key(monkeypatch, caplog):
    def fake_get(url, params=None, timeout=None):
        raise _status_error(403, f"{url}?api_key={params['api_key']}")

    monkeypatch.setattr(nasa_neows, "NASA_API_KEY", SECRET)
    monkeypatch.setattr(nasa_neows.httpx, "get", fake_get)
    with caplog.at_level(logging.DEBUG):
        nasa_neows.collect_neows()
    assert "HTTPStatusError status_code=403" in caplog.text
    assert SECRET not in caplog.text


def test_donki_error_log_does_not_contain_the_key(monkeypatch, caplog):
    def fake_get(url, params=None, timeout=None):
        raise _status_error(429, f"{url}?api_key={params['api_key']}")

    monkeypatch.setattr(nasa_donki, "NASA_API_KEY", SECRET)
    monkeypatch.setattr(nasa_donki.httpx, "get", fake_get)
    with caplog.at_level(logging.DEBUG):
        assert nasa_donki._fetch("CME", nasa_donki.date.today(), nasa_donki.date.today()) == []
    assert "HTTPStatusError status_code=429" in caplog.text
    assert SECRET not in caplog.text


def test_httpx_request_line_is_not_logged_after_quiet_http_loggers(caplog):
    """Sem o ajuste, o httpx registra 'HTTP Request: GET <url com api_key>' em INFO."""
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    url = f"https://api.nasa.gov/neo/rest/v1/feed?api_key={SECRET}"

    logging.getLogger("httpx").setLevel(logging.NOTSET)
    with caplog.at_level(logging.INFO):
        with httpx.Client(transport=transport) as client:
            client.get(url)
    assert SECRET in caplog.text, "premissa do teste: sem o ajuste, o httpx vaza a chave"

    caplog.clear()
    log_safety.quiet_http_loggers()
    with caplog.at_level(logging.INFO):
        with httpx.Client(transport=transport) as client:
            client.get(url)
    assert SECRET not in caplog.text


def test_quiet_http_loggers_sets_warning_level():
    log_safety.quiet_http_loggers()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_redact_filter_masks_api_key_in_any_record():
    record = logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "GET https://h/p?a=1&api_key=%s&b=2 failed", (SECRET,), None
    )
    assert log_safety.RedactApiKeyFilter().filter(record) is True
    message = record.getMessage()
    assert SECRET not in message
    assert "api_key=***" in message and "a=1" in message and "b=2" in message


def test_redact_filter_leaves_other_records_untouched():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "NeoWs: inserted=%d skipped=%d", (3, 4), None)
    log_safety.RedactApiKeyFilter().filter(record)
    assert record.getMessage() == "NeoWs: inserted=3 skipped=4"


def test_install_redaction_adds_filter_to_root_handlers():
    root = logging.getLogger()
    handler = logging.StreamHandler()
    root.addHandler(handler)
    try:
        log_safety.install_redaction()
        assert any(isinstance(f, log_safety.RedactApiKeyFilter) for f in handler.filters)
    finally:
        root.removeHandler(handler)
