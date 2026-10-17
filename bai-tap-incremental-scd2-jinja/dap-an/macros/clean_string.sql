{# J2 — trim, (tuỳ chọn) lower, chuỗi rỗng → null #}
{% macro clean_string(column_name, lower=false) -%}
    {%- set expr = 'trim(' ~ column_name ~ ')' -%}
    {%- if lower -%}
        {%- set expr = 'lower(' ~ expr ~ ')' -%}
    {%- endif -%}
    nullif({{ expr }}, '')
{%- endmacro %}
