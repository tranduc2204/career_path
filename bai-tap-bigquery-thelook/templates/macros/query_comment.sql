{#
  Biến comment của mỗi query thành LABEL của job BigQuery (cần query-comment job-label: true trong dbt_project.yml).
  dbt-bigquery tự chuẩn hoá giá trị: chữ thường, ký tự lạ → '_', tối đa 63 ký tự.
  Mọi job còn có sẵn label dbt_invocation_id.
#}
{% macro query_comment(node) %}
    {%- set comment_dict = {} -%}
    {%- do comment_dict.update(
        app='dbt',
        dbt_version=dbt_version,
        target_name=target.name,
    ) -%}
    {%- if node is not none -%}
        {%- do comment_dict.update(dbt_node=node.name, dbt_resource=node.resource_type) -%}
    {%- else -%}
        {%- do comment_dict.update(dbt_node='internal') -%}
    {%- endif -%}
    {% do return(tojson(comment_dict)) %}
{% endmacro %}
