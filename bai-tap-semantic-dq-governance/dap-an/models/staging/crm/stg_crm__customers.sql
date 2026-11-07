{#
  Q5: từ ngày 5 CRM đổi tên cột phone → phone_number. Model đọc danh sách cột thật của nguồn
  lúc chạy, nên chạy được với CẢ HAI phiên bản schema (trước và sau nâng cấp).
  Lưu ý: comment SQL (--) đặt ngay sau thẻ Jinja có dấu "-%}" sẽ dính vào dòng select → dùng comment Jinja.
#}
{%- set src = source('crm', 'customers') -%}
{%- set cols = [] -%}
{%- if execute -%}
  {%- set cols = adapter.get_columns_in_relation(src) | map(attribute='name') | map('lower') | list -%}
{%- endif -%}
{%- set phone_col = 'phone_number' if 'phone_number' in cols else 'phone' %}

select
    customer_id,
    full_name,
    lower(trim(email))   as email,
    {{ phone_col }}      as phone,
    city,
    lower(segment)       as segment,
    birth_date,
    signup_date,
    updated_at,
    _loaded_at
from {{ src }}
