-- Verifica que as quatro novas colunas existem em mart_asteroids
-- e que pelo menos uma linha possui valor não-nulo em cada campo.
-- Retorna linhas apenas em caso de falha (padrão dbt test).

select 'orbit_class' as campo
where not exists (
    select 1 from mart.mart_asteroids where orbit_class is not null
)
union all
select 'is_sentry_object'
where not exists (
    select 1 from mart.mart_asteroids where is_sentry_object is not null
)
union all
select 'first_observation_date'
where not exists (
    select 1 from mart.mart_asteroids where first_observation_date is not null
)
union all
select 'nasa_jpl_url'
where not exists (
    select 1 from mart.mart_asteroids where nasa_jpl_url is not null
)
