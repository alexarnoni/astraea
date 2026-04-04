from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from routers import asteroids, solar_events, stats


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host


limiter = Limiter(key_func=get_client_ip)


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded: 60 per 1 minute"},
        headers={"Retry-After": str(exc.limit.limit.get_expiry())},
    )


app = FastAPI(
    title="Astraea API",
    description="API de monitoramento de objetos próximos à Terra",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(asteroids.router, prefix="/v1", tags=["asteroides"])
app.include_router(solar_events.router, prefix="/v1", tags=["eventos solares"])
app.include_router(stats.router, prefix="/v1", tags=["estatísticas"])


@app.get("/")
def root():
    return {"status": "ok", "project": "Astraea", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
