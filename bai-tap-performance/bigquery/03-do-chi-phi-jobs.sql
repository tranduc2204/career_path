-- =====================================================================================================
-- B3. Bộ query đo chi phí cho playbook (copy nguyên vào mục "Đo ở đâu" của playbook)
-- Lý thuyết: GD2-ly-thuyet/tuan-7/05-bigquery-do-chi-phi-information-schema.md
-- Cần quyền xem job của mọi người (bigquery.jobs.listAll). Chỉ xem job của mình: đổi JOBS → JOBS_BY_USER.
-- =====================================================================================================

-- 1. Chi phí theo ngày (on-demand, CHƯA trừ 1 TiB miễn phí / tháng)
declare price_per_tib float64 default 6.25;   -- kiểm tra giá hiện hành trên trang pricing

select
    date(creation_time)                                                 as day,
    count(*)                                                            as jobs,
    round(sum(total_bytes_billed) / pow(1024, 4), 5)                    as tib_billed,
    round(sum(total_bytes_billed) / pow(1024, 4) * price_per_tib, 3)    as est_usd
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 30 day)
  and job_type = 'QUERY'
  and statement_type != 'SCRIPT'
group by day
order by day desc;

-- 2. Theo người dùng / service account (dev vs CI vs prod)
select user_email, count(*) as jobs, round(sum(total_bytes_billed) / pow(1024, 3), 3) as gib_billed
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 30 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
group by 1
order by 3 desc;

-- 3. Theo model dbt và môi trường (cần query_comment + job-label của tuần 5)
select
    (select value from unnest(labels) where key = 'dbt_node')       as dbt_node,
    (select value from unnest(labels) where key = 'target_name')    as target_name,
    count(*)                                                        as jobs,
    round(sum(total_bytes_billed) / pow(1024, 3), 3)                as gib_billed,
    round(sum(total_slot_ms) / 1000, 1)                             as slot_seconds
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
  and exists (select 1 from unnest(labels) where key = 'app' and value = 'dbt')
group by 1, 2
order by gib_billed desc;

-- 4. Top 10 query đắt nhất 7 ngày
select job_id, user_email, statement_type,
       round(total_bytes_billed / pow(1024, 3), 3) as gib_billed,
       round(total_slot_ms / 1000, 1)              as slot_seconds,
       left(regexp_replace(query, r'\s+', ' '), 150) as query_head
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
order by total_bytes_billed desc
limit 10;

-- 5. Chi phí từng lần chạy dbt (mọi job dbt-bigquery đều có label dbt_invocation_id)
select
    (select value from unnest(labels) where key = 'dbt_invocation_id')  as dbt_invocation_id,
    min(creation_time)                                                   as started,
    count(*)                                                             as jobs,
    round(sum(total_bytes_billed) / pow(1024, 3), 3)                     as gib_billed
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
  and exists (select 1 from unnest(labels) where key = 'dbt_invocation_id')
group by 1
order by started desc;

-- 6. Tỷ lệ cache hit
select countif(cache_hit) / count(*) as cache_hit_ratio
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY';

-- 7. Lưu trữ theo bảng
select table_schema, table_name,
       round(active_logical_bytes / pow(1024, 3), 3)     as active_gib,
       round(long_term_logical_bytes / pow(1024, 3), 3)  as long_term_gib
from `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
order by active_logical_bytes desc
limit 20;
