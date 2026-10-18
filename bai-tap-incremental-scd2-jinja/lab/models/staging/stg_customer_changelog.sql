

with source as (

    select * from {{ source('raw', 'customer_changelog') }}

),

renamed as (

    select
        customer_id,
        nullif(trim(op),NULL) as op,
        nullif(trim(full_name),NULL) as full_name,
        nullif(trim(lower(email)),NULL) as email,
        nullif(trim(city),NULL) as city,
        nullif(trim(tier),NULL) as tier,
        changed_at,
        _loaded_at

    from source

)

select * from renamed

