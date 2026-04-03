select
    count_mart,
    count_raw
from (
    select
        (select count(*) from {{ ref('mart_asteroids') }}) as count_mart,
        (select count(*) from {{ source('astraea', 'neo_feeds') }}) as count_raw
) counts
where count_mart != count_raw
