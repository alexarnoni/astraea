import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from limiter import limiter
from routers import asteroids, solar_events, stats

# Origens permitidas para CORS. Configurável via CORS_ALLOW_ORIGINS
# (lista separada por vírgula). Default cobre o dashboard em produção
# e o desenvolvimento local.
_DEFAULT_ORIGINS = "https://astraea.alexarnoni.com,http://localhost:5500,http://127.0.0.1:5500"
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOW_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if origin.strip()
]


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded: 60 per 1 minute"},
        headers={"Retry-After": str(exc.limit.limit.get_expiry())},
    )


app = FastAPI(
    title="Astraea API",
    description="API de monitoramento de objetos próximos à Terra",
    version="1.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(asteroids.router, prefix="/v1", tags=["asteroides"])
app.include_router(solar_events.router, prefix="/v1", tags=["eventos solares"])
app.include_router(stats.router, prefix="/v1", tags=["estatísticas"])


@app.get("/")
def root():
    return {"status": "ok", "project": "Astraea", "version": "1.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
