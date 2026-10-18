

with source as (

    select * from {{ source('raw', 'order_items') }}

),

renamed as (

    select
        order_id,
        line_no,
        product_id,
        quantity,
        unit_price_cents,
        _loaded_at

    from source

)

select * from renamed

