from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import asteroids, solar_events, stats

app = FastAPI(
    title="Astraea API",
    description="API de monitoramento de objetos próximos à Terra",
    version="1.0.0",
)

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
