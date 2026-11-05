


with order_info  as (
    select 
        cast(strftime(cast(order_date as date), '%Y%m%d') as integer) as order_date_key  ,
        customer_code,
        sku as product_key,
        {{ dbt_utils.generate_surrogate_key(['channel', 'payment_method', 'is_gift']) }} as order_profile_key,
        case 
            when channel = 'store'
                then 'POS'
            else '-2'
        end as store_location_key,
        case
            when channel ='store'
                then 'POS'
            else 'SHOP'
        end as source_system,
        order_number,
        line_no, 
        order_ts, 
        quantity, 
        unit_price,
        quantity * unit_price as gross_amount

    from {{ ref('int_sales__lines') }}
), info_voucher as (	
    select 
        order_number,
	    sum (discount_amount) as total_amount_voucher
        
    from {{ ref('stg_shop__order_vouchers') }}
    group by order_number 
)
, shares as (
    select o.*,
        sum (gross_amount) over(partition by o.order_number) as order_gross_amount,
         max (line_no) over(partition by o.order_number) as is_last_line
         , i.total_amount_voucher
       
    from order_info o
    left join info_voucher i 
    on o.order_number = i.order_number 
    where o.order_number = 'W0012'
), parts as (

select *,
case 
    when line_no <> is_last_line
        then round (total_amount_voucher * gross_amount / order_gross_amount)
end as discount_part
from shares
)
select 
    order_date_key
    customer_code,
    product_key,
    order_profile_key,
    store_location_key,
    source_system,
    order_number, 
    line_no, 
    order_ts,
    quantity,
    unit_price,
    gross_amount,
    

    coalesce(discount_part,
                total_amount_voucher - coalesce(sum(discount_part) over(partition by order_number),0)) as discount_allocated
    

from parts
























