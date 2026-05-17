{{ config(
    materialized='table',
    post_hook=[
        "DROP INDEX IF EXISTS mart.mart_asteroids_ml_neo_feed_idx",
        "ALTER TABLE mart.mart_asteroids_ml ADD CONSTRAINT IF NOT EXISTS mart_asteroids_ml_neo_id_feed_date_key UNIQUE (neo_id, feed_date)"
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
