-- Cách 1 (DuckDB/Postgres): EXCLUDE CURRENT ROW
select
    cua_hang,
    ngay,
    doanh_thu - avg(doanh_thu) over (
        partition by cua_hang, date_trunc('month', ngay)
        rows between unbounded preceding and unbounded following
        exclude current row
    ) as chenh_lech
from doanh_thu_ngay

-- Cách 2 (portable, BigQuery/Snowflake):
--   doanh_thu - (sum(doanh_thu) over p - doanh_thu) / nullif(count(*) over p - 1, 0)
--   với p = (partition by cua_hang, date_trunc('month', ngay))
