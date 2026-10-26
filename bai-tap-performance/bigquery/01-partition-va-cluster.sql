-- =====================================================================================================
-- B1. Partition và cluster tiết kiệm bao nhiêu byte?
-- Chạy trong BigQuery console, project NON-PROD của tuần 5. Thay <PROJECT> bằng project id của bạn.
-- Lý thuyết: GD2-ly-thuyet/tuan-7/04-bigquery-partition-va-cluster.md
-- Tài liệu:  https://docs.cloud.google.com/bigquery/docs/querying-partitioned-tables
--            https://docs.cloud.google.com/bigquery/docs/clustered-tables
--
-- QUY TẮC: trước khi chạy mỗi câu, nhìn dòng "This query will process ..." (dry run, miễn phí) và ghi lại.
-- =====================================================================================================

-- 0. Dataset thí nghiệm (cùng location US với dữ liệu public)
create schema if not exists `<PROJECT>.perf_lab` options (location = 'US');

-- 1. Kích thước bảng gốc và khoảng ngày (để chọn ngày lọc có dữ liệu ở bước 3)
select table_id, row_count, round(size_bytes / pow(1024, 2), 1) as size_mb
from `bigquery-public-data.thelook_ecommerce.__TABLES__`
where table_id = 'events';

select date(created_at) as d, count(*) as n
from `bigquery-public-data.thelook_ecommerce.events`
group by d order by d desc limit 10;

-- 2. Ba bản sao giống hệt nội dung, khác cách tổ chức (mỗi câu quét bảng gốc 1 lần)
create or replace table `<PROJECT>.perf_lab.events_plain` as
select * from `bigquery-public-data.thelook_ecommerce.events`;

create or replace table `<PROJECT>.perf_lab.events_part`
partition by date(created_at)
as select * from `bigquery-public-data.thelook_ecommerce.events`;

create or replace table `<PROJECT>.perf_lab.events_part_clust`
partition by date(created_at)
cluster by event_type, user_id
as select * from `bigquery-public-data.thelook_ecommerce.events`;

-- 3. Cùng 4 câu trên 3 bảng. Đổi '2026-10-01' thành một ngày CÓ dữ liệu (xem bước 1).
--    Mỗi câu: ghi "will process" (dry run) TRƯỚC khi chạy, rồi chạy.

-- Q1: 1 ngày, 1 cột
select event_type, count(*) from `<PROJECT>.perf_lab.events_plain`
where created_at >= '2026-10-01' and created_at < '2026-10-02' group by 1;
select event_type, count(*) from `<PROJECT>.perf_lab.events_part`
where created_at >= '2026-10-01' and created_at < '2026-10-02' group by 1;
select event_type, count(*) from `<PROJECT>.perf_lab.events_part_clust`
where created_at >= '2026-10-01' and created_at < '2026-10-02' group by 1;

-- Q2: 1 tháng, 1 loại sự kiện (cột cluster đứng đầu)
select count(*) from `<PROJECT>.perf_lab.events_part`
where created_at >= '2026-09-01' and created_at < '2026-10-01' and event_type = 'purchase';
select count(*) from `<PROJECT>.perf_lab.events_part_clust`
where created_at >= '2026-09-01' and created_at < '2026-10-01' and event_type = 'purchase';

-- Q3: filter làm MẤT pruning (so với Q1 trên events_part)
select event_type, count(*) from `<PROJECT>.perf_lab.events_part`
where cast(created_at as string) like '2026-10-01%' group by 1;

-- Q4: select * so với chọn cột (cùng 1 ngày)
select * from `<PROJECT>.perf_lab.events_part`
where created_at >= '2026-10-01' and created_at < '2026-10-02';
select user_id, event_type from `<PROJECT>.perf_lab.events_part`
where created_at >= '2026-10-01' and created_at < '2026-10-02';

-- 4. Số đo thật sau khi chạy: byte xử lý vs byte TÍNH TIỀN (mức tối thiểu 10 MB / bảng)
select
    left(regexp_replace(query, r'\s+', ' '), 110)       as query_head,
    round(total_bytes_processed / pow(1024, 2), 2)      as mb_processed,
    round(total_bytes_billed / pow(1024, 2), 2)         as mb_billed,
    total_slot_ms,
    cache_hit
from `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
where creation_time >= timestamp_sub(current_timestamp(), interval 3 hour)
  and statement_type = 'SELECT'
  and query like '%perf_lab.events%'
order by creation_time;

-- 5. Xem các partition (metadata, rất rẻ)
select partition_id, total_rows, round(total_logical_bytes / pow(1024, 2), 2) as mb
from `<PROJECT>.perf_lab.INFORMATION_SCHEMA.PARTITIONS`
where table_name = 'events_part'
order by partition_id desc
limit 10;

-- Câu hỏi để viết kết luận:
--   - Q1: events_part đọc bao nhiêu % so với events_plain? mb_billed có chạm mức tối thiểu 10 MB không?
--   - Q2: dry run của events_part_clust có khác events_part không? Sau khi chạy thì sao? (dry run là cận trên với cluster)
--   - Q3: vì sao mất pruning? Viết lại để giữ pruning.
--   - Q4: select * tốn gấp bao nhiêu lần?
--   - Partition mỗi ngày nặng bao nhiêu MB? Với Google gợi ý (partition < ~10 GB thì cân nhắc chỉ cluster), bạn chọn gì cho fct_events?
--
-- Dọn dẹp khi xong tuần:
-- drop schema `<PROJECT>.perf_lab` cascade;
