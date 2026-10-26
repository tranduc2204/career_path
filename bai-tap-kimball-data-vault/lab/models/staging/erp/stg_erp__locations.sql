with source as (
    select * from {{ source('erp', 'locations') }}
),

renamed as (
    select
        upper(trim(location_code))  as location_code,
        trim(location_name)         as location_name,
        lower(location_type)        as location_type,
        trim(city)                  as city,
        _loaded_at
    from source
)

select * from renamed
