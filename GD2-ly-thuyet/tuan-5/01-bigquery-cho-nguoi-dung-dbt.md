# 5.1 BigQuery cho người dùng dbt

> Bạn đã quen Snowflake (adventure_works) và DuckDB (lab). File này là những gì **khác** khi chuyển sang BigQuery.

## Cấu trúc tài nguyên

```
Organization (tuỳ chọn)
└── Project            ← đơn vị TÍNH TIỀN, phân quyền, quota.        dbt: database (hoặc project)
    └── Dataset        ← có LOCATION cố định, quyền, hạn xoá mặc định. dbt: schema (hoặc dataset)
        └── Table / View / Materialized view / Model / Routine
```

| Snowflake | BigQuery |
|---|---|
| Account | (Organization) |
| Database | **Project** |
| Schema | **Dataset** |
| Warehouse (compute riêng, bật/tắt) | Không có: compute **serverless**, dùng chung (slot) |
| Role | IAM role (cấp ở project, dataset, bảng) |

Tên đầy đủ: `` `project-id.dataset.table` `` (dấu backtick vì project id có dấu gạch ngang).

### Location

Mỗi dataset có **location** cố định lúc tạo: multi-region (`US`, `EU`) hoặc region (`asia-southeast1`...). **Một query không đọc được dữ liệu ở 2 location khác nhau.** Dataset public `thelook_ecommerce` ở `US` → mọi dataset của project thelook phải ở `US`.

## Tính tiền và các chế độ tài khoản

| | Sandbox | Free trial / có billing |
|---|---|---|
| Cần thẻ | Không | Có (free trial cho tài khoản mới: 300 USD dùng trong 90 ngày) |
| Query | 1 TiB / tháng miễn phí | 1 TiB / tháng miễn phí, sau đó theo giá on-demand |
| Lưu trữ | 10 GiB (giới hạn trọn đời) | 10 GiB / tháng miễn phí, sau đó theo giá |
| Bảng, partition | **Tự hết hạn sau 60 ngày** | Không |
| **DML** (`INSERT`, `UPDATE`, `DELETE`, `MERGE`) | ❌ **Không hỗ trợ** | ✅ |
| Streaming, Data Transfer Service | ❌ | ✅ |

Hệ quả cho dbt: **sandbox không chạy được model incremental** (dbt-bigquery dùng `MERGE` hoặc insert), **snapshot** (`MERGE`), seed lớn... Project tuần 5 cần **bật billing** (dùng free trial). Ngay khi bật: tạo **budget alert** trong Cloud Billing (ví dụ 5 USD) và đặt `maximum_bytes_billed` (bên dưới).

Giá on-demand (US multi-region): 6,25 USD / TiB byte quét, tối thiểu 10 MB / bảng được tham chiếu mỗi query, làm tròn lên MB. Query trúng cache và dry run không tính tiền. Chi tiết đo chi phí: tuần 7 ([7.5](../tuan-7/05-bigquery-do-chi-phi-information-schema.md)).

## Kết nối dbt với BigQuery

```bash
pip install dbt-bigquery          # hoặc thêm vào pyproject / requirements.txt
gcloud auth application-default login     # đăng nhập ADC cho máy dev
```

```yaml
# profiles.yml (target dev)
thelook:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth                     # ADC của gcloud
      project: thelook-ae-dev           # hoặc "{{ env_var('GCP_PROJECT_NONPROD') }}"
      dataset: dbt_duc
      location: US
      threads: 8
      priority: interactive             # interactive (mặc định) | batch
      job_execution_timeout_seconds: 300
      job_retries: 1
      maximum_bytes_billed: 5000000000  # query nào ước tính vượt 5 GB → bị từ chối, không tốn tiền
```

| `method` | Dùng khi |
|---|---|
| `oauth` | Máy dev (gcloud ADC) **và** GitHub Actions dùng Workload Identity Federation (5.4) |
| `service-account` + `keyfile` | Có file key JSON. Tránh nếu được: key sống lâu, dễ lộ |
| `service-account-json` | Key nằm thẳng trong profile (`keyfile_json`, đọc từ biến môi trường) |
| `oauth-secrets` | Dùng sẵn token / refresh token (ít gặp) |
| `external-oauth-wif` | Workload Identity Federation với nhà cung cấp danh tính ngoài (thường dùng với dbt platform). Trên GitHub Actions, cách đơn giản hơn vẫn là `oauth` + action `google-github-actions/auth` |

Tuỳ chọn hữu ích khác: `impersonate_service_account` (dev chạy với quyền của service account, không cần key), `execution_project` (chạy job và tính tiền ở project khác với project chứa dữ liệu).

Kiểm tra: `dbt debug`.

## SQL BigQuery: khác gì Snowflake / DuckDB

| Chủ đề | BigQuery |
|---|---|
| Kiểu dữ liệu | `INT64`, `FLOAT64`, `NUMERIC`, `BIGNUMERIC`, `STRING`, `BYTES`, `BOOL`, `DATE`, `DATETIME` (không múi giờ), `TIMESTAMP` (UTC), `JSON`, `ARRAY`, `STRUCT` |
| Ép kiểu an toàn | `SAFE_CAST(x AS INT64)` → null thay vì lỗi. `SAFE_DIVIDE(a, b)` |
| Ngày giờ | `DATE_TRUNC(d, MONTH)`, `DATE_DIFF(d1, d2, DAY)`, `TIMESTAMP_SUB(ts, INTERVAL 1 DAY)`, `FORMAT_DATE('%Y%m%d', d)` — **thứ tự tham số khác Snowflake** |
| Dãy ngày | `UNNEST(GENERATE_DATE_ARRAY('2026-01-01', '2026-12-31'))` |
| Lọc window | `QUALIFY` có hỗ trợ (cần window function trong `QUALIFY` hoặc `SELECT`) |
| Mảng | `UNNEST(arr)` để "duỗi" mảng thành dòng; `ARRAY_AGG` để gom |
| Chọn cột | `SELECT * EXCEPT(col1, col2)`, `SELECT * REPLACE(... AS col)` |
| Đếm có điều kiện | `COUNTIF(cond)` |
| Định danh | Tên bảng, dataset **phân biệt hoa thường**; tên cột thì không |

Để SQL chạy được trên nhiều warehouse (vd dùng chung macro giữa adventure_works và thelook), dùng **cross-database macro** của dbt: `{{ dbt.date_trunc('month', 'created_at') }}`, `{{ dbt.datediff('a', 'b', 'day') }}`, `{{ dbt.dateadd('day', -1, 'col') }}`, `{{ dbt.safe_cast('col', api.Column.translate_type('integer')) }}`.

## Config riêng của dbt-bigquery (biết trước, học sâu ở tuần 7)

| Config | Tác dụng |
|---|---|
| `partition_by`, `cluster_by` | Partition và cluster bảng (7.4) |
| `require_partition_filter` | Chặn query không lọc partition |
| `partition_expiration_days`, `hours_to_expiration` | Tự xoá partition / bảng |
| `labels` | Gắn nhãn cho bảng (và cho job nếu bật `query-comment` job-label, 7.5) |
| `incremental_strategy` | `merge` (mặc định), `insert_overwrite`, `microbatch` |
| `persist_docs` | Đẩy description của model/cột vào BigQuery (thấy được trong console) |
| `grant_access_to` | Authorized view: cho view đọc dataset khác mà người dùng không cần quyền trên dataset đó |

## Lỗi hay gặp

- Dùng sandbox rồi không hiểu vì sao incremental báo lỗi DML.
- Dataset tạo sai location.
- Viết `DATE_DIFF` theo thứ tự tham số của Snowflake (`DATEDIFF(day, a, b)`) → sai dấu.
- `TIMESTAMP` vs `DATETIME`: so sánh lẫn lộn gây lỗi kiểu hoặc lệch múi giờ (TIMESTAMP luôn là UTC).
- Không đặt `maximum_bytes_billed` khi dev.
- Commit file key JSON.

## Áp dụng: khởi động project thelook

Hướng dẫn từng bước: [bai-tap-bigquery-thelook](../../bai-tap-bigquery-thelook/README.md).

- [ ] Tạo tài khoản GCP, bật billing (free trial), tạo budget alert
- [ ] Cài `gcloud`, `gcloud auth application-default login`
- [ ] Repo `thelook` mới, `dbt init`, `profiles.yml` target dev có `maximum_bytes_billed`, `dbt debug` xanh
- [ ] Query thử thelook trên console, ghi kích thước các bảng vào README

## Câu hỏi tự kiểm tra

1. Project, dataset của BigQuery tương ứng với gì trong dbt và Snowflake?
2. Vì sao dataset phải cùng location với dữ liệu nguồn?
3. Sandbox thiếu gì khiến dbt incremental không chạy?
4. `maximum_bytes_billed` hoạt động thế nào?
5. Kể 4 khác biệt cú pháp SQL giữa BigQuery và Snowflake.
6. Khi nào dùng `method: oauth`, khi nào `service-account`?

## Tài liệu

- dbt — BigQuery setup: https://docs.getdbt.com/docs/core/connect-data-platform/bigquery-setup
- dbt — BigQuery configurations: https://docs.getdbt.com/reference/resource-configs/bigquery-configs
- BigQuery sandbox: https://docs.cloud.google.com/bigquery/docs/sandbox
- BigQuery pricing: https://cloud.google.com/bigquery/pricing
- GoogleSQL reference: https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax
