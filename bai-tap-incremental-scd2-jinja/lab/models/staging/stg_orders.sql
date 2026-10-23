{%- set source_columns = adapter.get_columns_in_relation(source('raw', 'orders'))
    | map(attribute='name') | map('lower') | list -%}


with source as (

    select * from {{ source('raw', 'orders') }}

),

renamed as (

    select distinct
        order_id,
        customer_id,
        order_date,
        status as  order_status,
        {# amount_cents / 100 as amount, #}
        {{ cents_to_dollars('amount_cents') }} as  amount,

        {%- if 'channel' in source_columns %}
            channel,
        {%- endif %}

        updated_at,
        _loaded_at

    from source

)

select * from renamed

