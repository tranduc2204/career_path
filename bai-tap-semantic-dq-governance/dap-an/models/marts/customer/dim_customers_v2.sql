-- v2: bỏ phone và birth_date khỏi giao diện public (giảm PII), thêm age_band, đổi segment → customer_segment.
select
    customer_id,
    {{ mask_pii('full_name', 'name') }}   as full_name,
    {{ mask_pii('email', 'email') }}      as email,
    city,
    segment                               as customer_segment,
    case
        when birth_date is null then 'unknown'
        when date_diff('year', birth_date, cast({{ current_timestamp() }} as date)) < 25 then '18-24'
        when date_diff('year', birth_date, cast({{ current_timestamp() }} as date)) < 35 then '25-34'
        when date_diff('year', birth_date, cast({{ current_timestamp() }} as date)) < 45 then '35-44'
        else '45+'
    end                                   as age_band,
    signup_date
from {{ ref('stg_crm__customers') }}
