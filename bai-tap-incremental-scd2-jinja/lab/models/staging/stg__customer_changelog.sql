

with source as (

    select * from {{ source('raw', 'customer_changelog') }}

),

renamed as (

    select
        customer_id,
        trim(op) as op,
        trim(full_name) as full_name,
        trim(lower(email)) as email,
        trim(city) as city,
        trim(tier) as  tier,
        changed_at,
        _loaded_at

    from source

)

select * from renamed

