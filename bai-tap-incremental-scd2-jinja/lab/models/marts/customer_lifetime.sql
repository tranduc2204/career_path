

with info_customers as (
    select *
    from {{ ref('stg_customers') }}
),
fct_orders as (
    select *
    from {{ ref('fct_order_lines') }}
)
select ord.customer_id, count (distinct order_id) as order_count, sum (line_amount) as lifetime_value,
 min (order_date) as first_order_date, max (order_date) as last_order_date
from fct_orders ord
left join info_customers cus on ord.customer_id = cus.customer_id
where ord.order_status != 'cancelled'
group by ord.customer_id
