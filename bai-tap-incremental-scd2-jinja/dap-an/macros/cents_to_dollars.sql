{# J1 — đổi cents sang dollars #}
{% macro cents_to_dollars(column_name, scale=2) -%}
    round({{ column_name }} / 100.0, {{ scale }})
{%- endmacro %}
