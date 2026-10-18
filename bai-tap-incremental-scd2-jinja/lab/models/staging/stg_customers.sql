

with source as (

    select * from {{ source('raw', 'customers') }}

),

renamed as (

    select
        customer_id,
        nullif(trim(full_name),NULL) as full_name,
        nullif(trim(lower(email)),NULL) as email,
        nullif(trim(city),NULL) as city,
        nullif(trim(tier),NULL) as tier,
        updated_at,
        _loaded_at

    from source

)

select * from renamed

