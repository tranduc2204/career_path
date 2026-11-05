

with order_info as (
    select *
    from {{ ref('int_sales__lines') }}
),
customer_info as (
    select * 
    from {{ ref('dim_customer') }}
)
, info_voucher as (	
    select 
        order_number,
	    sum (discount_amount) as total_amount_voucher
        
    from {{ ref('stg_shop__order_vouchers') }}
    group by order_number 
),
info_shipping as (
    select 
        order_number,
        shipping_fee
    from {{ ref('stg_shop__orders') }}
), pre_result as (
select ord.*, coalesce(cus.customer_key,'-1') as customer_key,
    {{ dbt_utils.generate_surrogate_key(['channel', 'payment_method', 'is_gift']) }} as order_profile_key,
    case 
        when channel = 'store' 
            then 'POS'
        else '-2'
    end as store_location_key,
    case
            when channel ='store'
                then 'pos'
            else 'shop'
    end as source_system,
    order_ts,
    quantity,
    unit_price, 
    quantity * unit_price as gross_amount,
    sum (gross_amount) over(partition by ord.order_number) order_gross_amount,
    max(line_no) over(partition by ord.order_number) as last_line
from order_info ord 
left join customer_info cus
    on ord.customer_code = cus.customer_code and (order_ts >= cus.valid_from and order_ts < cus.valid_to)
where order_number = 'W0012'

), result as (
select pre.*, total_amount_voucher,
    case 
        when line_no <> last_line
            then round (total_amount_voucher * gross_amount / order_gross_amount ,2)
    end as discount_part,shipping_fee,
    case 
        when line_no <> last_line 
            then round (shipping_fee * gross_amount / order_gross_amount,2)
    end as shipping_part
from pre_result pre
left join info_voucher iv on pre.order_number = iv.order_number
left join info_shipping iss on pre.order_number = iss.order_number 

), result_end as (
select *,
    round (coalesce(discount_part, total_amount_voucher - coalesce(sum (discount_part) over(partition by order_number),0)),2) discount_allocated,
    round (coalesce(shipping_part, shipping_fee - coalesce(sum (shipping_part) over(partition by order_number),0)),2) shipping_fee_allocated

from result 
)
select 
    cast(strftime(cast(order_date as date), '%Y%m%d') as integer) as order_date_key  ,
    customer_key,
    sku as product_key,
    order_profile_key,
    store_location_key,
    source_system, 
    order_number, line_no,
    order_ts, 
    quantity, 
    unit_price, 
    gross_amount,
    discount_allocated, 
    shipping_fee_allocated,
    gross_amount - (discount_allocated + shipping_fee_allocated) as net_amount
from result_end 



























