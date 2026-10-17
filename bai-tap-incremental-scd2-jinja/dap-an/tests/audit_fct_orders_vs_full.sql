-- I9 — so fct_orders (incremental) với kết quả tính lại toàn bộ từ staging. Trả về dòng lệch.
with full_recompute as (
    select order_id, order_status, amount from {{ ref('stg_orders') }}
),
incremental as (
    select order_id, order_status, amount from {{ ref('fct_orders') }}
),
missing as (select * from full_recompute except select * from incremental),
extra   as (select * from incremental except select * from full_recompute)

select 'thiếu/sai trong incremental' as issue, * from missing
union all
select 'thừa trong incremental' as issue, * from extra
