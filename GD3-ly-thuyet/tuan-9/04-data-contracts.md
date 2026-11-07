# 9.4 Data contracts

## Hai nghĩa của "data contract"

| | **Model contract** (tính năng dbt) | **Data contract** (thoả thuận giữa các đội) |
|---|---|---|
| Giữa ai | Model dbt ↔ người dùng của nó | Đội sở hữu nguồn (app, CRM) ↔ đội dữ liệu |
| Nội dung | Tên cột, kiểu dữ liệu, constraint | Schema + ngữ nghĩa + chất lượng + SLA + quy trình thay đổi + người chịu trách nhiệm |
| Thực thi | dbt kiểm lúc build, sai là lỗi | Một phần bằng công cụ (schema registry, test ở source, CI của đội nguồn), phần lớn bằng quy trình |
| Ví dụ lab | G3: `fct_orders` có `items_amount bigint` | Q5: CRM đổi `phone` → `phone_number` không báo trước |

AE Mid phải làm tốt cái đầu và **đề xuất** được cái sau.

## Model contract trong dbt

```yaml
models:
  - name: fct_orders
    config:
      contract: {enforced: true}
      access: public
    columns:
      - name: order_id
        data_type: bigint
        constraints:
          - type: not_null
          - type: primary_key
      - name: items_amount
        data_type: bigint
      - name: is_cancelled
        data_type: boolean
```

Khi `enforced: true`:

- **Mọi cột** trong SQL phải được khai báo, kèm `data_type`, và ngược lại. Thiếu, thừa hoặc sai kiểu đều làm build lỗi **trước khi** thay bảng cũ (preflight). Người dùng không bao giờ thấy bảng sai giao diện.
- `constraints` được đưa vào DDL `create table`. Mỗi warehouse **thực thi** khác nhau:

| Constraint | Postgres | Snowflake | BigQuery | Databricks |
|---|---|---|---|---|
| `not_null` | ✅ thực thi | ✅ thực thi | ✅ thực thi | ✅ thực thi |
| `primary_key`, `foreign_key` (và `unique` nơi có hỗ trợ) | ✅ | ⚠️ khai báo, **không** thực thi | ⚠️ khai báo, không thực thi (`unique` không hỗ trợ) | ⚠️ khai báo, không thực thi |
| `check` | ✅ | ❌ | ❌ | ✅ |

Constraint không thực thi vẫn có ích (optimizer, công cụ catalog đọc được), nhưng **vẫn cần data test `unique`**.

- Hỗ trợ materialization `table`, `view`, `incremental` (với `on_schema_change: append_new_columns` hoặc `fail`). Không hỗ trợ `ephemeral`.
- Contract kiểm **giao diện**, không kiểm **nội dung**: cột `bigint` toàn số âm vẫn qua contract. Contract + data test là hai lớp khác nhau.

Bài học G3 của lab: `sum(bigint)` trên DuckDB trả `HUGEINT`. Contract bắt được, sửa bằng `cast(... as bigint)` trong model.

## Thay đổi giao diện: không phá vỡ vs phá vỡ

| Không phá vỡ (thêm vào contract là đủ) | Phá vỡ (cần **version mới**, 10.5) |
|---|---|
| Thêm cột mới | Xoá cột, đổi tên cột |
| Nới constraint | Đổi kiểu (`int` → `varchar`) |
| Thêm dòng mới hợp lệ | Đổi grain (1 dòng/đơn → 1 dòng/dòng hàng) |
| | Đổi ngữ nghĩa (revenue bỏ/gồm phí ship) |

dbt phát hiện một phần: với `state:modified`, model có contract bị xoá/đổi kiểu cột mà **không** tăng version sẽ báo lỗi *breaking change* trong CI.

## Data contract với đội nguồn

Mẫu contract cho bảng `crm.customers` (YAML, đặt trong repo chung hoặc repo của đội CRM):

```yaml
dataset: crm.customers
owner: {team: CRM Platform, email: crm-platform@mayshop.vn, slack: "#crm-platform"}
consumers: [data-platform (dbt: stg_crm__customers), marketing-automation]
schema:
  - {name: customer_id, type: integer, required: true, unique: true}
  - {name: email, type: string, required: true, pii: true}
  - {name: phone, type: string, required: false, pii: true}
  - {name: city, type: string, enum_source: "danh mục tỉnh/thành"}
quality:
  - "customer_id không trùng"
  - "email hợp lệ theo regex, ≥ 99%"
sla: {delivery: "file mỗi ngày trước 06:00 GMT+7", freshness_hours: 24}
change_policy:
  breaking_changes: "báo trước ≥ 14 ngày trên #data-contracts, giữ cột cũ song song ≥ 30 ngày"
  non_breaking: "báo trong release notes"
```

Thực thi được tới đâu:

- Phía dữ liệu: `schema_changes_from_baseline` (Elementary) hoặc test trên source, so với contract → cảnh báo ngay khi vi phạm.
- Phía đội nguồn (lý tưởng): CI của họ chạy kiểm tra contract trước khi deploy thay đổi schema.
- Quy trình: kênh trao đổi, người phê duyệt, thời gian báo trước.

Chuẩn mở để tham khảo: **Open Data Contract Standard (ODCS)** của Bitol (Linux Foundation).

## Phòng thủ khi chưa có contract

Lab Q5 là ví dụ "phòng thủ ở staging": đọc cột thật của nguồn bằng `adapter.get_columns_in_relation` và chọn tên đúng. Các mẹo khác:

- Staging luôn `select` cột tường minh (không `select *`), nên nguồn thêm cột không lan xuống.
- `on_schema_change: fail` cho incremental quan trọng: lỗi to còn hơn âm thầm mất cột (GĐ1).
- Test `schema_changes` trên source quan trọng, severity warn, có owner rõ ràng.

## Câu hỏi tự kiểm tra

1. Model contract bắt được loại lỗi nào mà data test không bắt, và ngược lại?
2. Trên Snowflake, `primary_key` trong contract có ngăn trùng khoá không? Vậy bạn làm gì?
3. Viết 3 điều khoản quan trọng nhất của data contract giữa đội app và đội dữ liệu, rút ra từ sự cố Q6 (giá theo nghìn đồng).

## Tài liệu

- dbt docs: *Model contracts*, *Platform constraint support*, *Model versions*
- Bitol: *Open Data Contract Standard*. Andrew Jones, *Driving Data Quality with Data Contracts* (sách)
