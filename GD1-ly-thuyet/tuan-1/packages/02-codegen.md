# codegen — học sâu

## Bản chất

codegen là các macro **chỉ in text ra terminal**. Nó không tạo model, không ghi file, không chạy khi `dbt build`. Bạn gọi bằng `dbt run-operation`, codegen query `information_schema` của warehouse, rồi in YAML/SQL để bạn lưu lại.

```
dbt run-operation <macro> --args '<JSON/YAML>'
        │
        ▼
query information_schema  ──▶  render template  ──▶  in ra terminal  ──▶  bạn lưu vào file và CHỈNH SỬA
```

Điều kiện: đã `dbt deps`, và `dbt debug` kết nối warehouse thành công.

## Quy trình chuẩn khi thêm 1 nguồn mới

```
1. generate_source        → _<source>__sources.yml
2. generate_base_model    → stg_<source>__<entity>.sql      (cần bước 1 đã lưu)
3. (chỉnh sửa staging: rename, cast)  →  dbt run -s staging.<source>
4. generate_model_yaml    → _<source>__models.yml            (cần bước 3 đã build)
5. viết description + test vào YAML
```

---

## 1. `generate_source`

```bash
dbt run-operation generate_source --args '{
  "schema_name": "sales",
  "database_name": "adventure_works",
  "generate_columns": true,
  "include_descriptions": true
}'
```

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `schema_name` | (bắt buộc) | Schema chứa bảng raw |
| `database_name` | `target.database` | |
| `table_names` | tất cả | List bảng cụ thể |
| `table_pattern` | `%` | Lọc kiểu `like`, vd `"sales%"` |
| `exclude` | `''` | Pattern bảng loại bỏ |
| `generate_columns` | `false` | Liệt kê cột |
| `include_data_types` | `true` | Ghi `data_type` cho cột |
| `include_descriptions` | `false` | Thêm `description: ""` để điền |
| `name` | = `schema_name` | Tên source trong dbt (`source('<name>', ...)`) |
| `include_database` / `include_schema` | `false` | Ghi rõ `database:` / `schema:` |
| `case_sensitive_databases/schemas/tables/cols` | `false` | Giữ nguyên hoa/thường khi warehouse phân biệt |

Mẹo:
- **Đặt `name` khác `schema_name`** khi tên schema xấu: schema `raw_aw_sales_v2` → `"name": "sales"`, kèm `"include_schema": true` để dbt vẫn biết schema thật.
- Trên Snowflake, identifier mặc định viết HOA. Kết quả có thể ra `SALESORDERHEADER` → thường nên để lowercase (mặc định); chỉ bật `case_sensitive_*` khi bảng thật sự tạo bằng tên có nháy kép.

## 2. `generate_base_model`

```bash
dbt run-operation generate_base_model --args '{
  "source_name": "sales",
  "table_name": "salesorderheader",
  "leading_commas": false,
  "materialized": "view"
}'
```

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `source_name` | (bắt buộc) | Tên source đã khai báo |
| `table_name` | (bắt buộc) | |
| `leading_commas` | `false` | Dấu phẩy đầu dòng (khớp style sqlfluff của bạn) |
| `case_sensitive_cols` | `false` | |
| `materialized` | không có | Thêm `{{ config(materialized=...) }}` ở đầu |

Output:

```sql
with source as (
    select * from {{ source('sales', 'salesorderheader') }}
),

renamed as (
    select
        salesorderid,
        revisionnumber,
        orderdate,
        ...
    from source
)

select * from renamed
```

Đây chỉ là **khung**. Việc của bạn sau đó: đổi tên `salesorderid as order_id`, cast `orderdate` sang `date`, bỏ cột không dùng (`rowguid`), chuẩn hoá chuỗi.

### Sinh hàng loạt

Cách 1: vòng lặp bash.

```bash
for t in salesorderheader salesorderdetail customer salesterritory; do
  dbt --quiet run-operation generate_base_model \
    --args "{\"source_name\": \"sales\", \"table_name\": \"$t\"}" \
    > "models/staging/sales/stg_sales__$t.sql"
done
```

Cách 2: macro `create_base_models` của codegen in ra một chuỗi lệnh shell gọi script `base_model_creation.sh` có sẵn trong package (tạo file cho nhiều bảng). Cách 1 dễ hiểu và dễ kiểm soát hơn.

## 3. `generate_model_yaml`

```bash
dbt run -s staging.sales
dbt run-operation generate_model_yaml --args '{
  "model_names": ["stg_sales__orders", "stg_sales__order_details"],
  "upstream_descriptions": true,
  "include_data_types": true
}'
```

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `model_names` | (bắt buộc) | List model |
| `upstream_descriptions` | `false` | Lấy description của cột cùng tên ở model/source upstream |
| `include_data_types` | `true` | Ghi `data_type` — **cần cho contract** (bài 3.4) |

`upstream_descriptions: true` là lý do lớn nhất để dùng codegen ở marts: viết description cho `customer_id` một lần ở staging, các tầng sau kế thừa.

## 4. `generate_model_import_ctes`

```bash
dbt run-operation generate_model_import_ctes --args '{"model_name": "fct_sales", "leading_commas": false}'
```

Đọc SQL của model, gom mọi `ref()`/`source()` thành các **import CTE** ở đầu file:

```sql
with int_orders__joined_details as (
    select * from {{ ref('int_orders__joined_details') }}
),
dim_products as (
    select * from {{ ref('dim_products') }}
),
...
```

Dùng khi refactor model cũ viết lộn xộn về đúng style dbt.

## 5. `generate_unit_test_template` (bản codegen mới)

Các bản codegen gần đây có macro sinh khung **unit test** (dbt ≥ 1.8) cho một model: liệt kê các input `ref` để bạn điền dữ liệu giả và expected output. Kiểm tra README của version bạn cài; nếu có thì dùng khi làm unit test cho `fct_sales`.

---

## Cách truyền `--args`

`--args` nhận chuỗi **YAML** (JSON là tập con của YAML nên cũng được):

```bash
# JSON
--args '{"schema_name": "sales", "generate_columns": true}'
# YAML gọn
--args 'schema_name: sales'
--args '{schema_name: sales, generate_columns: true, table_names: [customer, store]}'
```

Ngoài cùng dùng nháy đơn `'...'`. Nếu cần biến shell bên trong → ngoài cùng dùng nháy kép và escape `\"` như ví dụ vòng lặp.

## Ghi thẳng ra file

```bash
dbt --quiet run-operation generate_source --args '{schema_name: sales}' > models/staging/sales/_sales__sources.yml
```

`--quiet` tắt log của dbt, chỉ giữ phần codegen in ra. Luôn mở file kiểm tra lại; nếu lẫn log thì xoá tay.

## Lỗi hay gặp

| Triệu chứng | Nguyên nhân |
|---|---|
| `'codegen' is undefined` | Chưa `dbt deps` |
| Output rỗng | Sai schema/database, sai hoa/thường, role không có quyền |
| Lỗi parse `--args` | Lẫn nháy đơn/kép |
| `generate_base_model` báo source not found | Chưa lưu file sources |
| `generate_model_yaml` không có cột | Model chưa được build |
| File có dòng `Running with dbt=...` | Thiếu `--quiet` |

## Tư duy đúng về codegen

- Nó tiết kiệm **gõ phím**, không tiết kiệm **suy nghĩ**. Rename, cast, description, test vẫn là việc của bạn — và là phần reviewer đánh giá.
- Chạy 1 lần lúc tạo, sau đó file thuộc về bạn. **Không** chạy lại đè lên file đã chỉnh sửa.
- Trong portfolio, nhắc ngắn trong README: "sources và staging khởi tạo bằng codegen, sau đó chuẩn hoá theo naming convention".

## Bài tập trên adventure_works

- [ ] `generate_source` cho 3 schema `sales`, `person`, `production` (chỉ bảng cần dùng, có `include_descriptions`)
- [ ] Vòng lặp bash sinh staging cho schema `sales`, rồi chỉnh tay từng file
- [ ] `generate_model_yaml` với `upstream_descriptions: true` cho marts
- [ ] Refactor 1 model bằng `generate_model_import_ctes`
- [ ] Mở `dbt_packages/codegen/macros/generate_source.sql` đọc cách nó query `information_schema`

## Câu hỏi tự kiểm tra

1. codegen có chạy khi `dbt build` không? Vì sao?
2. Vì sao `generate_base_model` phải chạy sau khi đã lưu file source?
3. `upstream_descriptions` giúp gì?
4. Vì sao không nên chạy lại codegen đè lên file staging đã sửa?
