{#
  ĐỒNG HỒ CỦA LAB. dbt-duckdb lấy "bây giờ" qua macro current_timestamp() → duckdb__current_timestamp().
  Macro cùng tên trong project gốc được ưu tiên hơn bản của adapter, nên mọi chỗ dbt cần "bây giờ"
  (source freshness, snapshot, ...) sẽ dùng giờ giả lập của lab (biến lab_now do simulate.py ghi).
  Ở công ty thật KHÔNG làm thế này: đây chỉ là cách để 7 "ngày" của lab chạy trong vài phút.
#}
{% macro duckdb__current_timestamp() -%}
  {%- if var('lab_now', none) -%}
    cast('{{ var("lab_now") }}' as timestamp)
  {%- else -%}
    now()
  {%- endif -%}
{%- endmacro %}
