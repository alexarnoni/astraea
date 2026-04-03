select * from {{ ref('mart_solar_events') }}
where intensity_label not in ('extremo', 'severo', 'moderado', 'fraco', 'desconhecido')
