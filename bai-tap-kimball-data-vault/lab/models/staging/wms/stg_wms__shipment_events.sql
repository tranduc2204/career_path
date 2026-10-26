with source as (
    select * from {{ source('wms', 'shipment_events') }}
),

renamed as (
    select
        event_id,
        upper(trim(order_number))   as order_number,
        lower(event_type)           as event_type,
        event_ts,
        upper(warehouse_code)       as warehouse_code,
        _loaded_at
    from source
)

select * from renamed
