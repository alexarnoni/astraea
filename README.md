# Astraea

![pipeline](https://img.shields.io/badge/pipeline-passing-brightgreen)

Near-Earth Object (NEO) monitoring and solar event tracking platform with ML-based risk classification.

## Live Demo

- **Dashboard**: https://astraea.alexarnoni.com
- **API docs**: https://astraea-api.alexarnoni.com/docs

## Architecture

```
NASA NeoWs / DONKI APIs
        │
        ▼
   ┌──────────┐
   │ Collector │  (daily cron, APScheduler)
   └────┬─────┘
        │
        ▼
┌──────────────────┐
│  PostgreSQL (raw) │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────┐
│  dbt Core (staging → mart)  │
└────────────┬────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  ML Scoring (Random Forest)      │
│  → mart.mart_asteroids_ml        │
└────────────┬─────────────────────┘
             │
             ▼
      ┌──────────┐       ┌────────────────────────┐
      │ FastAPI  │──────▶│ Frontend (Cloudflare   │
      └──────────┘       │ Pages, Vanilla JS)     │
                         └────────────────────────┘
```

## Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| API          | FastAPI 0.110+, SQLAlchemy, slowapi |
| Database     | PostgreSQL 15                       |
| Transform    | dbt Core                            |
| ML           | scikit-learn 1.5.2, joblib          |
| Frontend     | Vanilla JS, HTML/CSS                |
| Infra        | Docker Compose, Oracle Cloud VM     |
| CDN/Hosting  | Cloudflare Pages                    |

## Features

- **NEO monitoring** — daily ingestion from NASA NeoWs with close-approach data, orbital parameters, and hazard flags
- **CME / geomagnetic storm tracking** — coronal mass ejection and GST events from NASA DONKI
- **ML risk classification** — 3-class Random Forest (baixo / médio / alto) with per-class probability output
- **Model metadata traceability** — every prediction carries model version, `trained_at` timestamp, and scikit-learn version
- **12 months historical data** — rolling window maintained by the collector backfill
- **Automated daily pipeline** — collector runs at 00:30 UTC, dbt transforms, ML scoring follows

## ML Model

| Property | Value |
|----------|-------|
| Algorithm | Random Forest (100 trees, balanced class weights) |
| Features | `miss_distance_lunar`, `relative_velocity_km_s`, `diameter_avg_km`, `absolute_magnitude_h`, `is_potentially_hazardous` |
| Classes | baixo, médio, alto |
| Accuracy | 99.47% |
| Training samples | 1,899 |
| Output | 3-class probabilities (`risk_proba_baixo`, `risk_proba_medio`, `risk_proba_alto`) |
| Metadata | `model_version`, `trained_at`, `sklearn_version` persisted in `metadata.json` |

## API Endpoints

All endpoints are prefixed with `/v1` and rate-limited to 60 requests/minute.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/asteroids` | List asteroids (pagination, filters: hazardous, risk_label, date range) |
| GET | `/v1/asteroids/upcoming` | Next 20 close approaches from today |
| GET | `/v1/asteroids/{neo_id}` | Single asteroid detail with ML probabilities |
| GET | `/v1/solar-events` | List solar events (pagination, filters: event_type, date range) |
| GET | `/v1/solar-events/earth-directed` | CMEs potentially directed at Earth |
| GET | `/v1/solar-events/{event_id}` | Single solar event detail |
| GET | `/v1/stats/summary` | Aggregated statistics (counts, closest approach, risk breakdown) |

## Local Setup

### Prerequisites

- Docker and Docker Compose
- NASA API key (get one at https://api.nasa.gov)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/alexarnoni/astraea.git
cd astraea

# 2. Configure environment
cp .env.example .env
# Edit .env and set your NASA_API_KEY (and change passwords if desired)

# 3. Start services
docker compose up -d

# 4. Run dbt transformations (after collector finishes first ingestion)
docker compose exec api bash -c "cd /app/dbt/astraea && dbt run"

# 5. Train ML model
docker compose exec api python /app/ml/train.py

# 6. Run ML scoring
docker compose exec api python /app/ml/predict.py
```

The API will be available at `http://localhost:8002`. Interactive docs at `http://localhost:8002/docs`.

## Project Structure

```
astraea/
├── api/                  # FastAPI application
│   ├── routers/          # Endpoint modules (asteroids, solar_events, stats)
│   ├── models.py         # Pydantic response schemas
│   ├── database.py       # SQLAlchemy session management
│   └── tests/            # API test suite (pytest + hypothesis)
├── collector/            # NASA data ingestion service
│   ├── nasa_neows.py     # NeoWs collector
│   └── nasa_donki.py     # DONKI (CME + GST) collector
├── dashboard/            # Static frontend (Vanilla JS)
│   ├── js/               # API client, page scripts
│   └── css/              # Styles
├── dbt/astraea/          # dbt project (staging → mart models)
├── ml/                   # Machine learning pipeline
│   ├── train.py          # Model training script
│   ├── predict.py        # Batch scoring script
│   └── schedule.py       # Scheduled retraining
├── scripts/              # Database init and utilities
├── docker-compose.yml    # Service orchestration
└── .env.example          # Environment variable template
```

## Roadmap

| Version | Focus |
|---------|-------|
| v1.2 | CI/CD pipeline, Alembic migrations |
| v1.3 | Historical dashboard with time-series charts |
| v1.4 | Jupyter notebook for exploratory analysis |

## Disclaimer

This project is an independent research and engineering exercise. The ML model is trained on publicly available NASA data and **does not replace official risk assessments** from NASA, ESA, or any other space agency. Do not use these classifications for safety-critical decisions.

## License

MIT
