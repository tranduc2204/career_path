-- J3 — pivot số đơn theo trạng thái, danh sách trạng thái lấy từ var
{%- set statuses = var('order_statuses') %}

select
    customer_id,
    count(*) as total_orders,
    {%- for s in statuses %}
    sum(case when order_status = '{{ s }}' then 1 else 0 end) as orders_{{ s }}
    {{- "," if not loop.last }}
    {%- endfor %}
from {{ ref('stg_orders') }}
group by customer_id
