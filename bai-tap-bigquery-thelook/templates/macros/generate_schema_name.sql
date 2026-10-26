{#
  Đặt tên dataset theo môi trường:
    prod: dùng thẳng custom schema           → staging, marts
    dev / ci: <dataset của target>_<custom>  → dbt_duc_marts, ci_pr_12_marts
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
