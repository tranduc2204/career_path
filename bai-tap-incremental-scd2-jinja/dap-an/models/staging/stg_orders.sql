{# I7 — chỉ chọn channel khi nguồn đã có cột này (introspection lúc compile) #}
{%- set source_columns = adapter.get_columns_in_relation(source('raw', 'orders'))
    | map(attribute='name') | map('lower') | list -%}

select
    order_id,
    customer_id,
    order_date,
    status                                          as order_status,
    {{ cents_to_dollars('amount_cents') }}          as amount,
    {%- if 'channel' in source_columns %}
    channel,
    {%- endif %}
    updated_at,
    _loaded_at
from {{ source('raw', 'orders') }}
