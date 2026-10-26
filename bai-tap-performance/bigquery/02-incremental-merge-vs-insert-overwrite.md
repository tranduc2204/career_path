# B2. Chiến lược incremental nào rẻ hơn cho `fct_events`?

> Chạy trong project thelook (tuần 5), target `dev`. Lý thuyết: [7.4](../../GD2-ly-thuyet/tuan-7/04-bigquery-partition-va-cluster.md), [7.5](../../GD2-ly-thuyet/tuan-7/05-bigquery-do-chi-phi-information-schema.md)

## Mục tiêu

So **byte tính tiền** của lần chạy incremental (không phải lần đầu) giữa 3 cấu hình của cùng một model:

| Phiên bản | Config |
|---|---|
| A | `incremental_strategy='merge'`, `unique_key='event_id'`, **không** partition |
| B | `merge` + `partition_by` ngày + `incremental_predicates` giới hạn vùng quét của bảng đích |
| C | `insert_overwrite` + `partition_by` ngày (dynamic, dùng `_dbt_max_partition`) |

Phiên bản C:

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by={'field': 'event_date', 'data_type': 'date'},
    cluster_by=['event_type', 'customer_id']
) }}
select ..., date(event_created_at) as event_date
from {{ ref('stg_thelook__events') }}
{% if is_incremental() %}
where event_created_at >= timestamp(date_sub(_dbt_max_partition, interval 2 day))
{% endif %}
```

Phiên bản B thêm vào config:

```sql
incremental_predicates = ["DBT_INTERNAL_DEST.event_date >= date_sub(current_date(), interval 3 day)"]
```

(`DBT_INTERNAL_DEST` là alias dbt đặt cho bảng đích trong câu `MERGE`.)

## Cách đo

Với **mỗi** phiên bản:

```bash
dbt build -s fct_events --full-refresh      # lần đầu: dựng bảng
dbt build -s fct_events                      # lần incremental: ĐO LẦN NÀY
python - <<'PY'
import json
r = json.load(open("target/run_results.json"))
for x in r["results"]:
    a = x.get("adapter_response", {})
    print(x["unique_id"], "bytes_processed=", a.get("bytes_processed"), "bytes_billed=", a.get("bytes_billed"), "slot_ms=", a.get("slot_ms"))
PY
```

Đối chiếu với `INFORMATION_SCHEMA.JOBS` (gồm cả các câu phụ dbt chạy: kiểm tra bảng, tính `_dbt_max_partition`...):

```sql
select (select value from unnest(labels) where key = 'dbt_invocation_id') as invocation,
       statement_type,
       round(sum(total_bytes_billed) / pow(1024, 2), 2) as mb_billed,
       count(*) as jobs
from `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
where creation_time >= timestamp_sub(current_timestamp(), interval 2 hour)
  and exists (select 1 from unnest(labels) where key = 'dbt_node' and value = 'fct_events')
group by 1, 2
order by 1, 2;
```

(Nhãn `dbt_node` có nhờ `query_comment` + `job-label: true` của tuần 5. Ở bảng này đừng loại `SCRIPT` vội: nhìn để thấy dbt chạy những loại câu gì; khi **cộng tổng** thì loại `SCRIPT` để không đếm trùng.)

## Ghi vào playbook

| Phiên bản | MB tính tiền (lần incremental) | Số job | Thời gian | Ghi chú |
|---|---|---|---|---|
| A merge không partition | | | | |
| B merge + partition + predicates | | | | |
| C insert_overwrite | | | | |

Kết luận: chọn phiên bản nào làm **mặc định** cho fact sự kiện? Đưa config đó vào mục "Cấu hình mặc định" của playbook và vào `dbt_project.yml`.
