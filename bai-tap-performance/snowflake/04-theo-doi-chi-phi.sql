-- =====================================================================================================
-- S4. Credit đi đâu? (ACCOUNT_USAGE có độ trễ: metering tới 3 giờ, attribution tới 8 giờ → chạy file này hôm sau)
-- Tài liệu: https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history
--           https://docs.snowflake.com/en/sql-reference/account-usage/query_attribution_history
-- =====================================================================================================
use role accountadmin;

-- 1. Credit theo warehouse theo ngày (30 ngày)
select warehouse_name, to_date(start_time) as day, round(sum(credits_used), 3) as credits
from snowflake.account_usage.warehouse_metering_history
where start_time >= dateadd('day', -30, current_timestamp())
group by 1, 2
order by 2 desc, 3 desc;

-- 2. Credit gán cho từng query, gom theo query_tag (dbt gắn qua config query_tag)
select coalesce(query_tag, '(không tag)') as query_tag,
       count(*) as queries,
       round(sum(credits_attributed_compute), 4) as credits
from snowflake.account_usage.query_attribution_history
where start_time >= dateadd('day', -7, current_timestamp())
group by 1
order by credits desc;

-- 3. Top 10 query chạy lâu nhất 7 ngày (kèm pruning và spill)
select query_id, user_name, warehouse_name, warehouse_size, query_tag,
       total_elapsed_time / 1000 as seconds,
       partitions_scanned, partitions_total,
       bytes_spilled_to_local_storage, bytes_spilled_to_remote_storage,
       left(query_text, 100) as query_head
from snowflake.account_usage.query_history
where start_time >= dateadd('day', -7, current_timestamp())
  and execution_status = 'SUCCESS'
order by total_elapsed_time desc
limit 10;

-- 4. Gắn query_tag cho dbt (adventure_works), trong dbt_project.yml:
--    models:
--      adventure_works:
--        +query_tag: "dbt_{{ target.name }}"
--        marts:
--          +query_tag: "dbt_{{ target.name }}_marts"
--    Chạy dbt build, hôm sau chạy lại câu 2 để thấy credit theo tag.
