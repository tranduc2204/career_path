


with order_shop_line_info as (
    select *
    from {{ ref('stg_shop__order_lines') }}
), 
order_shop_info as (
    select *
    from {{ ref('stg_shop__orders') }}
),
pos_sales_info as (
    select *
    from {{ ref('stg_pos__sales') }}

)
select order_date, order_ts,sol.order_number , sol.line_no , customer_code, so.channel , so.payment_method,  order_status, sku,quantity, unit_price , is_gift
from order_shop_line_info sol
left join order_shop_info so
    on sol.order_number  = so.order_number

union all

select sale_date, sale_ts,receipt_no, line_no, customer_code,  'store' as channel, payment_method, 'paid' as order_status, sku, quantity, unit_price, false as is_gift
from pos_sales_info sps 

























































       