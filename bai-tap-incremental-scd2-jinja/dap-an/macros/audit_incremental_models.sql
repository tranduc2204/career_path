{# J8 — dbt run-operation audit_incremental_models
   Liệt kê model incremental của project, báo lỗi nếu merge/delete+insert mà thiếu unique_key. #}
{% macro audit_incremental_models() %}
    {% if execute %}
        {% set issues = [] %}
        {% set models = graph.nodes.values()
            | selectattr('resource_type', 'equalto', 'model')
            | selectattr('package_name', 'equalto', project_name) %}
        {{ print('model | strategy | unique_key | on_schema_change') }}
        {% for node in models | sort(attribute='name') %}
            {% if node.config.materialized == 'incremental' %}
                {% set strategy = node.config.incremental_strategy or 'default' %}
                {% set key = node.config.unique_key %}
                {{ print(node.name ~ ' | ' ~ strategy ~ ' | ' ~ key ~ ' | ' ~ node.config.on_schema_change) }}
                {% if strategy in ['merge', 'delete+insert'] and not key %}
                    {% do issues.append(node.name) %}
                {% endif %}
            {% endif %}
        {% endfor %}
        {% if issues %}
            {{ exceptions.raise_compiler_error('Model thiếu unique_key: ' ~ issues | join(', ')) }}
        {% endif %}
    {% endif %}
{% endmacro %}
