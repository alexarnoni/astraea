-- Astraea Base Infrastructure — Database Initialization Script
-- Idempotent: safe to run multiple times (IF NOT EXISTS throughout)

-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

-- raw.neo_feeds
CREATE TABLE IF NOT EXISTS raw.neo_feeds (
    id          SERIAL PRIMARY KEY,
    neo_id      VARCHAR(50)  NOT NULL,
    name        VARCHAR(200),
    raw_data    JSONB        NOT NULL,
    ingested_at TIMESTAMPTZ  DEFAULT NOW(),
    feed_date   DATE         NOT NULL,
    CONSTRAINT uq_neo_feeds_neo_id_feed_date UNIQUE (neo_id, feed_date)
);

CREATE INDEX IF NOT EXISTS idx_neo_feeds_neo_id    ON raw.neo_feeds (neo_id);
CREATE INDEX IF NOT EXISTS idx_neo_feeds_feed_date ON raw.neo_feeds (feed_date);

-- raw.solar_events
CREATE TABLE IF NOT EXISTS raw.solar_events (
    id          SERIAL PRIMARY KEY,
    event_id    VARCHAR(100) NOT NULL,
    event_type  VARCHAR(50)  NOT NULL,
    raw_data    JSONB        NOT NULL,
    ingested_at TIMESTAMPTZ  DEFAULT NOW(),
    event_date  DATE         NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_solar_events_event_type ON raw.solar_events (event_type);
CREATE INDEX IF NOT EXISTS idx_solar_events_event_date ON raw.solar_events (event_date);

-- mart.mart_asteroids_ml
CREATE TABLE IF NOT EXISTS mart.mart_asteroids_ml (
    id              SERIAL PRIMARY KEY,
    neo_id          VARCHAR(50)  NOT NULL,
    feed_date       DATE         NOT NULL,
    features        JSONB,
    prediction      DOUBLE PRECISION,
    model_version   VARCHAR(50),
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT mart_asteroids_ml_neo_id_feed_date_key UNIQUE (neo_id, feed_date)
);

CREATE INDEX IF NOT EXISTS idx_mart_asteroids_ml_neo_id    ON mart.mart_asteroids_ml (neo_id);
CREATE INDEX IF NOT EXISTS idx_mart_asteroids_ml_feed_date ON mart.mart_asteroids_ml (feed_date);
