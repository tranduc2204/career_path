# 04 — Governance trong dbt (G1–G6)

> Lý thuyết: [GD3-ly-thuyet/tuan-10/05-governance-dbt.md](../../GD3-ly-thuyet/tuan-10/05-governance-dbt.md) và [06-pii-policy-tags-openmetadata.md](../../GD3-ly-thuyet/tuan-10/06-pii-policy-tags-openmetadata.md). Chấm: `dbt build && python scripts/check.py G`.
> Làm ở ngày nào cũng được, nhưng **sau khi xong M và Q**: governance thay đổi cấu hình model, và bạn phải chứng minh semantic layer + bộ test vẫn xanh (`replay.sh` lần cuối của tuần).

Mây Shop có 3 đội. Đến nay ai cũng `ref` được mọi thứ, nên đội Growth đang đọc thẳng staging của đội Commerce. Tuần này bạn biến project thành một **"nền tảng có giao diện"**: mỗi đội sở hữu model của mình, chỉ phơi ra những model đã cam kết (public + contract), và đổi giao diện thì phải qua version.

## G1 ⭐ — Groups

Tạo `models/_groups.yml` với 3 group, mỗi group có `owner` (name + email):

| Group | Sở hữu |
|---|---|
| `commerce` | `staging/shop`, `staging/erp`, `marts/commerce` |
| `customer` | `staging/crm`, `marts/customer` |
| `growth` | `staging/web`, `staging/mkt`, `marts/growth`, `models/growth/` |

Gán bằng `+group:` theo folder trong `dbt_project.yml`, đừng sửa từng model.

## G2 ⭐⭐ — Access

- Mọi model staging: `access: private` (chỉ model cùng group được ref)
- Mọi model trong `marts/`: `access: public`
- `models/growth/`: `protected` (mặc định)

Bật xong, `dbt parse` sẽ báo lỗi kiểu:

```
Node model.lab.growth_campaign_daily attempted to reference node model.lab.stg_shop__orders,
which is not allowed because the referenced node is private to the 'commerce' group.
```

Đó là mục đích của bài. **Sửa `growth_campaign_daily`** để chỉ dùng model public của Commerce (`fct_orders`) cộng staging của chính Growth. Kết quả của model không được thay đổi: tự viết một truy vấn đối chiếu trước và sau khi sửa.

## G3 ⭐⭐⭐ — Contracts trên model public

Mọi model public: `contract: {enforced: true}` (đặt một lần bằng `+contract` trong `dbt_project.yml`) và **mọi cột có `data_type`**. Thêm `constraints: [{type: not_null}]` cho khoá chính.

Bạn sẽ gặp:

```
This model has an enforced contract that failed.
| column_name   | definition_type | contract_type | mismatch_reason    |
| items_amount  | HUGEINT         | BIGINT        | data type mismatch |
```

Trên DuckDB, `sum()` của `BIGINT` trả về `HUGEINT` (số nguyên 128 bit). Contract bắt được điều mà mắt thường không thấy: người dùng downstream (BI, Python) có thể không đọc được kiểu đó. Sửa ở SQL của model (ép kiểu), đừng sửa contract theo dữ liệu.

**Câu hỏi:** constraint `not_null` trên DuckDB được dbt đưa vào DDL `create table`. Trên Snowflake thì sao? BigQuery thì sao? (lý thuyết 10.5)

## G4 ⭐⭐⭐ — Versions: `dim_customers` v1 → v2

Đội Customer muốn **giảm PII ở giao diện public** và chuẩn hoá tên cột:

| | v1 (hiện tại) | v2 |
|---|---|---|
| Cột | `customer_id, full_name, email, phone, city, segment, birth_date, signup_date` | `customer_id, full_name, email, city, customer_segment, age_band, signup_date` |
| Thay đổi | | bỏ `phone`, `birth_date`; `segment` → `customer_segment`; thêm `age_band` (`18-24`, `25-34`, `35-44`, `45+`, `unknown`) |

Yêu cầu:

- `latest_version: 2`; v1 có `deprecation_date: 2027-01-31`
- Giữ file gốc `dim_customers.sql` làm v1 (`defined_in: dim_customers`), viết thêm `dim_customers_v2.sql`
- Trong DB có cả `dim_customers_v1` lẫn `dim_customers_v2`. Khai báo cột một lần ở cấp model, mỗi version `include: all` + `exclude:` phần không có
- **Semantic layer vẫn chạy:** M2, M7 (`customer__city`) phải còn xanh
- `age_band` tính theo **ngày của lab** (`{{ current_timestamp() }}`), không theo `current_date` thật, để kết quả không đổi theo ngày bạn chạy

> ⚠️ **Đã kiểm chứng trên dbt-core 1.12.6:** đặt khối `semantic_model:` kiểu mới lên một model **có `versions:`** thì dbt **lặng lẽ bỏ qua**: `semantic_manifest.json` không còn semantic model `customers`, `mf validate-configs` không báo gì, nhưng `mf query ... --group-by customer__city` lỗi. Tìm cách khác (gợi ý bên dưới).

<details><summary>Gợi ý</summary>

Spec cũ vẫn chạy song song với spec mới, và nhận `ref` có version:

```yaml
semantic_models:
  - name: customers
    model: ref('dim_customers', v=2)
    entities:
      - {name: customer, type: primary, expr: customer_id}
    dimensions:
      - {name: city, type: categorical}
      - {name: customer_segment, type: categorical}
```
</details>

Sau khi xong: ai còn `ref('dim_customers', v=1)` hoặc `ref('dim_customers')` (trỏ tới latest)? Chạy `dbt ls --select dim_customers.v1+` để biết ai sẽ bị ảnh hưởng khi xoá v1.

## G5 ⭐⭐⭐ — PII: gắn nhãn và che

1. Gắn `config: {meta: {pii: true}}` cho `full_name`, `email`, `phone`, `birth_date` ở cấp cột của `dim_customers`.
2. Viết macro `mask_pii(column, kind)` (`macros/mask_pii.sql`) và dùng trong **cả hai version**:

| kind | Giá trị gốc | Ở target `dev` (mặc định) |
|---|---|---|
| `email` | `an.nguyen12@gmail.com` | `a***@gmail.com` |
| `phone` | `0912345678` | `*******678` |
| `name` | `Nguyễn Văn An` | `Nguyễn ***` |
| `date` | `1994-07-15` | `1994-01-01` |

3. Chỉ khi biến `pii_access` đúng (vd `vars: {pii_access: "{{ target.name == 'prod_pii' }}"}`) thì trả giá trị gốc.

`check.py` đọc dữ liệu thật trong `dim_customers_v1` / `_v2` để kiểm tra mẫu che, và đọc manifest để kiểm tra nhãn.

**Bàn luận (ghi vào ADR governance):** che ở tầng dbt có lỗ hổng gì? (Ai chạy `dbt build --target prod_pii` là thấy hết. Bảng staging vẫn chứa PII gốc.) Ở Snowflake bạn sẽ dùng masking policy, ở BigQuery dùng policy tag. Lý thuyết 10.6 có ví dụ cho cả hai.

## G6 ⭐ — Exposures

`models/exposures.yml` có ít nhất 2 exposure, ví dụ:

- `daily_revenue_dashboard` (dashboard, maturity high, chủ là phòng Tài chính): phụ thuộc `fct_orders`, `fct_order_items`, `fct_refunds`, **`metric('revenue')`**, `metric('net_revenue')`
- `marketing_roas_report` (analysis, maturity medium): phụ thuộc `fct_ad_spend`, `fct_sessions`, `dim_marketing_channels`, `metric('roas')`

Mỗi exposure phải có `owner.email`, `maturity`, `depends_on`. Chỉ được phụ thuộc model **public**. Ít nhất 1 exposure phụ thuộc metric.

Kiểm tra lineage: `dbt docs generate && dbt docs serve`, mở exposure và đi ngược về source.

---

## Áp dụng vào project thật

- `adventure_works`: groups theo domain (sales, production, person), access + contract cho mart, version cho 1 dimension có thay đổi phá vỡ giao diện.
- `thelook` (BigQuery): policy tag cho `users.email` (taxonomy + `policy_tags` trong YAML + `persist_docs`). Đây là việc tuần 12 (dbt Mesh) sẽ cần lại.
- Chạy thử OpenMetadata bằng Docker, ingest `manifest.json` + `catalog.json` + `run_results.json` của `adventure_works`, chụp ảnh lineage và tag PII (hướng dẫn ở lý thuyết 10.6).

## Câu hỏi tự kiểm tra

1. `protected` khác `private` thế nào? Model trong package khác ref được model `protected` của bạn không?
2. Vì sao contract nên đặt ở model public chứ không phải mọi model?
3. Khi nào đổi giao diện cần **version mới**, khi nào chỉ cần thêm cột? Liệt kê 3 thay đổi "phá vỡ" và 3 thay đổi "không phá vỡ".
4. `deprecation_date` qua rồi thì dbt làm gì? Ai phải hành động?
