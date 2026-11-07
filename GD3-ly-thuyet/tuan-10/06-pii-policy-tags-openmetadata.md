# 10.6 PII: phân loại, che dữ liệu, policy tag, data catalog (OpenMetadata)

## Phân loại dữ liệu

| Mức | Ví dụ Mây Shop | Ai được xem |
|---|---|---|
| **Public** | danh mục sản phẩm | mọi người |
| **Internal** | doanh thu, số đơn | nhân viên |
| **Confidential** | giá vốn, biên lợi nhuận | Finance, ban giám đốc |
| **Restricted / PII** | họ tên, email, số điện thoại, ngày sinh, địa chỉ | chỉ người có lý do nghiệp vụ (CSKH, marketing có đồng ý của khách) |

Ở Việt Nam, **Nghị định 13/2023/NĐ-CP** về bảo vệ dữ liệu cá nhân và **Luật Bảo vệ dữ liệu cá nhân** (Quốc hội thông qua năm 2025, hiệu lực từ 01/01/2026) đặt ra nghĩa vụ với dữ liệu cá nhân và dữ liệu cá nhân nhạy cảm. AE không cần làm luật sư, nhưng phải **biết cột nào là PII** và đảm bảo nó không lọt ra nơi không cần.

Gắn nhãn trong dbt:

```yaml
      - name: email
        data_type: varchar
        config:
          meta: {pii: true, pii_kind: email, classification: restricted}
          tags: [pii]
```

Nhãn trong `meta` / `tags` được đọc bởi: CI (cấm model public mới có cột PII chưa duyệt), docs, catalog (OpenMetadata), và macro che dữ liệu.

## Ba tầng che dữ liệu

| Tầng | Cách | Ưu | Nhược |
|---|---|---|---|
| **dbt (lúc build)** | macro `mask_pii()` theo target / var | Chạy trên mọi warehouse, dễ test | Ai build với target có quyền là thấy hết; bảng upstream (staging) vẫn có PII gốc |
| **Warehouse (lúc đọc)** | Snowflake **masking policy**, BigQuery **policy tag** (column-level security) + data masking | Thực thi theo **người đọc**, không phụ thuộc ai chạy dbt | Gắn với từng nền tảng, cần quản trị IAM |
| **BI** | Ẩn cột / row-level security trong Looker, Power BI | Gần người dùng | Ai truy vấn thẳng warehouse thì vượt qua |

Thực tế dùng **kết hợp**: dbt che ở dev/CI (dev không cần PII thật), warehouse che ở prod theo vai trò, và không đưa PII vào model public khi không cần (lý do của `dim_customers` v2).

### Macro trong lab (tầng dbt)

```sql
{% macro mask_pii(column, kind) -%}
  {%- if var('pii_access', false) in [true, 'True', 'true'] -%} {{ column }}
  {%- elif kind == 'email' -%} left({{ column }}, 1) || '***@' || split_part({{ column }}, '@', 2)
  {%- elif kind == 'phone' -%} repeat('*', length({{ column }}) - 3) || right({{ column }}, 3)
  {%- elif kind == 'name'  -%} split_part({{ column }}, ' ', 1) || ' ***'
  {%- elif kind == 'date'  -%} cast(date_trunc('year', {{ column }}) as date)
  {%- endif -%}
{%- endmacro %}
```

`vars: {pii_access: "{{ target.name == 'prod_pii' }}"}`. Biến được render thành **chuỗi** `"True"`/`"False"`, nên macro so sánh với cả hai dạng.

### Snowflake: masking policy

```sql
create masking policy governance.pii_email as (val string) returns string ->
  case when is_role_in_session('PII_READER') then val
       else regexp_replace(val, '^(.).*@', '\\1***@') end;

alter table analytics.marts.dim_customers modify column email
  set masking policy governance.pii_email;
```

Gắn tự động bằng `post-hook` đọc `meta` của cột (tự viết macro lặp qua `model.columns`), hoặc dùng package cộng đồng như `dbt_snow_mask`. Policy gắn vào **cột của bảng**, nên `create or replace table` mỗi lần build cần gắn lại (lý do dùng post-hook).

### BigQuery: policy tag

1. Tạo **taxonomy** + policy tag (`PII/email`) trong Data Catalog / Dataplex, cấp quyền *Fine-Grained Reader* cho nhóm được xem. Tuỳ chọn thêm **data masking rule** (SHA-256, null, default value) cho nhóm "Masked Reader".
2. Khai báo trong dbt:

```yaml
models:
  - name: dim_users
    config:
      persist_docs: {relation: true, columns: true}    # dbt-bigquery gắn policy tag cùng lúc với persist_docs cột
    columns:
      - name: email
        policy_tags: ["projects/<project>/locations/<loc>/taxonomies/<id>/policyTags/<id>"]
```

3. Service account chạy dbt cần quyền gắn policy tag (*Policy Tag Admin* hoặc tương đương) nhưng **không cần** quyền đọc giá trị.

Đây là việc thực hành của `thelook` tuần này.

## Data catalog: OpenMetadata

Catalog trả lời: "có bảng nào chứa email khách?", "ai sở hữu bảng này?", "dashboard này lấy từ đâu?". **OpenMetadata** (mã nguồn mở) đọc artifact của dbt:

| Artifact | OpenMetadata lấy được |
|---|---|
| `manifest.json` | model, mô tả, lineage (model ↔ model ↔ source), owner (từ `meta.owner` / group), tags |
| `catalog.json` | kiểu cột thật trong warehouse (`dbt docs generate`) |
| `run_results.json` | kết quả test → "data quality" trên trang của bảng |

Chạy thử:

1. Docker: tải `docker-compose.yml` của bản release OpenMetadata mới nhất từ GitHub (`open-metadata/OpenMetadata`), `docker compose up -d` (MySQL/Postgres + Elasticsearch/OpenSearch + server + ingestion, cần ~6–8 GB RAM). UI ở cổng 8585.
2. Thêm *Database service* trỏ tới warehouse (Snowflake / BigQuery) và chạy *metadata ingestion*.
3. Thêm *dbt ingestion* với nguồn artifact là đường dẫn file hoặc bucket (S3/GCS) chứa 3 file trên. Đây là lý do CI/CD nên upload artifact sau mỗi lần chạy (GĐ2 tuần 5).
4. Kiểm tra: trang `dim_customers` có lineage tới source, owner, tag PII (map `tags: [pii]` sang classification), kết quả test.

Lựa chọn khác: DataHub, Atlan, Select Star, dbt Catalog (dbt platform), Dataplex (GCP), Snowflake Horizon.

## Câu hỏi tự kiểm tra

1. Vì sao che PII ở tầng dbt **không đủ** cho production?
2. Policy tag của BigQuery và masking policy của Snowflake khác nhau thế nào về nơi gắn và cách cấp quyền?
3. Thiết kế quy trình: một analyst xin xem email khách để làm chiến dịch. Ai duyệt, cấp quyền ở đâu, thu hồi khi nào?
4. OpenMetadata lấy lineage cột (column-level) từ đâu khi chỉ có `manifest.json`?

## Tài liệu

- dbt docs: *meta*, *tags*, *persist_docs*, *BigQuery configs: policy tags*
- Snowflake docs: *Column-level security: masking policies*. Google Cloud: *Restrict access with column-level access control*, *Data masking*
- OpenMetadata docs: *Quickstart (Docker)*, *dbt integration*
