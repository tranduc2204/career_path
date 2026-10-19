{% macro get_order_statuses() %}
    {% if execute %}
        {%- set results = run_query("select distinct order_status from " ~ ref('stg_orders') ~ " order by 1") %}
        {{ return(results.columns[0].values() | list) }}
    {% else %}
        {{ return([0]) }}
    {% endif %}
{% endmacro %}
