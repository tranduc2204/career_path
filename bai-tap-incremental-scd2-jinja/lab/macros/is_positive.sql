{%- test is_positive (model, column_name, allow_zero = true)  -%}

    select *
    from {{ model }}
    where {{ column_name }} {{ '<' if allow_zero else '<='  }} 0
 
{% endtest %}