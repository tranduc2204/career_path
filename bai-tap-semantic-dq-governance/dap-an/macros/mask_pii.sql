{#
  G5: che PII khi target không có quyền (var pii_access = false).
    email     → ký tự đầu + '***@' + tên miền          (an.nguyen12@gmail.com → a***@gmail.com)
    phone     → toàn '*' trừ 3 số cuối                  (0912345678 → *******678)
    name      → giữ từ đầu tiên (họ) + ' ***'          (Nguyễn Văn An → Nguyễn ***)
    date      → về ngày đầu năm                         (1994-07-15 → 1994-01-01)
  Đây là che ở TẦNG dbt (dev/CI/sandbox). Ở production thật, che ở tầng warehouse
  (Snowflake masking policy, BigQuery policy tag) để không phụ thuộc vào việc ai chạy dbt.
#}
{% macro mask_pii(column, kind) -%}
  {%- set allowed = var('pii_access', false) -%}
  {%- if allowed in [true, 'True', 'true'] -%}
    {{ column }}
  {%- elif kind == 'email' -%}
    left({{ column }}, 1) || '***@' || split_part({{ column }}, '@', 2)
  {%- elif kind == 'phone' -%}
    repeat('*', length({{ column }}) - 3) || right({{ column }}, 3)
  {%- elif kind == 'name' -%}
    split_part({{ column }}, ' ', 1) || ' ***'
  {%- elif kind == 'date' -%}
    cast(date_trunc('year', {{ column }}) as date)
  {%- else -%}
    {{ exceptions.raise_compiler_error("mask_pii: kind không hợp lệ: " ~ kind) }}
  {%- endif -%}
{%- endmacro %}
