-- =====================================================================================================
-- S2. Nhận ra exploding join và spilling trong Query Profile
-- Tài liệu: https://docs.snowflake.com/en/user-guide/ui-snowsight-activity
-- =====================================================================================================
use warehouse perf_wh;
use schema perf_lab.exp;
alter session set use_cached_result = false;
alter session set query_tag = 'perf_lab_s2';

-- ---------------------------------------------------------------- S2a. Exploding join
-- Đúng: nối dòng hàng với đơn theo khoá đơn.
select count(*)
from (select * from snowflake_sample_data.tpch_sf1.orders limit 100000) o
join snowflake_sample_data.tpch_sf1.lineitem l
  on l.l_orderkey = o.o_orderkey;

-- Sai: nối theo NGÀY (không phải khoá) → mỗi dòng bên trái khớp hàng nghìn dòng bên phải.
-- Dữ liệu đã được giới hạn bằng LIMIT để câu không chạy quá lâu.
select count(*)
from (select * from snowflake_sample_data.tpch_sf1.orders limit 100000) o
join (select * from snowflake_sample_data.tpch_sf1.lineitem limit 100000) l
  on l.l_shipdate = o.o_orderdate;

-- Mở Query Profile của câu thứ 2: node Join nhận vào bao nhiêu dòng, xuất ra bao nhiêu dòng?
-- Đây là dấu hiệu "exploding join" mà tài liệu Snowflake mô tả.

-- ---------------------------------------------------------------- S2b. Spilling
-- Window function trên 60 triệu dòng với warehouse nhỏ nhất. Có thể spill ra đĩa.
alter warehouse perf_wh set warehouse_size = 'XSMALL';

select count(*) from (
    select l_orderkey, l_linenumber,
           row_number() over (partition by l_suppkey order by l_extendedprice desc) as rn
    from snowflake_sample_data.tpch_sf10.lineitem
    qualify rn <= 3
);

-- Đọc số đo. Nếu không thấy spill: đổi tpch_sf10 → tpch_sf100 (600 triệu dòng, chạy lâu hơn vài phút).
select
    left(query_text, 70)                                        as query_head,
    warehouse_size,
    total_elapsed_time / 1000                                   as seconds,
    round(bytes_spilled_to_local_storage / power(1024, 3), 2)   as gb_spilled_local,
    round(bytes_spilled_to_remote_storage / power(1024, 3), 2)  as gb_spilled_remote
from table(information_schema.query_history_by_session(result_limit => 100))
where query_tag = 'perf_lab_s2'
  and query_type = 'SELECT'
order by start_time desc;

-- Thử lại câu S2b với warehouse_size = 'MEDIUM': spill còn không? Thời gian, credit (credit/giờ × giờ) đổi thế nào?
-- Ghi cả 2 lần vào nhật ký playbook. Nhớ trả warehouse về XSMALL:
-- alter warehouse perf_wh set warehouse_size = 'XSMALL';
