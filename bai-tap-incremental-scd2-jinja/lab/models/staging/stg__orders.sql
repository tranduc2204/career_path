

with source as (

    select * from {{ source('raw', 'orders') }}

),

renamed as (

    select distinct
        order_id,
        customer_id,
        order_date,
        status,
        amount_cents / 100 as amount,
        updated_at,
        _loaded_at

    from source

)

select * from renamed

