with staging as (
    select * from {{ ref('stg_asteroids') }}
),

scored as (
    select
        *,
        (
            case when is_potentially_hazardous = true  then 3 else 0 end +
            case when relative_velocity_km_s > 20      then 2 else 0 end +
            case when miss_distance_km < 1000000       then 2 else 0 end +
            case when estimated_diameter_max_km > 0.5  then 1 else 0 end
        )::integer as risk_score
    from staging
),

enriched as (
    select
        *,
        case
            when risk_score >= 6 then 'alto'
            when risk_score >= 3 then 'médio'
            else                      'baixo'
        end as risk_label
    from scored
)

select * from enriched
