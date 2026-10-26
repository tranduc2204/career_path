-- DRILL-ACROSS: 2 fact khác grain không join trực tiếp với nhau.
-- Bước 1: đưa TỪNG fact về grain chung (tháng × danh mục cấp 1) qua thuộc tính CONFORMED.
-- Bước 2: full outer join 2 kết quả trên các thuộc tính chung.
with actual as (
    select
        d.month_key,
        p.category_l1_code,
        sum(f.net_amount)           as actual_net_amount
    from {{ ref('fct_sales') }} as f
    inner join {{ ref('dim_date') }} as d on d.date_key = f.order_date_key
    inner join {{ ref('dim_product') }} as p using (product_key)
    group by d.month_key, p.category_l1_code
),

target as (
    select
        t.month_key,
        c.category_l1_code,
        t.target_amount
    from {{ ref('fct_sales_target') }} as t
    inner join {{ ref('dim_category_l1') }} as c using (category_l1_key)
)

select
    coalesce(t.month_key, a.month_key)                      as month_key,
    coalesce(t.category_l1_code, a.category_l1_code)        as category_l1_code,
    c.category_l1_name,
    t.target_amount,
    coalesce(a.actual_net_amount, 0)                        as actual_net_amount,
    coalesce(a.actual_net_amount, 0) * 1.0 / nullif(t.target_amount, 0)   as achievement_ratio
from target as t
full outer join actual as a
    on  a.month_key = t.month_key
    and a.category_l1_code = t.category_l1_code
left join {{ ref('dim_category_l1') }} as c
    on c.category_l1_code = coalesce(t.category_l1_code, a.category_l1_code)
