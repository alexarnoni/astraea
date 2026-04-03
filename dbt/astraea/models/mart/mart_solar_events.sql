with staging as (
    select * from {{ ref('stg_solar_events') }}
),

enriched as (
    select
        *,
        case
            when event_type = 'CME' then
                case
                    when speed_km_s >= 1000 then 'extremo'
                    when speed_km_s >= 500  then 'moderado'
                    else                         'fraco'
                end
            when event_type = 'GST' then
                case
                    when kp_index_max >= 8 then 'extremo'
                    when kp_index_max >= 7 then 'severo'
                    when kp_index_max >= 5 then 'moderado'
                    else                        'fraco'
                end
            else 'desconhecido'
        end as intensity_label
    from staging
)

select * from enriched
