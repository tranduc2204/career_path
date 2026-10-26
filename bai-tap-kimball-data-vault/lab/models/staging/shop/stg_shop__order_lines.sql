with source as (
    select * from {{ source('shop', 'order_lines') }}
),

renamed as (
    select
        upper(trim(order_number))   as order_number,
        line_no,
        upper(trim(sku))            as sku,
        quantity,
        cast(unit_price as bigint)  as unit_price,      -- giá bán thực tế (đã trừ khuyến mãi nếu có)
        _loaded_at
    from source
)

select * from renamed
