# 7.4 BigQuery: partition và cluster

## Vì sao quan trọng hơn ở BigQuery

On-demand BigQuery tính tiền theo **byte đọc**. Bảng 500 GB, query chỉ cần 1 ngày dữ liệu:
- Không partition: đọc (các cột cần của) cả 500 GB → trả tiền 500 GB.
- Partition theo ngày: đọc 1 partition → trả tiền vài trăm MB.

Ở Snowflake pruning chủ yếu giúp **nhanh**. Ở BigQuery on-demand nó giúp **rẻ** trực tiếp.

## Partitioning

Chia bảng thành các phần độc lập theo một cột. Query lọc trên cột đó chỉ đọc các partition liên quan (**partition pruning**).

| Kiểu | Theo | Độ chi tiết |
|---|---|---|
| **Time-unit column** | Cột `DATE`, `TIMESTAMP`, `DATETIME` | `TIMESTAMP`/`DATETIME`: giờ, ngày, tháng, năm. `DATE`: ngày, tháng, năm |
| **Ingestion time** | Thời điểm dữ liệu được nạp (giả cột `_PARTITIONTIME`, `_PARTITIONDATE`) | giờ, ngày, tháng, năm |
| **Integer range** | Cột số nguyên, khoảng `[start, end)` bước `interval` | |

Giới hạn số partition mỗi bảng (hiện tại 10.000 theo ghi chú phát hành 2024, trước đó 4.000; xem trang *Quotas and limits*). Partition theo giờ cho dữ liệu nhiều năm sẽ chạm giới hạn → dùng ngày/tháng.

### Điều kiện để pruning hoạt động

Theo tài liệu BigQuery:

| Prune được ✅ | Không prune ❌ |
|---|---|
| `where created_at >= '2026-03-01' and created_at < '2026-03-08'` (hằng số) | `where created_at >= (select max(...) from t2)` (subquery) |
| Một số hàm có hỗ trợ trên cột partition, với tham số là hằng số | Hàm khác / phép toán trên cột partition |
| | So với **cột khác** của bảng (`where created_at > updated_at`) |
| | `AND` đổi thành `OR` với điều kiện không phải partition |

Lời khuyên: lọc **trực tiếp** cột partition bằng khoảng `>=` và `<`.

### `require_partition_filter`

Bật lên thì mọi query **không có** điều kiện lọc partition bị **từ chối** (lỗi *Cannot query over table ... without a filter that can be used for partition elimination*). Rào chắn tuyệt vời cho bảng lớn. Lưu ý: model dbt khác và **test** đọc bảng đó cũng phải có filter (test dùng config `where`).

### Partition expiration

`partition_expiration_days`: partition tự xoá sau N ngày. Hợp với log, sự kiện thô chỉ cần giữ 90 ngày.

## Clustering

Sắp xếp dữ liệu **bên trong** bảng (hoặc bên trong từng partition) theo tối đa **4 cột**. BigQuery đọc metadata của các block và bỏ qua block không chứa giá trị cần tìm (**block pruning**).

| Đặc điểm | |
|---|---|
| Số cột | Tối đa 4 |
| Thứ tự cột | **Quan trọng**: lọc theo cột thứ nhất hiệu quả nhất; lọc chỉ cột thứ 2 mà không có cột 1 thì kém hơn |
| Re-clustering | **Tự động, miễn phí**, không tốn slot của bạn |
| Ước tính chi phí | Dry run cho con số **trước khi** prune block → con số thật sau khi chạy thường **thấp hơn**. Không có ước tính chính xác trước khi chạy |
| Hợp với | Cột lọc / join / group by thường xuyên, **cardinality cao** (`user_id`, `product_id`, `event_type`) |

## Chọn partition, cluster hay cả hai

| Tình huống | Gợi ý |
|---|---|
| Bảng nhỏ (< vài GB) | Thường không cần gì. Phí tối thiểu 10 MB / bảng vẫn áp dụng |
| Bảng lớn, query luôn lọc theo ngày | Partition theo ngày (+ `require_partition_filter`) |
| Partition sẽ rất nhỏ (Google gợi ý: dưới khoảng 10 GB mỗi partition) | Cân nhắc **chỉ clustering** (nhiều partition nhỏ làm tăng metadata) |
| Lọc theo ngày **và** theo khách / sản phẩm / loại sự kiện | Partition theo ngày + cluster theo các cột còn lại |
| Cần biết **chắc** chi phí trước khi chạy | Partition (dry run ước tính đúng với partition) |
| Cần xoá / ghi đè theo kỳ | Partition (expiration, `insert_overwrite`) |

Google khuyên **thử clustering trước**, rồi thêm partition khi có lý do (ước tính chi phí chắc chắn, quản lý vòng đời dữ liệu, ghi đè theo partition).

## Trong dbt-bigquery

```sql
{{ config(
    materialized = 'table',
    partition_by = {
        'field': 'created_at',
        'data_type': 'timestamp',      -- timestamp | date | datetime | int64
        'granularity': 'day'           -- hour | day | month | year (mặc định day)
    },
    cluster_by = ['user_id', 'product_id'],
    require_partition_filter = true,
    partition_expiration_days = 400,
    labels = {'domain': 'sales', 'layer': 'mart'}
) }}
```

Partition theo số nguyên: `'data_type': 'int64', 'range': {'start': 0, 'end': 100000, 'interval': 1000}`.

### Incremental trên BigQuery

| Chiến lược | Cơ chế | Chi phí |
|---|---|---|
| `merge` (mặc định, cần `unique_key`) | `MERGE` khớp theo khoá | Quét bảng nguồn **và** bảng đích (có thể giới hạn bằng partition + `incremental_predicates`) |
| `insert_overwrite` + **static partitions** | Ghi đè đúng danh sách partition bạn chỉ định (`partitions = [...]`) | **Rẻ và nhanh nhất** theo tài liệu dbt |
| `insert_overwrite` + **dynamic** | dbt tự tính partition bị ảnh hưởng; biến SQL `_dbt_max_partition` = partition lớn nhất đang có ở bảng đích | Thêm 1 bước tính partition |
| `copy_partitions: true` (với insert_overwrite dynamic) | Dùng API copy bảng thay vì insert | Copy **không tốn phí** xử lý |
| `microbatch` | Chia batch theo `event_time` (GĐ1) | |

Mẫu `insert_overwrite` động, tính lại 2 ngày gần nhất (xử lý dữ liệu trễ):

```sql
{{ config(
    materialized = 'incremental',
    incremental_strategy = 'insert_overwrite',
    partition_by = {'field': 'created_date', 'data_type': 'date'},
    cluster_by = ['user_id']
) }}

select ..., date(created_at) as created_date
from {{ ref('stg_thelook__events') }}
{% if is_incremental() %}
where created_at >= timestamp(date_sub(_dbt_max_partition, interval 1 day))   -- _dbt_max_partition là biến SQL của BigQuery
{% endif %}
```

Lưu ý: filter **trên bảng nguồn** cũng cần prune được. Nguồn không partition thì incremental vẫn quét cả nguồn, chỉ tiết kiệm phần ghi.

## Lỗi hay gặp

- Partition theo cột mà query không bao giờ lọc.
- Partition theo giờ cho dữ liệu nhiều năm → chạm giới hạn số partition.
- Lọc bằng subquery hoặc bọc cột partition trong hàm không hỗ trợ → quét cả bảng mà không biết.
- Cluster theo cột cardinality thấp (boolean) đứng đầu.
- Tin vào dry run cho bảng chỉ có clustering (con số là cận trên).
- `require_partition_filter` bật nhưng test dbt không có `where` → test lỗi.
- `merge` trên bảng đích lớn không partition → mỗi lần chạy quét cả bảng đích.

## Áp dụng vào project thelook (tuần 5) và playbook

Bài thực hành chi tiết: [bai-tap-performance/bigquery](../../bai-tap-performance/bigquery/).

- [ ] `fct_order_items`: partition theo ngày `created_at`, cluster `user_id`, `product_id`; so byte quét trước/sau cho 3 query mẫu
- [ ] `fct_events` (bảng lớn nhất): `insert_overwrite` theo ngày, `require_partition_filter`
- [ ] Thí nghiệm: cùng 1 query trên bản không partition / chỉ partition / partition + cluster, ghi byte xử lý (dry run) và byte tính tiền (sau khi chạy)
- [ ] Kết luận vào playbook: cấu hình mặc định cho fact, cho dimension

## Câu hỏi tự kiểm tra

1. Vì sao partition ở BigQuery on-demand tiết kiệm **tiền** trực tiếp?
2. Kể 3 kiểu partition và độ chi tiết cho phép.
3. Những dạng filter nào làm mất partition pruning?
4. `require_partition_filter` làm gì? Ảnh hưởng gì tới test dbt?
5. Clustering khác partitioning thế nào? Vì sao dry run không chính xác với clustering?
6. Khi nào chọn chỉ clustering, không partition?
7. So sánh `merge` và `insert_overwrite` (static, dynamic) về chi phí.

## Tài liệu

- Introduction to partitioned tables: https://docs.cloud.google.com/bigquery/docs/partitioned-tables
- Query partitioned tables (điều kiện pruning): https://docs.cloud.google.com/bigquery/docs/querying-partitioned-tables
- Introduction to clustered tables: https://docs.cloud.google.com/bigquery/docs/clustered-tables
- dbt — BigQuery configurations: https://docs.getdbt.com/reference/resource-configs/bigquery-configs
