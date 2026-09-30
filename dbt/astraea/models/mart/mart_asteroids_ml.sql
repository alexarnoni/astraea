{{ config(
    materialized='table'
) }}

select
    neo_id,
    feed_date,
    null::float        as risk_proba_baixo,
    null::float        as risk_proba_medio,
    null::float        as risk_proba_alto,
    null::varchar(20)  as risk_label_ml,
    null::float        as pha_probability,
    null::varchar      as pha_model_version
from {{ ref('mart_asteroids') }}
where 1 = 0
