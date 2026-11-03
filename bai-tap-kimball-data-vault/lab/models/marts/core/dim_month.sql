
select distinct 
    month_key,
    month_start_date,
    month_number,
    month_name_vi,
    quarter_number,
    year_number
from {{ ref('dim_date') }}
where date_key <> -1

