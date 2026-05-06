{{ config(
    materialized='table',
    post_hook=[
        "ALTER TABLE mart.mart_asteroids_ml DROP CONSTRAINT IF EXISTS mart_asteroids_ml_pkey",
        "ALTER TABLE mart.mart_asteroids_ml ADD CONSTRAINT mart_asteroids_ml_pkey PRIMARY KEY (neo_id, feed_date)"
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
