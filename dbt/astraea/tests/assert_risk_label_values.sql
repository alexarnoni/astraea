select * from {{ ref('mart_asteroids') }}
where risk_label not in ('alto', 'médio', 'baixo')
