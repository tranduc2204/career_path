-- J4 — như J3 nhưng danh sách trạng thái lấy từ dữ liệu thật
-- Thân model đã ref('stg_orders') nên không bắt buộc, nhưng khai rõ cho an toàn khi refactor:
-- depends_on: {{ ref('stg_orders') }}
{%- set statuses = get_order_statuses() %}

select
    customer_id,
    count(*) as total_orders
    {%- for s in statuses %},
    sum(case when order_status = '{{ s }}' then 1 else 0 end) as orders_{{ s }}
    {%- endfor %}
from {{ ref('stg_orders') }}
group by customer_id
