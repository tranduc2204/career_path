{% test one_current_row_per_key(model, column_name, current_condition='dbt_valid_to is null') %}
select {{ column_name }}, count(*) as n_current
from {{ model }}
where {{ current_condition }}
group by {{ column_name }}
having count(*) > 1
{% endtest %}
