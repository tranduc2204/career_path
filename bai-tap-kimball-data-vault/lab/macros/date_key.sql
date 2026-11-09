{% macro date_key(expr) -%}
    coalesce(cast(strftime(cast({{ expr }} as date), '%Y%m%d') as integer), -1)
{%- endmacro %}
