

with source as (

    select * from {{ source('raw', 'customer_changelog') }}

),

renamed as (

    select
        customer_id,
     
        {{ clean_string('op') }},
        {{ clean_string('full_name') }},
        {{ clean_string('email', lower = true) }},
        {{ clean_string('city') }},
        {{ clean_string('tier') }},
        changed_at,
        _loaded_at

    from source

)

select * from renamed

