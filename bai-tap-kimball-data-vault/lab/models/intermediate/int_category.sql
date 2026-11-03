{{
    config (
        materialized='view',
    )
}}

with recursive up as (
    select category_code as start_code, category_code as current_code, parent_code
    from {{ ref('stg_erp__categories') }}

    union all 

    select u.start_code, c.category_code, c.parent_code
    from up u join {{ ref('stg_erp__categories') }} c on c.category_code = u.parent_code
)
select start_code, current_code as category_l1_code
from up 
where parent_code is null





