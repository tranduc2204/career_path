

with source as (

    select * from {{ source('raw', 'events') }}

),

renamed as (

    select distinct
        event_id,
        user_id,
        event_type,
        event_ts,
        _loaded_at

    from source

)

select * from renamed

