{#- Khoá ngày dạng số yyyymmdd. NULL (mốc chưa xảy ra) → -1 = dòng "Chưa xảy ra" của dim_date. -#}
{% macro date_key(expr) -%}
    coalesce(cast(strftime(cast({{ expr }} as date), '%Y%m%d') as integer), -1)
{%- endmacro %}
