-- Các mốc "as of" = mỗi lần kho nạp dữ liệu (06:00 sáng hằng ngày).
-- PIT trả lời: "ngay sau lần nạp X, vault biết gì về khách?"
select distinct _loaded_at as AS_OF_DATE
from {{ ref('stg_crm__customers') }}
