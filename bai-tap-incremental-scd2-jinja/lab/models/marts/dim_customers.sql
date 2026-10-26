

with customer_info as (
    select 
        {{ dbt_utils.generate_surrogate_key(['customer_id', 'dbt_valid_from']) }} as customer_sk,
        customer_id, 
        full_name,
        email, 
        city,
        tier,
        dbt_valid_from as valid_from,
        COALESCE(dbt_valid_to, '9999-12-31') as valid_to,
        dbt_valid_to is null as  is_current
    from {{ ref('snap_customers') }}
   

), 
unknown_member as (
    select
        '-1'                                as customer_sk,
        -1                                  as customer_id,
        'Unknown'                           as full_name,
        cast(null as varchar)               as email,
        'Unknown'                           as city,
        'Unknown'                           as tier,
        cast('1900-01-01' as timestamp)     as valid_from,
        cast('9999-12-31' as timestamp)     as valid_to,
        true                                as is_current
)
select *
from customer_info      
union all 
select * from unknown_member                                                                                                                                                                                                               


















