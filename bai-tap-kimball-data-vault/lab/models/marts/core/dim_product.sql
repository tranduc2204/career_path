

with product_info as (
    select *
    from {{ ref('stg_erp__products') }}
), recursivee as (
    select category_code as start_code, category_code as current_code, parent_code
    from {{ ref('stg_erp__categories') }}
    union all 
    -- leo lên 1 bậc
    select u.start_code, c.category_code, c.parent_code
    from recursivee u join {{ ref('stg_erp__categories') }} c on c.category_code = u.parent_code
)
select *
from recursivee 
where parent_code is null


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



