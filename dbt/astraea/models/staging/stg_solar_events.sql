with source as (
    select * from {{ source('astraea', 'solar_events') }}
),

renamed as (
    select
        event_id,
        event_type,
        event_date,
        ingested_at,

        -- campos específicos de CME
        case when event_type = 'CME'
            then (raw_data ->> 'startTime')
            else null
        end as start_time,

        case when event_type = 'CME'
            then (raw_data -> 'cmeAnalyses' -> 0 ->> 'speed')::numeric
            else null
        end as speed_km_s,

        case when event_type = 'CME'
            then (raw_data -> 'cmeAnalyses' -> 0 ->> 'type')
            else null
        end as cme_type,

        case when event_type = 'CME'
            then (raw_data -> 'cmeAnalyses' -> 0 ->> 'halfAngle')::numeric
            else null
        end as half_angle_deg,

        case when event_type = 'CME'
            then (raw_data -> 'cmeAnalyses' -> 0 ->> 'latitude')::numeric
            else null
        end as latitude,

        case when event_type = 'CME'
            then (raw_data -> 'cmeAnalyses' -> 0 ->> 'longitude')::numeric
            else null
        end as longitude,

        case when event_type = 'CME'
            then (raw_data ->> 'note')
            else null
        end as note,

        -- campos específicos de GST
        case when event_type = 'GST'
            then (raw_data -> 'allKpIndex' -> 0 ->> 'kpIndex')::numeric
            else null
        end as kp_index_max,

        -- direcionamento à Terra (CME)
        case when event_type = 'CME'
            then (raw_data -> 'cmeAnalyses' -> 0 ->> 'isEarthDirected')::boolean
            else null
        end as is_earth_directed

    from source
)

select * from renamed
