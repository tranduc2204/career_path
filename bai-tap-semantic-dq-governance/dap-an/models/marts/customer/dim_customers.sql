-- v1 (deprecated 31/01/2027), viết trong file gốc dim_customers.sql nhờ `defined_in`: giữ nguyên giao diện cũ cho dashboard chưa chuyển.
select
    customer_id,
    {{ mask_pii('full_name', 'name') }}   as full_name,
    {{ mask_pii('email', 'email') }}      as email,
    {{ mask_pii('phone', 'phone') }}      as phone,
    city,
    segment,
    {{ mask_pii('birth_date', 'date') }}  as birth_date,
    signup_date
from {{ ref('stg_crm__customers') }}
