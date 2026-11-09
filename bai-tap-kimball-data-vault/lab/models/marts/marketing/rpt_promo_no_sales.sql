

select *
from {{ ref('fct_promotion_coverage') }} 
{# where date_key not exists in  #}
{# select order_date_key, 
from {{ ref('fct_sales') }}
where order_date_key <= {{ date_key('{{ business_date() }}')}} #}









































