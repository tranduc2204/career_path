
with customer_info as (
    select *, 
    {{ dbt_utils.generate_surrogate_key(['city','loyalty_tier']) }} as customer_check
    from {{ ref('stg_crm__customers') }}
), tmp as (
select *, lag(customer_check) over(partition by customer_code order by extract_date asc) as next_customer_check
from customer_info
), customer_change as (
select *
from tmp 
where customer_check != next_customer_check or next_customer_check is null
)
, valid_from as (
select 
       *,
        case
            when row_number() over(partition by customer_code order by (extract_date) asc) = 1
                then '1900-01-01'::date
            else extract_date
        end as valid_from

from customer_change

), valid_to as (
select *, 

case 
    when lead(valid_from) over(partition by customer_code order by (valid_from) asc) is null then '9999-12-31'::date
    else lead(valid_from) over(partition by customer_code order by (valid_from) asc)
    end as valid_to

from valid_from
)
select 
    {{ dbt_utils.generate_surrogate_key(['customer_code','valid_from']) }} as customer_key,
    customer_code,
    full_name,
    email,
    city,
    loyalty_tier,
    valid_from,
    valid_to,
    case when valid_to = '9999-12-31'::date then true else false end as is_current,
    false as is_inferred
from valid_to 


union all

select 
    -1 as customer_key,
    -1 as customer_code,
    'Khách vãng lai / không xác định' as full_name,
    null as email,
    'Không xác định' as city,
    'Không xác định' as loyalty_tier,
    '1900-01-01'::date as valid_from,
    '9999-12-31'::date as valid_to,
    false as is_current,
    true as is_inferred



