

with source as (

    select * from {{ source('raw', 'customer_changelog') }}

),

renamed as (

    select
        customer_id,
        coalesce(trim(op),NULL) as op,
        coalesce(trim(full_name),NULL) as full_name,
        coalesce(trim(lower(email)),NULL) as email,
        coalesce(trim(city),NULL) as city,
        coalesce(trim(tier),NULL) as tier,
        changed_at,
        _loaded_at

    from source

)

select * from renamed

