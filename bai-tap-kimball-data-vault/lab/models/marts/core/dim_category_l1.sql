{# with category_l1_info as (
    select
        i.start_code,
        i.category_l1_code,
       
    from {{ ref('int_category') }} i
    left join {{ ref('stg_erp__categories') }} s on s.category_code = i.category_l1_code
)
select *
from category_l1_info #}

with category as (
    select distinct 
        i.category_l1_code
    from {{ ref('int_category') }} i 
),
category_l1_info as (
    select 
        {{ dbt_utils.generate_surrogate_key(['s.category_code']) }} as category_l1_key,
        s.category_code as category_l1_code,
        s.category_name as category_l1_name
    from category c
    left join {{ ref('stg_erp__categories') }} s on c.category_l1_code = s.category_code
)
select *
from category_l1_info