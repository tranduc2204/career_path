-- G2: đội Growth chỉ được dùng model PUBLIC của đội Commerce (fct_*), không ref thẳng staging của họ.
with orders as (
    select order_date, utm_source, count(*) as orders, sum(items_amount) as revenue
    from {{ ref('fct_orders') }}
    where not is_cancelled
    group by 1, 2
),
spend as (
    select spend_date as order_date, utm_source, spend from {{ ref('stg_mkt__ad_spend') }}
)
select
    coalesce(o.order_date, s.order_date)  as report_date,
    coalesce(o.utm_source, s.utm_source)  as utm_source,
    coalesce(o.orders, 0)                 as orders,
    coalesce(o.revenue, 0)                as revenue,
    coalesce(s.spend, 0)                  as spend
from orders o
full join spend s using (order_date, utm_source)
