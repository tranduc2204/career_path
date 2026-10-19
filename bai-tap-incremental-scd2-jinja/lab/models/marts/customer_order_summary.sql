
{%- set statuses = var('order_statuses') %}



select ord.customer_id, count ( order_id) as total_orders, 

{%- for s in statuses -%}
sum (case when ord.order_status = '{{ s }}' then 1 else 0 end) as orders_{{s}}
{{- "," if not loop.last }}
{%- endfor %}


from {{ ref ('stg_orders') }}  ord 
group by ord.customer_id
