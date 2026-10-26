# 7.5 BigQuery: đo chi phí bằng `INFORMATION_SCHEMA.JOBS`

## Ba cách biết một query tốn bao nhiêu

| Cách | Khi nào | Chính xác |
|---|---|---|
| **Dry run** | **Trước** khi chạy | Đúng với bảng partition; với bảng clustering là **cận trên** (thực tế thường ít hơn). Không tốn tiền |
| Thông báo sau khi chạy (console, `run_results.json` của dbt: `bytes_processed`, `bytes_billed`) | Ngay sau khi chạy | Chính xác cho 1 query |
| **`INFORMATION_SCHEMA.JOBS`** | Phân tích lịch sử, tổng hợp theo ngày/người/model | Chính xác, gom được mọi thứ |

Dry run:

```bash
bq query --use_legacy_sql=false --dry_run 'select user_id from `bigquery-public-data.thelook_ecommerce.events`'
# → Query successfully validated. ... this query will process N bytes of data.
```

## View `INFORMATION_SCHEMA.JOBS`

```sql
select ...
from `region-us`.INFORMATION_SCHEMA.JOBS          -- BẮT BUỘC có region qualifier
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)   -- cột partition: luôn lọc
```

| Điểm cần nhớ | |
|---|---|
| Tên | `INFORMATION_SCHEMA.JOBS` và `JOBS_BY_PROJECT` là **một** (đồng nghĩa). `JOBS_BY_USER`: chỉ job của bạn. Ngoài ra có `JOBS_BY_FOLDER`, `JOBS_BY_ORGANIZATION` |
| Region | Phải có `` `region-us` `` (hoặc region dataset của bạn) |
| Thời gian lưu | 180 ngày |
| Quyền | Xem job của **mọi người** trong project: `bigquery.jobs.listAll` (vd role `roles/bigquery.resourceViewer`). Chỉ job của mình: dùng `JOBS_BY_USER` |
| Partition / cluster | Partition theo `creation_time` (`user_email` là cột clustering) → luôn lọc `creation_time` |

Cột hay dùng:

| Cột | Ý nghĩa |
|---|---|
| `creation_time`, `start_time`, `end_time` | Thời gian |
| `user_email` | Người / service account chạy |
| `job_type` | `QUERY`, `LOAD`, `EXTRACT`, `COPY` |
| `statement_type` | `SELECT`, `INSERT`, `MERGE`, `CREATE_TABLE_AS_SELECT`, `SCRIPT`... |
| `total_bytes_processed` | Byte xử lý |
| `total_bytes_billed` | Byte **tính tiền** (on-demand: đã làm tròn, áp mức tối thiểu) |
| `total_slot_ms` | Tổng slot-mili-giây (quan trọng với giá capacity / editions) |
| `cache_hit` | Trúng cache (miễn phí) |
| `labels` | Mảng `key`/`value` gắn cho job |
| `query` | Câu SQL |
| `referenced_tables`, `destination_table` | Bảng đọc / bảng ghi |
| `error_result` | Lỗi nếu có |
| `parent_job_id` | Job con của một script |

**Tránh đếm trùng**: dbt-bigquery chạy một số thao tác (incremental `merge`, `insert_overwrite`) dưới dạng **script** nhiều câu lệnh. Job cha có `statement_type = 'SCRIPT'` mang tổng của các job con → khi cộng byte, **loại** job `SCRIPT` (như ví dụ trong tài liệu Google).

## Các query cho playbook

### Chi phí theo ngày (on-demand)

```sql
declare price_per_tib float64 default 6.25;   -- giá on-demand US; kiểm tra trang giá hiện hành

select
    date(creation_time)                                         as day,
    count(*)                                                    as jobs,
    round(sum(total_bytes_billed) / pow(1024, 4), 4)            as tib_billed,
    round(sum(total_bytes_billed) / pow(1024, 4) * price_per_tib, 2)  as est_usd   -- chưa trừ 1 TiB miễn phí / tháng
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 30 day)
  and job_type = 'QUERY'
  and statement_type != 'SCRIPT'
group by day
order by day desc;
```

### Top 10 query đắt nhất 7 ngày

```sql
select
    job_id, user_email, statement_type,
    round(total_bytes_billed / pow(1024, 3), 2)     as gib_billed,
    round(total_slot_ms / 1000, 1)                  as slot_seconds,
    left(query, 200)                                as query_head
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
order by total_bytes_billed desc
limit 10;
```

### Theo người dùng / service account

```sql
select user_email, round(sum(total_bytes_billed) / pow(1024, 3), 2) as gib_billed
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 30 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
group by 1 order by 2 desc;
```

Tách được dev (tài khoản của bạn), CI (`sa-dbt-ci`), prod (`sa-dbt-prod`) — một lý do nữa để mỗi môi trường một service account.

### Tỷ lệ cache hit

```sql
select countif(cache_hit) / count(*) as cache_hit_ratio
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day) and job_type = 'QUERY';
```

## Gắn nhãn job theo model dbt

Mặc định label của model (`labels` config) chỉ gắn vào **bảng**, không gắn vào **job**. Muốn biết model nào tốn bao nhiêu, bật **job label** qua `query-comment`:

```sql
-- macros/query_comment.sql
{% macro query_comment(node) %}
    {%- set comment_dict = {} -%}
    {%- do comment_dict.update(
        app='dbt',
        dbt_version=dbt_version,
        target_name=target.name,
    ) -%}
    {%- if node is not none -%}
        {%- do comment_dict.update(dbt_node=node.name, dbt_resource=node.resource_type) -%}
    {%- else -%}
        {%- do comment_dict.update(dbt_node='internal') -%}
    {%- endif -%}
    {% do return(tojson(comment_dict)) %}
{% endmacro %}
```

```yaml
# dbt_project.yml
query-comment:
  comment: "{{ query_comment(node) }}"
  job-label: true
```

dbt-bigquery đọc JSON comment và biến các cặp khoá/giá trị thành **label của job**. Label của BigQuery chỉ cho chữ thường, số, `_`, `-`, tối đa 63 ký tự, nên adapter tự chuẩn hoá (theo mã nguồn dbt-bigquery 1.12): bỏ khoảng trắng hai đầu, chuyển chữ thường, thay mọi ký tự khác bằng `_`, cắt còn 63 ký tự. Ví dụ `model.thelook.fct_events` thành `model_thelook_fct_events`. Ví dụ trên dùng `node.name` cho gọn.

Ngoài ra, **mọi** job do dbt-bigquery chạy đều có sẵn label `dbt_invocation_id` (kể cả khi không bật job-label) → gom được chi phí của **từng lần chạy** `dbt build`.

Chi phí theo model:

```sql
select
    (select value from unnest(labels) where key = 'dbt_node')         as dbt_node,
    (select value from unnest(labels) where key = 'target_name')      as target_name,
    count(*)                                                          as jobs,
    round(sum(total_bytes_billed) / pow(1024, 3), 3)                  as gib_billed,
    round(sum(total_slot_ms) / 1000, 1)                               as slot_seconds
from `region-us`.INFORMATION_SCHEMA.JOBS
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY' and statement_type != 'SCRIPT'
  and exists (select 1 from unnest(labels) where key = 'app' and value = 'dbt')
group by 1, 2
order by gib_billed desc;
```

## Chi phí lưu trữ

```sql
select table_schema, table_name,
       round(active_logical_bytes / pow(1024, 3), 3)     as active_gib,
       round(long_term_logical_bytes / pow(1024, 3), 3)  as long_term_gib
from `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
order by active_logical_bytes desc;
```

Dữ liệu không sửa 90 ngày tự chuyển sang giá **long-term** (rẻ hơn khoảng một nửa). Mỗi lần `create or replace table` (model `table` dựng lại hằng ngày) làm bảng luôn là "active".

## Rào chắn

| Rào chắn | Ở đâu |
|---|---|
| `maximum_bytes_billed` | `profiles.yml` mỗi target (5.3). Query ước tính vượt ngưỡng bị từ chối, không tốn tiền |
| Custom quota "Query usage per day" | Cloud console → IAM & Admin → Quotas, cho project hoặc từng user |
| Budget alert | Cloud Billing → Budgets & alerts (chỉ **báo**, không tự chặn) |
| `require_partition_filter` | Bảng lớn (7.4) |

## Lỗi hay gặp

- Query `INFORMATION_SCHEMA.JOBS` không có region qualifier → lỗi.
- Không lọc `creation_time` → quét cả 180 ngày metadata (cũng tính tiền).
- Cộng cả job `SCRIPT` và job con → chi phí gấp đôi.
- Dùng `total_bytes_processed` thay vì `total_bytes_billed` để tính tiền.
- Quên trừ free tier khi ước tính hoá đơn tháng.
- Chỉ đặt budget alert và nghĩ nó sẽ **chặn** chi tiêu.

## Áp dụng vào project thelook

Bài thực hành: [bai-tap-performance/bigquery](../../bai-tap-performance/bigquery/).

- [ ] Bật `query-comment` job-label, chạy `dbt build` 1 lần, query chi phí theo model
- [ ] Đưa 4 query (theo ngày, top 10, theo người dùng, theo model) vào playbook
- [ ] So `bytes_billed` trong `run_results.json` với `INFORMATION_SCHEMA.JOBS` cho 1 model
- [ ] Đặt `maximum_bytes_billed` cho cả 3 target, ghi lý do chọn ngưỡng

## Câu hỏi tự kiểm tra

1. Dry run chính xác tới đâu với bảng partition? Với bảng clustering?
2. `JOBS`, `JOBS_BY_PROJECT`, `JOBS_BY_USER` khác nhau thế nào? Cần quyền gì?
3. Vì sao phải loại `statement_type = 'SCRIPT'` khi cộng chi phí?
4. `total_bytes_processed` và `total_bytes_billed` khác nhau thế nào?
5. Làm sao biết model dbt nào tốn nhiều tiền nhất?
6. Budget alert có chặn được chi tiêu không? Rào chắn nào chặn được?

## Tài liệu

- JOBS view: https://docs.cloud.google.com/bigquery/docs/information-schema-jobs
- TABLE_STORAGE view: https://docs.cloud.google.com/bigquery/docs/information-schema-table-storage
- Control costs (dry run, maximum bytes billed, custom quotas): https://docs.cloud.google.com/bigquery/docs/best-practices-costs
- dbt — BigQuery job labels (`query-comment`): https://docs.getdbt.com/reference/resource-configs/bigquery-configs
