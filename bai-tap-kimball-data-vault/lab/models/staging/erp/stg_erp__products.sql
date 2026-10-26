with source as (
    select * from {{ source('erp', 'products') }}
),

renamed as (
    select
        upper(trim(sku))            as sku,
        trim(product_name)          as product_name,
        trim(brand)                 as brand,
        upper(trim(category_code))  as category_code,
        cast(list_price as bigint)  as list_price,
        _loaded_at
    from source
)

select * from renamed
