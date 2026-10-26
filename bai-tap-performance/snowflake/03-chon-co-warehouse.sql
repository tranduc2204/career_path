-- =====================================================================================================
-- S3. Cỡ warehouse nào đáng tiền cho một query nặng?
-- Lý thuyết: GD2-ly-thuyet/tuan-7/03-snowflake-warehouse-va-resource-monitor.md
-- =====================================================================================================
use warehouse perf_wh;
use schema perf_lab.exp;
alter session set use_cached_result = false;
alter session set query_tag = 'perf_lab_s3';

-- Query thử: kiểu TPC-H Q1 trên 600 triệu dòng. Chạy lần lượt ở 4 cỡ.
-- (Resize không làm mất credit; mỗi lần warehouse BẬT LẠI sau khi suspend mới tính tối thiểu 60 giây.)

alter warehouse perf_wh set warehouse_size = 'XSMALL';
select l_returnflag, l_linestatus, sum(l_quantity), sum(l_extendedprice),
       sum(l_extendedprice * (1 - l_discount)), avg(l_discount), count(*)
from snowflake_sample_data.tpch_sf100.lineitem
where l_shipdate <= '1998-09-02'
group by 1, 2 order by 1, 2;

alter warehouse perf_wh set warehouse_size = 'SMALL';
select l_returnflag, l_linestatus, sum(l_quantity), sum(l_extendedprice),
       sum(l_extendedprice * (1 - l_discount)), avg(l_discount), count(*)
from snowflake_sample_data.tpch_sf100.lineitem
where l_shipdate <= '1998-09-02'
group by 1, 2 order by 1, 2;

alter warehouse perf_wh set warehouse_size = 'MEDIUM';
select l_returnflag, l_linestatus, sum(l_quantity), sum(l_extendedprice),
       sum(l_extendedprice * (1 - l_discount)), avg(l_discount), count(*)
from snowflake_sample_data.tpch_sf100.lineitem
where l_shipdate <= '1998-09-02'
group by 1, 2 order by 1, 2;

alter warehouse perf_wh set warehouse_size = 'LARGE';
select l_returnflag, l_linestatus, sum(l_quantity), sum(l_extendedprice),
       sum(l_extendedprice * (1 - l_discount)), avg(l_discount), count(*)
from snowflake_sample_data.tpch_sf100.lineitem
where l_shipdate <= '1998-09-02'
group by 1, 2 order by 1, 2;

alter warehouse perf_wh set warehouse_size = 'XSMALL';     -- LUÔN trả về cỡ nhỏ

-- Bảng kết quả: thời gian và credit ước tính (chỉ tính lúc query chạy, chưa tính thời gian rảnh)
with runs as (
    select warehouse_size, total_elapsed_time / 1000 as seconds,
           bytes_spilled_to_local_storage, bytes_spilled_to_remote_storage, start_time
    from table(information_schema.query_history_by_session(result_limit => 100))
    where query_tag = 'perf_lab_s3' and query_type = 'SELECT'
)
select
    warehouse_size,
    seconds,
    case warehouse_size when 'X-Small' then 1 when 'Small' then 2 when 'Medium' then 4 when 'Large' then 8 end
        as credits_per_hour,
    round(seconds / 3600 * credits_per_hour, 4)       as est_credits,
    bytes_spilled_to_local_storage,
    bytes_spilled_to_remote_storage
from runs
order by start_time;

-- Viết kết luận theo lý thuyết 7.3: cấp nào thời gian còn giảm khoảng một nửa? cấp nào chỉ tốn thêm tiền?
-- Lặp lại thí nghiệm với `dbt build` của adventure_works (đổi warehouse trong profile) và ghi vào playbook.
