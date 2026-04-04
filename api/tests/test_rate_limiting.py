import sys
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import types
from unittest.mock import MagicMock, patch
from fastapi import APIRouter, Request

for _mod in list(sys.modules.keys()):
    if _mod in ("main", "database", "routers",
                "routers.asteroids", "routers.solar_events", "routers.stats"):
        del sys.modules[_mod]

_stub_router = APIRouter()
for _mod_name in ("routers", "routers.asteroids", "routers.solar_events", "routers.stats"):
    _m = types.ModuleType(_mod_name)
    _m.router = _stub_router
    sys.modules[_mod_name] = _m

with patch("sqlalchemy.create_engine"):
    from main import app, get_client_ip, limiter
    from database import get_db

_v1_router = APIRouter()

@_v1_router.get("/asteroids")
@limiter.limit("60/minute")
def _asteroids_stub(request: Request):
    return []

app.include_router(_v1_router, prefix="/v1")

def _override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = _override_get_db

from starlette.testclient import TestClient
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from hypothesis import given, settings, assume
from hypothesis import strategies as st

client = TestClient(app, raise_server_exceptions=False)

def reset_limiter():
    app.state.limiter._storage.reset()

_ip_counter = 0

def next_test_ip():
    global _ip_counter
    _ip_counter += 1
    a = (_ip_counter >> 16) & 0xFF
    b = (_ip_counter >> 8) & 0xFF
    c = _ip_counter & 0xFF
    return f"10.{a}.{b}.{c}"


# ---------------------------------------------------------------------------
# Task 5.1 - Configuration and excluded endpoints
# ---------------------------------------------------------------------------

def test_app_state_limiter_configured():
    assert hasattr(app.state, "limiter")
    assert app.state.limiter is not None


def test_slowapi_middleware_registered():
    middleware_classes = [m.cls for m in app.user_middleware]
    assert SlowAPIMiddleware in middleware_classes


def test_rate_limit_exceeded_handler_registered():
    assert RateLimitExceeded in app.exception_handlers


def test_root_endpoint_no_rate_limit():
    reset_limiter()
    ip = next_test_ip()
    for i in range(65):
        r = client.get("/", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200, f"Falhou na requisicao {i + 1}"


def test_health_endpoint_no_rate_limit():
    reset_limiter()
    ip = next_test_ip()
    for i in range(65):
        r = client.get("/health", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200, f"Falhou na requisicao {i + 1}"


# ---------------------------------------------------------------------------
# Task 5.2 - Rate limit behavior on /v1/asteroids
# ---------------------------------------------------------------------------

def test_60th_request_returns_200():
    reset_limiter()
    ip = next_test_ip()
    for i in range(59):
        r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200, f"Falhou na requisicao {i + 1}"
    r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
    assert r.status_code == 200, "A 60a requisicao deveria retornar 200"


def test_61st_request_returns_429():
    reset_limiter()
    ip = next_test_ip()
    for i in range(60):
        r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200, f"Falhou na requisicao {i + 1}"
    r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
    assert r.status_code == 429, "A 61a requisicao deveria retornar 429"


def test_429_response_body():
    reset_limiter()
    ip = next_test_ip()
    for _ in range(60):
        client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
    r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
    assert r.status_code == 429
    assert r.json() == {"error": "Rate limit exceeded: 60 per 1 minute"}


# ---------------------------------------------------------------------------
# Property tests (hypothesis)
# ---------------------------------------------------------------------------

# Feature: api-rate-limiting, Property 1: Extracao do IP real do X-Forwarded-For
# Validates: Requirements 2.2, 2.4, 5.1, 5.2

def _make_mock_request(x_forwarded_for=None):
    request = MagicMock()
    request.headers.get = lambda key, default=None: (
        x_forwarded_for if key == "X-Forwarded-For" else default
    )
    request.client.host = "127.0.0.1"
    return request


@given(
    first_ip=st.ip_addresses().map(str),
    extra_ips=st.lists(st.ip_addresses().map(str), min_size=0, max_size=3),
)
@settings(max_examples=100)
def test_get_client_ip_returns_first_ip(first_ip, extra_ips):
    """
    Feature: api-rate-limiting, Property 1: Extracao do IP real do X-Forwarded-For
    Validates: Requirements 2.2, 2.4, 5.1, 5.2
    """
    header_value = ", ".join([first_ip] + extra_ips)
    request = _make_mock_request(x_forwarded_for=header_value)
    assert get_client_ip(request) == first_ip


# Feature: api-rate-limiting, Property 2: Limite de requisicoes por IP
# Validates: Requirements 3.1, 3.5, 4.1

@given(ip=st.ip_addresses(v=4).map(str))
@settings(max_examples=5, deadline=None)
def test_61st_request_returns_429_property(ip):
    """
    Feature: api-rate-limiting, Property 2: Limite de requisicoes por IP
    Validates: Requirements 3.1, 3.5, 4.1
    """
    reset_limiter()
    for i in range(60):
        r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200, f"Requisicao {i + 1} deveria retornar 200"
    r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
    assert r.status_code == 429


# Feature: api-rate-limiting, Property 3: Formato da resposta 429
# Validates: Requirements 4.2, 4.3

@given(ip=st.ip_addresses(v=4).map(str))
@settings(max_examples=5, deadline=None)
def test_429_response_format_property(ip):
    """
    Feature: api-rate-limiting, Property 3: Formato da resposta 429
    Validates: Requirements 4.2, 4.3
    """
    reset_limiter()
    for _ in range(61):
        r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip})
    assert r.status_code == 429
    assert r.json()["error"] == "Rate limit exceeded: 60 per 1 minute"
    assert "retry-after" in r.headers
    assert int(r.headers["retry-after"]) > 0


# Feature: api-rate-limiting, Property 4: Isolamento de contadores por IP
# Validates: Requirements 5.3, 5.4

@given(
    ip_a=st.ip_addresses(v=4).map(str),
    ip_b=st.ip_addresses(v=4).map(str),
)
@settings(max_examples=5, deadline=None)
def test_independent_counters_per_ip(ip_a, ip_b):
    """
    Feature: api-rate-limiting, Property 4: Isolamento de contadores por IP
    Validates: Requirements 5.3, 5.4
    """
    assume(ip_a != ip_b)
    reset_limiter()
    for _ in range(61):
        client.get("/v1/asteroids", headers={"X-Forwarded-For": ip_a})
    r = client.get("/v1/asteroids", headers={"X-Forwarded-For": ip_b})
    assert r.status_code == 200
