

with source as (

    select * from {{ source('raw', 'customers') }}

),

renamed as (

    select
        customer_id,
        full_name,
        email,
        city,
        tier,
        updated_at,
        _loaded_at

    from source

)

select * from renamed

