{# J4 — lấy danh sách trạng thái từ dữ liệu thật bằng run_query #}
{% macro get_order_statuses() %}
    {% if execute %}
        {% set q %}
            select distinct order_status from {{ ref('stg_orders') }} order by 1
        {% endset %}
        {% set rows = run_query(q) %}
        {{ return(rows.columns[0].values() | list) }}
    {% else %}
        {{ return([]) }}
    {% endif %}
{% endmacro %}
