{#
  B3 — staging cho orders. Các phần thêm dần theo bài:
  - I7 (ngày 4): cột channel chỉ có từ ngày 4
  - P1 (ngày 6): nguồn có dòng trùng → giữ 1 dòng / order_id
  - P2 (ngày 7): nguồn đổi tên status → order_status
  - P6 (ngày 11): nguồn thêm _is_deleted (soft delete)
#}
{%- set source_columns = adapter.get_columns_in_relation(source('raw', 'orders'))
    | map(attribute='name') | map('lower') | list -%}

with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        order_date,
        {%- if 'order_status' in source_columns %}
        order_status,
        {%- else %}
        status                                      as order_status,
        {%- endif %}
        {{ cents_to_dollars('amount_cents') }}      as amount,
        {%- if 'channel' in source_columns %}
        channel,
        {%- endif %}
        {%- if '_is_deleted' in source_columns %}
        coalesce(_is_deleted, false)                as is_deleted,
        {%- else %}
        false                                       as is_deleted,
        {%- endif %}
        updated_at,
        _loaded_at
    from source
)

select *
from renamed
qualify row_number() over (partition by order_id order by _loaded_at desc) = 1
