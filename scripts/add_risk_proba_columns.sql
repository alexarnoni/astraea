-- Astraea — Migration: Add ML risk probability columns
-- Adds three probability columns from predict_proba (baixo, médio, alto)
-- to mart.mart_asteroids. Run manually BEFORE deploying the refactored Scorer.
-- Idempotent: safe to run multiple times (IF NOT EXISTS throughout)

ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_proba_baixo NUMERIC(6,4);
ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_proba_medio NUMERIC(6,4);
ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_proba_alto  NUMERIC(6,4);
