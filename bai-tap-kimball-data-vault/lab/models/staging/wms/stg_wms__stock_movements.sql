with source as (
    select * from {{ source('wms', 'stock_movements') }}
),

renamed as (
    select
        movement_id,
        upper(trim(sku))            as sku,
        upper(warehouse_code)       as warehouse_code,
        movement_date,
        qty_change,
        lower(reason)               as reason,
        _loaded_at
    from source
)

select * from renamed
