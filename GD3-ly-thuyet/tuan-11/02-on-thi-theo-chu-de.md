# 11.2 Ôn thi theo chủ đề: bảng tra nhanh

> Viết cho dbt 1.10–1.12. Mỗi mục là thứ hay ra đề. Chưa chắc chỗ nào thì mở docs và **chạy thử trên lab** (lab GĐ1 có đủ incremental / snapshot / test, lab GĐ3 có contract / version / freshness).

## 1. Model và materialization

| Materialization | Ghi nhớ |
|---|---|
| `view` | **Mặc định**. Không tốn lưu trữ, chậm khi truy vấn nhiều |
| `table` | `create or replace` mỗi lần chạy |
| `incremental` | Lần đầu (hoặc `--full-refresh`) tạo cả bảng. Các lần sau chỉ xử lý phần `is_incremental()` |
| `ephemeral` | Không tạo object trong warehouse, được chèn thành CTE vào model dùng nó → BI/người dùng không truy vấn được; không có contract; dùng nhiều thì SQL compile ra rất khó debug |
| `materialized_view` | Warehouse tự làm mới (`on_configuration_change: apply / continue / fail`) |
| `snapshot` | SCD2. Từ 1.9 khai báo bằng **YAML** |

**Incremental**

```sql
{{ config(materialized='incremental', unique_key='order_id',
          incremental_strategy='merge', on_schema_change='append_new_columns') }}
select ... from {{ ref('stg_orders') }}
{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

- `is_incremental()` đúng khi: bảng đích đã tồn tại, **và** là bảng (không phải view), **và** không `--full-refresh`, **và** model là incremental.
- Chiến lược: `append`, `merge`, `delete+insert`, `insert_overwrite` (BigQuery/Spark theo partition), `microbatch`. Mỗi adapter hỗ trợ một tập khác nhau. Thiếu `unique_key` thì merge/delete+insert thành gần như append.
- `on_schema_change`: `ignore` (**mặc định**), `fail`, `append_new_columns`, `sync_all_columns`. Không áp dụng lúc full refresh.
- `full_refresh: false` trong config: model **không bao giờ** bị full refresh, kể cả có cờ.

**Microbatch** (1.9+)

```sql
{{ config(materialized='incremental', incremental_strategy='microbatch',
          event_time='order_ts', batch_size='day', begin='2026-01-01', lookback=1) }}
```

- Không viết `is_incremental()`: dbt tự lọc theo `event_time` cho từng lô (`batch_size`: `hour`, `day`, `month`, `year`).
- Model upstream **có khai báo `event_time`** cũng được tự lọc theo lô. Không muốn thì `ref('x').render()`.
- `lookback` (mặc định **1**): xử lý lại N lô trước để đón dữ liệu trễ.
- Backfill: `dbt run -s m --event-time-start "2026-11-01" --event-time-end "2026-11-08"`. Lô lỗi thì `dbt retry` chỉ chạy lại lô đó.
- Mỗi lô chạy độc lập; có thể chạy song song (`concurrent_batches`).

**Snapshot YAML** (1.9+)

```yaml
snapshots:
  - name: customers_snapshot
    relation: source('crm', 'customers')
    config:
      schema: snapshots
      unique_key: customer_id
      strategy: timestamp            # hoặc check (check_cols: [..] | all)
      updated_at: updated_at
      hard_deletes: invalidate       # ignore (mặc định) | invalidate | new_record
      dbt_valid_to_current: "to_date('9999-12-31')"
```

Cột thêm: `dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to` (đổi tên bằng `snapshot_meta_column_names`; `new_record` thêm `dbt_is_deleted`).

**Khác**

- `--empty`: build với `limit 0` trên mọi `ref`/`source` → kiểm tra SQL hợp lệ, schema đúng mà không tốn tiền (CI, unit test cần bảng cha).
- `--sample "3 days"` (1.10+): chỉ đọc dữ liệu gần đây của input có `event_time`, dùng cho dev/CI.
- Python model: `def model(dbt, session):`, `dbt.ref()`, `dbt.source()`, `dbt.config()`, trả về DataFrame. Chỉ Snowflake / BigQuery / Databricks.
- Seeds: CSV nhỏ, tĩnh; `column_types`, `quote_columns`; `dbt seed --full-refresh` khi đổi cột.
- `grants: {select: ['reporter']}` áp sau khi build. `persist_docs: {relation: true, columns: true}` ghi description vào comment của warehouse.
- Doc block: `{% docs order_status %}...{% enddocs %}` trong file `.md`, dùng `description: '{{ doc("order_status") }}'`.
- Thứ tự ưu tiên config: **trong model `config()`** > YAML properties > `dbt_project.yml` (cụ thể hơn thắng).
- Hook: `pre-hook`/`post-hook` (model), `on-run-start`/`on-run-end` (project).

## 2. Governance

- **Contract**: `contract: {enforced: true}` ⇒ mọi cột phải khai báo, có `data_type`. Sai thì lỗi trước khi tạo bảng. Không dùng với `ephemeral`. Incremental cần `on_schema_change` là `append_new_columns` hoặc `fail`.
- **Constraints**: `not_null`, `unique`, `primary_key`, `foreign_key`, `check`. Phần lớn warehouse chỉ **thực thi** `not_null` (xem bảng ở [9.4](../tuan-9/04-data-contracts.md)). Constraint cấp model (nhiều cột) đặt ở `constraints:` của model.
- **Versions**: `latest_version`, `versions: [{v: 1, deprecation_date: ...}]`, `ref('m', v=1)`, `include/exclude` cột, `defined_in`. Tên bảng mặc định `m_v1`.
- **Access / groups**: `private` (cùng group), `protected` (mặc định, cùng project), `public`.
- Breaking change trên model có contract mà không tăng version → lỗi khi so `state:modified`.

## 3. Debugging

| Loại lỗi | Khi nào | Xem ở đâu |
|---|---|---|
| **Compilation error** | Jinja sai, `ref` tới model không tồn tại, YAML sai cấu trúc | Thông báo nêu file + dòng. `dbt parse` / `dbt compile` |
| **Database error** | SQL đã render nhưng warehouse báo lỗi (cột không tồn tại, sai kiểu) | `target/run/.../model.sql` (câu thật đã gửi), `logs/dbt.log` |
| **Dependency error** | Vòng lặp trong DAG, package thiếu | `dbt deps`, `dbt ls` |
| **Runtime / connection** | Sai profile, mất kết nối | `dbt debug` |

- `target/compiled/` = SQL sau Jinja (chưa bọc DDL). `target/run/` = câu thật chạy (có `create table as`...).
- `dbt show -s m --limit 10`, `dbt show --inline "select ..."` để xem dữ liệu.
- `{{ log("x = " ~ x, info=True) }}`, `{% if execute %}` (khi parse, `run_query` trả về None).
- **Behavior flags** trong `dbt_project.yml` → `flags:`: bật/tắt hành vi mới trong giai đoạn chuyển tiếp (vd `require_explicit_package_overrides_for_builtin_materializations`, `require_yaml_configuration_for_mf_time_spines`, `source_freshness_run_project_hooks`...). Có cảnh báo deprecation cho tới khi mặc định đổi.

## 4. Pipeline

- `dbt build` = seed + run + snapshot + test **theo thứ tự DAG**. Test fail (severity error) → **skip** mọi node phía sau. `--fail-fast` (`-x`) dừng ngay khi có lỗi.
- `dbt retry`: đọc `target/run_results.json` lần trước, chạy lại node **lỗi + bị skip**, giữ nguyên lệnh và cờ cũ.
- `dbt clone --state <prod-artifacts>`: tạo bản **clone** (zero-copy clone nếu warehouse hỗ trợ, ngược lại là view) của các node từ môi trường trong state sang schema của target hiện tại. Dùng để dựng nhanh môi trường CI/dev hoặc blue-green. Mặc định không ghi đè bảng đã tồn tại (`--full-refresh` để ghi đè).
- `--threads`, `--target`, `--vars '{"k": "v"}'`, `--select/--exclude/--selector`.

## 5. Test

| Loại | Viết ở đâu | Ghi nhớ |
|---|---|---|
| Generic có sẵn | YAML | `unique`, `not_null`, `accepted_values`, `relationships` |
| Generic tự viết | `tests/generic/` hoặc `macros/` với `{% test ten(model, column_name) %}` | Trả về **các dòng lỗi**; 0 dòng = pass |
| Singular | `tests/*.sql` | Một câu SQL trả dòng lỗi |
| Unit test (1.8+) | YAML `unit_tests:` | Kiểm **logic SQL** với input giả |

```yaml
unit_tests:
  - name: test_is_cancelled_flag
    model: fct_orders
    given:
      - input: ref('stg_shop__orders')
        rows:
          - {order_id: 1, status: cancelled}
          - {order_id: 2, status: completed}
      - input: ref('stg_shop__order_items')
        rows: []
    expect:
      rows:
        - {order_id: 1, is_cancelled: true}
        - {order_id: 2, is_cancelled: false}
```

- Unit test: `format: dict` (mặc định) / `csv` / `sql`; chỉ cần cột liên quan; chạy bằng `dbt test --select test_type:unit` (hoặc trong `dbt build`, chạy **trước** model). Cần bảng cha tồn tại (dùng `--empty` trong CI). Không dùng cho Python model; `overrides` cho macro/var (`is_incremental`).
- Cấu hình: `severity` (`error` **mặc định** / `warn`), `warn_if`, `error_if` (mặc định `!= 0`), `where`, `limit`, `store_failures` (+ `store_failures_as: table|view|ephemeral`), `tags`.
- Tham số generic test từ 1.10: `arguments:`.

## 6. Phụ thuộc bên ngoài

- **Sources**: `{{ source('shop', 'orders') }}`; `freshness` với `warn_after`/`error_after` (`count` + `period`: minute/hour/day), `loaded_at_field` hoặc `loaded_at_query` (1.10+), `filter`. `dbt source freshness` → `target/sources.json`. Không có `loaded_at_field`/query thì dùng metadata của warehouse (nếu adapter hỗ trợ).
- **Exposures**: `type` (dashboard, notebook, analysis, ml, application), `maturity` (high/medium/low), `owner` (bắt buộc có name hoặc email), `depends_on` (ref, source, metric). Chọn: `+exposure:ten`.
- **Packages**: `packages.yml` (hub `package: x/y`, `git:` + `revision:`, `local:`), `dbt deps` sinh **`package-lock.yml`**. Phiên bản theo khoảng `[">=1.3.0", "<2.0.0"]`. Ghi đè macro của package bằng `dispatch`.

## 7. State

```bash
dbt build -s state:modified+ --defer --state prod-artifacts/      # Slim CI
dbt build -s result:error+ --state target/                        # chạy lại lỗi lần trước (giống dbt retry)
dbt build -s source_status:fresher+ --state prod-artifacts/       # chỉ phần có nguồn mới
```

- `state:modified` gồm các phần con: `.body`, `.configs`, `.relation`, `.persisted_descriptions`, `.macros`, `.contract`. `state:new`, `state:old`, `state:unmodified`.
- **`--defer`**: `ref` tới model **không được chọn** và **chưa có** trong môi trường hiện tại sẽ trỏ sang môi trường trong `--state` (prod). `--favor-state`: ưu tiên prod kể cả khi bản dev đã có.
- Artifact: `manifest.json` (toàn bộ project), `run_results.json` (kết quả lần chạy), `sources.json` (freshness), `catalog.json` (`dbt docs generate`), `semantic_manifest.json`.
- Selector: `+m` (tổ tiên), `m+` (con cháu), `2+m`, `@m` (con cháu + tổ tiên của con cháu), `tag:`, `path:`, `config.materialized:`, `test_type:`, `source:`, giao: `-s "tag:a,tag:b"`, `--exclude`, `selectors.yml`.

## Giá trị mặc định nên thuộc

| Thứ | Mặc định |
|---|---|
| materialization | `view` |
| `on_schema_change` | `ignore` |
| test severity | `error`, `error_if: "!=0"`, `warn_if: "!=0"` |
| access | `protected` |
| snapshot `hard_deletes` | `ignore` |
| microbatch `lookback` | `1` |
| `threads` | theo profile (thường 1–4 khi `dbt init`) |
| unit test input `format` | `dict` |
