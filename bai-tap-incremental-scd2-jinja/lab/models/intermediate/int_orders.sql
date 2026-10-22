{{
    config(
        materialized='view'
    )
}}

select 
    {{ dbt_utils.star(ref('stg_orders')) }}
    , 
    order_status not in (
        {% for s in var('non_revenue_statuses') %}
            '{{s}}' {{',' if not loop.last}}
        {% endfor %}
    ) as is_revenue_order
from {{ ref('stg_orders') }}




