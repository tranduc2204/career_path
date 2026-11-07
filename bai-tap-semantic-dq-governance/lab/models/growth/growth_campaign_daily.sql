-- Model của đội Growth: hiệu quả từng nguồn quảng cáo theo ngày.
-- Viết từ hồi chưa có quy định truy cập, nên đang ref thẳng vào staging của đội Commerce (bài G2).
with orders as (
    select order_date, utm_source, count(*) as orders, sum(items_amount) as revenue
    from (
        select o.order_id, o.order_date, o.utm_source, sum(i.line_amount) as items_amount
        from {{ ref('stg_shop__orders') }} o
        join {{ ref('stg_shop__order_items') }} i using (order_id)
        where o.status <> 'cancelled'
        group by 1, 2, 3
    )
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
