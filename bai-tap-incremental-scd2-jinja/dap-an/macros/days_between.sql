{# J9 — adapter.dispatch: mỗi warehouse một cách cài đặt #}
{% macro days_between(start_date, end_date) -%}
    {{ return(adapter.dispatch('days_between')(start_date, end_date)) }}
{%- endmacro %}

{% macro default__days_between(start_date, end_date) -%}
    {{ dbt.datediff(start_date, end_date, 'day') }}
{%- endmacro %}

{% macro duckdb__days_between(start_date, end_date) -%}
    date_diff('day', cast({{ start_date }} as date), cast({{ end_date }} as date))
{%- endmacro %}
