

with source as (

    select * from {{ source('raw', 'products') }}

),

renamed as (

    select
        product_id,
        product_name,
        category,
        list_price_cents,
        _loaded_at

    from source

)

select * from renamed

