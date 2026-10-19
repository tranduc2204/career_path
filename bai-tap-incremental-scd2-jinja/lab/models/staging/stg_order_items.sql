

with source as (

    select * from {{ source('raw', 'order_items') }}

),

renamed as (

    select
        order_id,
        line_no,
        product_id,
        quantity,
        {# unit_price_cents / 100 as unit_price, #}
        {{ cents_to_dollars('unit_price_cents') }} as unit_price,
        _loaded_at
    from source

)

select * from renamed

