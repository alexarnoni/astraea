-- Chave composta (neo_id, feed_date) de mart_asteroids.
-- dbt_utils.unique_combination_of_columns nao esta disponivel (nao ha packages.yml),
-- entao a unicidade e verificada por este teste singular. Falha se retornar linhas.
select
    neo_id,
    feed_date,
    count(*) as n_rows
from {{ ref('mart_asteroids') }}
group by neo_id, feed_date
having count(*) > 1
