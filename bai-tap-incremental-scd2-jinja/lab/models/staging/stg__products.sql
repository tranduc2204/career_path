

with source as (

    select * from {{ source('raw', 'products') }}

),

renamed as (

    select
        product_id,
        coalesce(trim(product_name),NULL) as product_name,
        coalesce(trim(category),NULL) as category,
        coalesce(list_price_cents / 100,NULL) as list_price,
        _loaded_at

    from source

)

select * from renamed

