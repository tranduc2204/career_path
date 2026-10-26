-- Shrunken rollup dimension của dim_date: cùng tên cột, cùng giá trị, chỉ ở grain tháng.
-- Dùng cho fact có grain tháng (chỉ tiêu doanh thu). Vì "conformed" nên drill-across với dim_date được.
select distinct
    month_key,
    month_start_date,
    month_number,
    month_name_vi,
    quarter_number,
    year_number
from {{ ref('dim_date') }}
where date_key <> -1
