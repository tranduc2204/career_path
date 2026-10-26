-- Fact kế hoạch. GRAIN: 1 tháng × 1 danh mục cấp 1 (thô hơn fct_sales rất nhiều).
select
    m.month_key,
    c.category_l1_key,
    t.target_amount
from {{ ref('stg_erp__sales_targets') }} as t
inner join {{ ref('dim_month') }} as m on m.month_start_date = t.target_month
inner join {{ ref('dim_category_l1') }} as c on c.category_l1_code = t.category_code
