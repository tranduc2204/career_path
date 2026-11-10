



with info_fct_sales as (
select *
from {{ ref('fct_sales') }}

), result as (
select fc.*, fs.order_date_key
from {{ ref('fct_promotion_coverage') }} fc
left join info_fct_sales fs on fc.date_key =  fs.order_date_key and fc.product_key = fs.product_key
)



select   dd.date_key, dd.full_date, dp.sku, dp.product_name, dpr.promo_code, order_date_key
from result r
left join {{ ref('dim_date') }} dd on r.date_key = dd.date_key 
left join {{ ref('dim_product') }} dp on dp.product_key = r.product_key
left join {{ ref('dim_promotion') }} dpr on r.promotion_key = dpr.promotion_key 
where order_date_key is null and dd.full_date <= {{ business_date() }}





{# select
    c.date_key,
    d.full_date,
    p.sku,
    p.product_name,
    pr.promo_code
from {{ ref('fct_promotion_coverage') }} as c
inner join {{ ref('dim_date') }} as d using (date_key)
inner join {{ ref('dim_product') }} as p using (product_key)
inner join {{ ref('dim_promotion') }} as pr using (promotion_key)
where d.full_date <= {{ business_date() }}
  and not exists (
      select 1
      from {{ ref('fct_sales') }} as s
      where s.product_key = c.product_key
        and s.order_date_key = c.date_key
  ) #}










