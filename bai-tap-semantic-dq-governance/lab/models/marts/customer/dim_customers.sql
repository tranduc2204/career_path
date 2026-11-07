-- 1 dòng / khách. Chứa PII (full_name, email, phone, birth_date): xem bài G5.
select
    customer_id,
    full_name,
    email,
    phone,
    city,
    segment,
    birth_date,
    signup_date
from {{ ref('stg_crm__customers') }}
