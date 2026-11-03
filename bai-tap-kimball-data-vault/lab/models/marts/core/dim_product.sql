

with product_info as (
    select *
    from {{ ref('stg_erp__products') }}
), 

category_l1_info as (
    select i.start_code,  i.category_l1_code, s.category_name as category_l1_name
    from {{ ref('int_category') }} i
    left join {{ ref('stg_erp__categories') }} s on s.category_code = i.category_l1_code
   
),
category_info as (
    select s.*, i.category_l1_code, i.category_l1_name
    from {{ ref('stg_erp__categories') }} s
    left join category_l1_info i on s.category_code = i.start_code
)
select 
     
    {{ dbt_utils.generate_surrogate_key(['prd.sku']) }} as product_key,
    sku,
    prd.product_name, 
    brand, 
    list_price,
    cat.category_code, 
    cat.category_name, 
    cat.category_l1_code, 
    cat.category_l1_name
from product_info prd
left join category_info cat on prd.category_code = cat.category_code

union all

select 
    -1 as product_key,
    -1 as sku,
    'Không xác định' as product_name,
    null as brand,
    null as list_price,
    null as category_code,
    null as category_name,
    null as category_l1_code,
    null as category_l1_name

{# 
recursive up as (
    -- anchor: mọi danh mục, bắt đầu với "cha hiện tại" = chính nó
    select category_code as start_code, category_code as current_code, parent_code
    from dev_staging.stg_erp__categories
    union all
    -- leo lên 1 bậc
    select u.start_code, c.category_code, c.parent_code
    from up u join dev_staging.stg_erp__categories c on c.category_code = u.parent_code
)
select start_code, current_code as category_l1_code
from up 
where parent_code is null    #}



