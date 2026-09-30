# 🌌 Astraea

Near-Earth Object (NEO) monitoring and solar event tracking platform. Asteroids get a rule-based risk heuristic defined by the project, and an ML model for the NASA hazard flag is being validated.

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

- **NEO monitoring**: daily ingestion from NASA NeoWs with close-approach data, orbital parameters, and hazard flags
- **CME / geomagnetic storm tracking**: coronal mass ejection and GST events from NASA DONKI
- **Rule-based risk heuristic**: `risk_score` / `risk_label` (baixo / médio / alto) from thresholds chosen by the author, not a NASA methodology
- **ML scoring (legacy model 1.0.0 in production)**: 3-class Random Forest that reproduces the rule; the retargeted model 2.0.0 (NASA hazard flag) is validated but not in production
- **Model metadata traceability**: every prediction carries model version, `trained_at` timestamp, and scikit-learn version
- **12 months historical data**: rolling window maintained by the collector backfill
- **Automated daily pipeline**: collector runs at 00:30 UTC, dbt transforms, ML scoring follows

## Risk score (project heuristic)

`risk_score` and `risk_label` in `mart.mart_asteroids` are a heuristic defined by this project,
with thresholds chosen by the author. **It is not a NASA methodology.** It is computed by rule in
`dbt/astraea/models/mart/mart_asteroids.sql`:

| Condition | Points |
|-----------|--------|
| `is_potentially_hazardous` (PHA flag) | 3 |
| relative velocity > 20 km/s | 2 |
| miss distance < 1,000,000 km | 2 |
| maximum estimated diameter > 0.5 km | 1 |

`risk_label` is `alto` when the score is >= 6, `médio` when >= 3, and `baixo` otherwise.

Which label the product shows (verified in the code): the dashboard badges and the asteroid page
show the rule-based `risk_label`. The ML model exposes a PHA probability (`pha_probability`, with
`pha_model_version`) instead of a risk class, shown on the asteroid page when available. Two API
pieces still read `risk_label_ml`, the prediction of the legacy model 1.0.0 described below: the
`?risk_label=` filter of `GET /v1/asteroids` and the risk counts of `GET /v1/stats/summary`. Moving
them to the rule-based label is part of the same rollout and is not done yet.

## ML Model

### Production today: model 1.0.0 (legacy)

Random Forest (100 trees, balanced class weights) that predicts `risk_label`. Features:
`miss_distance_lunar`, `relative_velocity_km_s`, `diameter_avg_km`, `absolute_magnitude_h`,
`is_potentially_hazardous` (5 features). Its target is computed by rule from these same columns
(the PHA flag is one of the rule inputs and also a feature), so the accuracy it reported
(99.47%) only measured how well it re-learned the rule. It says nothing about predictive
quality, so it is no longer used as a quality metric. The split was random, without grouping,
and the same `neo_id` could appear in train and test.

### Validated, not in production: model 2.0.0 (target `is_potentially_hazardous`)

The new target is the NASA hazard flag. Features: `relative_velocity_km_s`, `miss_distance_lunar`, `absolute_magnitude_h` (3 features).
The flag is not a feature, and neither are `risk_score`, `risk_label` or `diameter_avg_km`
(Spearman rho with `absolute_magnitude_h` is -1.0, so it adds no information; see the report).
Same Random Forest hyperparameters, fixed threshold 0.5, no tuning.

Validation: `StratifiedGroupKFold(5)` grouped by `neo_id` (shuffle, fixed seed), plus a temporal
evaluation (train on the oldest 80% of dates, test on the most recent). Evaluation unit is the
row (an approach). Data: 2083 rows, 1822 distinct asteroids, 180
positive asteroids (about 9% positive rows).

Mean over the 5 folds, positive class (source: [`docs/ml-metrics.json`](docs/ml-metrics.json)):

| Model | Precision | Recall | F1 | PR-AUC |
|-------|-----------|--------|----|--------|
| Random Forest | 0.64 | 0.44 | 0.52 (std between folds 0.05) | 0.65 |
| Logistic regression (baseline) | 0.38 | 0.17 | 0.23 | 0.42 |
| Majority class (baseline) | 0.00 | 0.00 | 0.00 | 0.09 (= prevalence) |

What the numbers say, and their limits:

- Recall is low at the fixed 0.5 threshold: the model misses more than half of the PHAs.
- Magnitude H dominates. Impurity importances: `absolute_magnitude_h` 0.67,
  `relative_velocity_km_s` 0.17, `miss_distance_lunar` 0.16.
  The NASA flag is defined by H and by the MOID (0.05 AU limit), and the MOID is not a feature,
  so the model approximates the flag without seeing its orbital determinant.
  `miss_distance_lunar` is the distance of one specific approach.
- Comparison with the simple rule `absolute_magnitude_h <= 22` (added after the first run, no
  tuning): precision 0.3900, recall 0.9949, F1 0.5599 on the same folds, above the
  Random Forest F1 (0.518). Temporal: F1 0.4970 for the rule.
- Post-hoc exploratory analysis (not part of the original plan): using H alone as a score has
  pooled PR-AUC 0.3592 against 0.6394 for the Random Forest, so the model ranks better than H
  alone. At recall >= 0.95 the best precision of the Random Forest is 0.4045, close to the rule's 0.39.
- Temporal evaluation (cut at 2026-07-12): F1 0.3881, PR-AUC 0.5548, lower than the
  cross-validation F1. Removing test asteroids already seen in training gives F1 0.4000, PR-AUC 0.5532.
  With about 43 positives in the test set, the data do not separate temporal drift from variance.

Status: model 2.0.0 is validated and in rollout. The API and the dashboard read its output
(`pha_probability`) from `mart.mart_asteroids_ml`, whose `pha_*` columns stay NULL until the model
artifact is published to the server and the scoring runs. Details, per-fold metrics and confusion matrices:
[`docs/ml-report.md`](docs/ml-report.md). Training script: `ml/train_retarget.py`.

## API Endpoints

The 7 data endpoints below are prefixed with `/v1` and rate-limited to 60 requests/minute. The API also exposes `GET /` (status) and `GET /health` (health check), without prefix.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/asteroids` | List asteroids (pagination, filters: hazardous, risk_label, date range) |
| GET | `/v1/asteroids/upcoming` | Next 20 close approaches from today |
| GET | `/v1/asteroids/{neo_id}` | Single asteroid detail, including the rule-based `risk_label` and the legacy ML fields |
| GET | `/v1/solar-events` | List solar events (pagination, filters: event_type, date range) |
| GET | `/v1/solar-events/earth-directed` | CMEs potentially directed at Earth |
| GET | `/v1/solar-events/{event_id}` | Single solar event detail |
| GET | `/v1/stats/summary` | Aggregated statistics (counts, closest approach, risk breakdown by `risk_label_ml`) |

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

# 5. Train the legacy ML model (1.0.0, the one currently served)
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
│   ├── train.py          # Legacy training script (model 1.0.0, production)
│   ├── train_retarget.py # Retargeted model validation (writes to docs/ and ml/artifacts_retarget/)
│   ├── predict.py        # Batch scoring script
│   └── schedule.py       # APScheduler wrapper around the scoring
├── docs/                 # ML metrics (ml-metrics.json) and report (ml-report.md)
├── scripts/              # Database init and utilities
├── docker-compose.yml    # Service orchestration
└── .env.example          # Environment variable template
```

## Roadmap

| Version | Focus |
|---------|-------|
| v1.2 | CD pipeline, Alembic migrations (CI runs on push and pull requests) |
| v1.3 | Historical dashboard with time-series charts |
| v1.4 | Jupyter notebook for exploratory analysis |

## Disclaimer

This project is an independent research and engineering exercise. The risk score is a heuristic defined by this project, not a NASA methodology, and the ML model is trained on publicly available NASA data. Neither **replaces official risk assessments** from NASA, ESA, or any other space agency. Do not use these classifications for safety-critical decisions.

## License

MIT
