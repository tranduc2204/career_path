-- Dimension ngày dùng chung (conformed). Được "đóng nhiều vai" (role-playing): ngày đặt, ngày giao, ngày chụp tồn kho...
-- Dòng -1 = "Chưa xảy ra": để khoá ngày của mốc chưa tới KHÔNG bao giờ null.
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2026-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
),

days as (
    select cast(date_day as date) as full_date from spine
)

select
    cast(strftime(cast(full_date as date), '%Y%m%d') as integer) as date_key,   
    full_date,
    isodow(full_date)                                   as day_of_week,
    case isodow(full_date)
        when 1 then 'Thứ Hai' when 2 then 'Thứ Ba' when 3 then 'Thứ Tư' when 4 then 'Thứ Năm'
        when 5 then 'Thứ Sáu' when 6 then 'Thứ Bảy' else 'Chủ Nhật'
    end                                                 as day_name_vi,
    isodow(full_date) in (6, 7)                         as is_weekend,
    cast(strftime(full_date, '%Y%m') as integer)        as month_key,
    month(full_date)                                    as month_number,
    'Tháng ' || month(full_date)                        as month_name_vi,
    quarter(full_date)                                  as quarter_number,
    year(full_date)                                     as year_number,
    cast(date_trunc('month', full_date) as date)        as month_start_date
from days

union all

select
    -1, null, null, 'Chưa xảy ra', null, -1, null, 'Chưa xảy ra', null, null, null
