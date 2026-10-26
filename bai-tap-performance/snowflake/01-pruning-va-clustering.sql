-- =====================================================================================================
-- S1. Dữ liệu được sắp xếp giúp pruning bao nhiêu?
-- Lý thuyết: GD2-ly-thuyet/tuan-7/02-snowflake-query-profile-va-clustering.md
-- Tài liệu:  https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions
-- =====================================================================================================
use warehouse perf_wh;
use schema perf_lab.exp;
alter session set use_cached_result = false;
alter session set query_tag = 'perf_lab_s1';

-- 1. Tạo 2 bản sao 150 triệu dòng (TPC-H SF100). Dùng SMALL cho nhanh, vài phút.
--    Muốn nhẹ hơn: đổi tpch_sf100 → tpch_sf10 (hiệu ứng pruning sẽ kém rõ hơn vì ít micro-partition hơn).
alter warehouse perf_wh set warehouse_size = 'SMALL';

create or replace table orders_random as                 -- cố ý xáo trộn thứ tự dòng
select * from snowflake_sample_data.tpch_sf100.orders
order by random();

create or replace table orders_sorted as                 -- sắp theo cột hay dùng để lọc
select * from snowflake_sample_data.tpch_sf100.orders
order by o_orderdate;

alter warehouse perf_wh set warehouse_size = 'XSMALL';

-- 2. Cùng 1 câu lọc 1 tháng trên 2 bảng. Chạy MỖI câu 2–3 lần.
select count(*), sum(o_totalprice) from orders_random
where o_orderdate >= '1995-03-01' and o_orderdate < '1995-04-01';

select count(*), sum(o_totalprice) from orders_sorted
where o_orderdate >= '1995-03-01' and o_orderdate < '1995-04-01';

-- 3. Bọc cột lọc trong hàm: pruning còn không? (so với câu ở bước 2 trên orders_sorted)
select count(*), sum(o_totalprice) from orders_sorted
where to_char(o_orderdate, 'YYYY-MM') = '1995-03';

-- 4. Đọc số đo của các query trong phiên này (không có độ trễ như ACCOUNT_USAGE)
select
    left(query_text, 70)                         as query_head,
    warehouse_size,
    total_elapsed_time / 1000                    as seconds,
    partitions_scanned,
    partitions_total,
    round(bytes_scanned / power(1024, 2), 1)     as mb_scanned
from table(information_schema.query_history_by_session(result_limit => 100))
where query_tag = 'perf_lab_s1'
  and query_type = 'SELECT'
order by start_time desc;

-- 5. Độ "gọn" của 2 bảng theo o_orderdate: so average_depth, average_overlaps
select system$clustering_information('orders_random', '(o_orderdate)');
select system$clustering_information('orders_sorted', '(o_orderdate)');

-- 6. Mở Query Profile (Snowsight → Monitoring → Query History) của 2 câu ở bước 2:
--    ghi Partitions scanned / Partitions total và node đắt nhất vào nhật ký playbook.
--
-- Câu hỏi để viết kết luận:
--   - orders_sorted quét bao nhiêu % micro-partition? orders_random?
--   - Câu ở bước 3 (to_char) có giữ được pruning không? Rút ra quy tắc viết filter gì?
--   - Với adventure_works (bảng nhỏ), có đáng đặt clustering key không?
--
-- Dọn dẹp khi xong tuần:
-- drop table orders_random; drop table orders_sorted;
