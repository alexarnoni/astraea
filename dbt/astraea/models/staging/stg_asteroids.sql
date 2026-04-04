with source as (
    select * from {{ source('astraea', 'neo_feeds') }}
),

renamed as (
    select
        neo_id,
        name,
        feed_date,
        ingested_at,

        -- dados de aproximação (close_approach_data é array, pegar index 0)
        (raw_data -> 'close_approach_data' -> 0 ->> 'close_approach_date')::date
            as close_approach_date,

        (raw_data -> 'close_approach_data' -> 0
            -> 'miss_distance' ->> 'lunar')::numeric
            as miss_distance_lunar,

        (raw_data -> 'close_approach_data' -> 0
            -> 'miss_distance' ->> 'kilometers')::numeric
            as miss_distance_km,

        (raw_data -> 'close_approach_data' -> 0
            -> 'relative_velocity' ->> 'kilometers_per_second')::numeric
            as relative_velocity_km_s,

        (raw_data -> 'close_approach_data' -> 0
            -> 'relative_velocity' ->> 'kilometers_per_hour')::numeric
            as velocity_km_per_h,

        -- diâmetro estimado em km
        (raw_data -> 'estimated_diameter' -> 'kilometers'
            ->> 'estimated_diameter_min')::numeric
            as estimated_diameter_min_km,

        (raw_data -> 'estimated_diameter' -> 'kilometers'
            ->> 'estimated_diameter_max')::numeric
            as estimated_diameter_max_km,

        -- magnitude absoluta
        (raw_data ->> 'absolute_magnitude_h')::numeric as absolute_magnitude_h,

        -- flag NASA de objeto potencialmente perigoso
        (raw_data ->> 'is_potentially_hazardous_asteroid')::boolean
            as is_potentially_hazardous,

        -- grupo orbital
        raw_data -> 'orbital_data' ->> 'orbit_class_type'
            as orbit_class,

        -- presença na lista Sentry da NASA
        (raw_data ->> 'is_sentry_object')::boolean
            as is_sentry_object,

        -- data da primeira observação
        raw_data -> 'orbital_data' ->> 'first_observation_date'
            as first_observation_date,

        -- link direto para o JPL Small-Body Database
        raw_data ->> 'nasa_jpl_url'
            as nasa_jpl_url

    from source
)

select * from renamed
