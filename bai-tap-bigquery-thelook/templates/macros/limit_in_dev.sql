{#
  Giới hạn dữ liệu ở dev / ci để rẻ và nhanh. Prod không bị ảnh hưởng.
  Dùng ở cuối model staging:   {{ limit_in_dev('created_at') }}
  (Model đã có WHERE thì dùng: {{ limit_in_dev('created_at', keyword='and') }})
#}
{% macro limit_in_dev(column, days=90, keyword='where') -%}
    {%- if target.name in ['dev', 'ci'] -%}
        {{ keyword }} {{ column }} >= timestamp_sub(current_timestamp(), interval {{ days }} day)
    {%- endif -%}
{%- endmacro %}
