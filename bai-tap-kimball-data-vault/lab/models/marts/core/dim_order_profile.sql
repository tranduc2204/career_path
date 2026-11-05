

---  junk dimension gom 3 thuộc tính ít giá trị.
with group as (
    select distinct
        {{ dbt_utils.generate_surrogate_key(['channel', 'payment_method', 'is_gift']) }} as order_profile_key,
        channel,
        payment_method,
        is_gift
    from {{ ref('int_sales__lines') }}
)

select *
from group




























































































