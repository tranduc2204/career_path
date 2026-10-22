

with source as (

    select * from {{ source('raw', 'customer_changelog') }}

),

renamed as (

    select
        customer_id,
     
        {{ clean_string('op') }} as op,
        {{ clean_string('full_name') }} as full_name,
        {{ clean_string('email', lower = true) }} as email,
        {{ clean_string('city') }} as city,
        {{ clean_string('tier') }} as tier,
        changed_at,
        _loaded_at

    from source

)

select * from renamed

