

with source as (

    select * from {{ source('raw', 'customers') }}

),

renamed as (

    select
        customer_id,
        coalesce(trim(full_name),NULL) as full_name,
        coalesce(trim(lower(email)),NULL) as email,
        coalesce(trim(city),NULL) as city,
        coalesce(trim(tier),NULL) as tier,
        updated_at,
        _loaded_at

    from source

)

select * from renamed

