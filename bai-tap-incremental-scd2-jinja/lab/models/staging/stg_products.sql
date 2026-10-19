

with source as (

    select * from {{ source('raw', 'products') }}

),

renamed as (

    select
        product_id,
        {{ clean_string('product_name') }} as product_name,
        {{ clean_string('category') }} as category,
        nullif( {{ cents_to_dollars('list_price_cents') }},NULL) as list_price,
        _loaded_at

    from source

)

select * from renamed

