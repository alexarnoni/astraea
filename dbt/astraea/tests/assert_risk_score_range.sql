select * from {{ ref('mart_asteroids') }}
where risk_score < 0 or risk_score > 8
