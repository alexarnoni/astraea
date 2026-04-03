select
    count_mart,
    count_raw
from (
    select
        (select count(*) from {{ ref('mart_solar_events') }}) as count_mart,
        (select count(*) from {{ source('astraea', 'solar_events') }}) as count_raw
) counts
where count_mart != count_raw
