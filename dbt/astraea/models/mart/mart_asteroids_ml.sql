{{ config(
    materialized='table',
    post_hook=[
        "DROP INDEX IF EXISTS mart.mart_asteroids_ml_neo_feed_idx",
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mart_asteroids_ml_neo_id_feed_date_key') THEN ALTER TABLE mart.mart_asteroids_ml ADD CONSTRAINT mart_asteroids_ml_neo_id_feed_date_key UNIQUE (neo_id, feed_date); END IF; END $$"
    ]
) }}

select
    neo_id,
    feed_date,
    null::float        as risk_proba_baixo,
    null::float        as risk_proba_medio,
    null::float        as risk_proba_alto,
    null::varchar(20)  as risk_label_ml
from {{ ref('mart_asteroids') }}
where 1 = 0
