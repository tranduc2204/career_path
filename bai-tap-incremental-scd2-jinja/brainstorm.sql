-- brain storm cá nhân J1 macro 
{% macro cents_to_dollars(column_name, scale=2) %}

    round( {{column_name}} / 100.0, {{scale}} )

{% endmacro %}




