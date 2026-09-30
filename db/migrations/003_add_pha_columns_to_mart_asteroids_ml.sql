-- Etapa B, passo 1 (expandir): colunas do modelo novo (alvo is_potentially_hazardous).
-- Aditivo e idempotente. As colunas antigas (risk_proba_*, risk_label_ml) ficam intactas.
-- Sem NOT NULL e sem default: linhas existentes ficam com NULL ate o predict.py passar a escrever.
--
-- IMPORTANTE: mart_asteroids_ml e recriada pelo dbt a cada "dbt run" (materialized: table).
-- As mesmas colunas estao declaradas em dbt/astraea/models/mart/mart_asteroids_ml.sql,
-- senao a proxima execucao do dbt as removeria.
--
-- Aplicacao (manual, como as demais migrations do repo):
--   docker exec -i astraea-db-1 psql -U astraea -d astraea < db/migrations/003_add_pha_columns_to_mart_asteroids_ml.sql
--
-- Rollback (reverter tambem o modelo dbt antes de rodar o dbt de novo):
--   ALTER TABLE mart.mart_asteroids_ml
--       DROP COLUMN IF EXISTS pha_probability,
--       DROP COLUMN IF EXISTS pha_model_version;

ALTER TABLE mart.mart_asteroids_ml
    ADD COLUMN IF NOT EXISTS pha_probability   double precision,
    ADD COLUMN IF NOT EXISTS pha_model_version varchar;
