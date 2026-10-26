-- Multi-active satellite so sánh CẢ TẬP số điện thoại của lần nạp mới với tập gần nhất,
-- nên stage của nó chỉ được chứa ĐÚNG MỘT lần nạp: file CRM mới nhất.
select *
from {{ ref('stg_crm__customer_phones') }}
where extract_date = (select max(extract_date) from {{ ref('stg_crm__customer_phones') }})
