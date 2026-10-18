

with source as (

    select * from {{ source('raw', 'orders') }}

),

renamed as (

    select
        order_id,
        customer_id,
        order_date,
        status,
        amount_cents,
        updated_at,
        _loaded_at

    from source

)

select * from renamed

