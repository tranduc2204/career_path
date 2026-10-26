# 6.3 automate_dv: dựng Data Vault bằng dbt

> Phiên bản tham chiếu: **automate_dv 0.11.5** (lab đã kiểm chứng trên bản này). Tên cũ của package là *dbtvault*.

## Cài đặt

```yaml
# packages.yml
packages:
  - package: Datavault-UK/automate_dv
    version: 0.11.5
```

```bash
dbt deps
```

Nền tảng hỗ trợ chính thức: Snowflake, BigQuery, SQL Server, Databricks, Postgres. `adventure_works` trên Snowflake dùng được ngay. Lab DuckDB dùng shim (`macros/automate_dv_duckdb.sql` + `dispatch`), cùng kỹ thuật `adapter.dispatch` bạn đã học ở GĐ1.

## Bức tranh tổng thể

```
staging (của bạn) ──▶ automate_dv.stage ──▶ hub / link / nh_link / sat / eff_sat / ma_sat ──▶ pit / bridge ──▶ mart (SQL thường)
                      (view: hash, nguồn,     (incremental, insert-only)                    (pit_incremental,
                       thời điểm nạp)                                                         bridge_incremental)
```

Mọi macro bảng nhận **metadata** (tên cột) và tự sinh SQL insert-only. Bạn không viết logic "so với dòng mới nhất" bằng tay.

## 1. Macro `stage`

```sql
{%- set yaml_metadata -%}
source_model: stg_crm__customers          # ref tới model, hoặc {source_name: table_name}
derived_columns:
  RECORD_SOURCE: "!CRM.CUSTOMERS"           # '!' = hằng chuỗi
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: "CAST(extract_date AS TIMESTAMP)"   # biểu thức SQL
null_columns:                                # thay NULL của business key bằng zero key
  required: [customer_code]                  # → '-1'  (biến null_key_required)
  optional: [referrer_code]                  # → '-2'  (biến null_key_optional); giữ cột gốc *_ORIGINAL
hashed_columns:
  CUSTOMER_HK: customer_code                 # hash key 1 cột
  LINK_ORDER_CUSTOMER_HK: [order_number, customer_code]   # hash key tổ hợp
  CUSTOMER_STATUS_HASHDIFF:
    is_hashdiff: true                        # sắp xếp cột trước khi băm
    columns: [city, loyalty_tier]
{%- endset -%}
{%- set metadata = fromyaml(yaml_metadata) -%}
{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     null_columns=metadata['null_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}
```

Thứ tự xử lý bên trong: cột nguồn → `derived_columns` → `null_columns` → `hashed_columns` → `ranked_columns`. Vì vậy hash được trên cột dẫn xuất (lab: `order_number: receipt_no` rồi `ORDER_HK: order_number`).

## 2. Macro bảng

| Macro | Tham số chính | Ghi chú |
|---|---|---|
| `hub` | `src_pk, src_nk, src_ldts, src_source, source_model` | `source_model` nhận **danh sách** stage. Cột business key phải trùng tên ở mọi stage |
| `link` | `src_pk, src_fk (list), src_ldts, src_source, source_model` | Nhận danh sách stage. Bỏ dòng có FK null |
| `nh_link` | `src_pk, src_fk, src_payload, src_ldts, src_source, source_model` | Non-historized link. **Chỉ nhận 1 `source_model`** → muốn 2 nguồn thì union 2 stage thành 1 view (lab V3). `t_link` là tên cũ, bị đánh dấu deprecated từ 0.11.5 |
| `sat` | `src_pk, src_hashdiff, src_payload, src_eff, src_ldts, src_source, source_model` | Config `apply_source_filter` |
| `eff_sat` | `src_pk, src_dfk (driving), src_sfk (secondary), src_start_date, src_end_date, src_eff, src_ldts, src_source, source_model` | Config `is_auto_end_dating` |
| `ma_sat` | như `sat` + `src_cdk` (child dependent key) | Không có `apply_source_filter` |
| `xts` | `src_pk, src_satellite, src_ldts, src_source, source_model` | Extended tracking satellite: theo dõi hashdiff nào đã vào satellite nào |
| `pit` | `src_pk, as_of_dates_table, satellites, stage_tables_ldts, src_ldts, source_model` | Materialization `pit_incremental` |
| `bridge` | `src_pk, as_of_dates_table, bridge_walk, stage_tables_ldts, src_ldts, source_model` | Materialization `bridge_incremental` |
| `ref_table` | | Bảng tham chiếu (mã → tên) |

Ví dụ:

```sql
-- hub nhiều nguồn
{{ automate_dv.hub(src_pk='CUSTOMER_HK', src_nk='customer_code', src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model=['v_stg_crm__customers', 'v_stg_shop__orders', 'v_stg_pos__sales']) }}

-- satellite, stage chứa nhiều lần nạp
{{ config(apply_source_filter=true) }}
{{ automate_dv.sat(src_pk='CUSTOMER_HK', src_hashdiff='CUSTOMER_STATUS_HASHDIFF',
                   src_payload=['city', 'loyalty_tier'], src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME', src_source='RECORD_SOURCE',
                   source_model='v_stg_crm__customers') }}

-- effectivity satellite tự đóng link cũ
{{ config(is_auto_end_dating=true) }}
{{ automate_dv.eff_sat(src_pk='LINK_PRODUCT_CATEGORY_HK', src_dfk=['PRODUCT_HK'], src_sfk=['CATEGORY_HK'],
                       src_start_date='START_DATE', src_end_date='END_DATE', src_eff='EFFECTIVE_FROM',
                       src_ldts='LOAD_DATETIME', src_source='RECORD_SOURCE',
                       source_model='v_stg_erp__products') }}
```

## 3. Cấu hình model quan trọng

| Config | Dùng với | Tác dụng |
|---|---|---|
| `apply_source_filter: true` | `sat` | Chỉ xét bản ghi stage **mới hơn** dòng mới nhất của key trong satellite. Bắt buộc khi stage chứa **nhiều lần nạp** (bảng nguồn giữ lịch sử, persistent staging) |
| `is_auto_end_dating: true` | `eff_sat` | Khi driving key xuất hiện với secondary key mới, **tự thêm dòng đóng** (END_DATE) cho quan hệ cũ. Mặc định `false`: chờ nguồn gửi end date |

## 4. Biến toàn cục (`vars` trong `dbt_project.yml`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `hash` | `MD5` | `MD5`, `SHA` (SHA-256), `SHA1` |
| `concat_string` | `'\|\|'` | Dấu nối khi băm nhiều cột |
| `null_placeholder_string` | `'^^'` | Thay NULL trong tổ hợp khi băm |
| `hash_content_casing` | `'upper'` | Chuẩn hoá chữ trước khi băm |
| `null_key_required` / `null_key_optional` | `'-1'` / `'-2'` | Zero key cho `null_columns` |
| `enable_ghost_records` | `false` | Thêm ghost record vào satellite |
| `max_datetime` | `9999-12-31 23:59:59.999999` | Ngày "vô cực" cho end date |
| `enable_native_hashes` | `false` | BigQuery/Databricks: lưu hash dạng BYTES thay vì chuỗi hex |

## 5. Materialization

| Materialization | Khi nào |
|---|---|
| `incremental` (của dbt) | Mặc định cho hub/link/sat: mỗi lần chạy chỉ **thêm** dòng mới |
| `vault_insert_by_period` | Nạp lại / backfill lịch sử dài **từng kỳ một** (ngày, tháng) theo một cột thời gian. Config `timestamp_field`, `period`, `start_date`, `stop_date` |
| `vault_insert_by_rank` | Nạp từng "lô" theo cột rank (`ranked_columns` ở stage, config `rank_column`) |
| `pit_incremental`, `bridge_incremental` | Cho PIT và bridge |

## 6. Mẫu hình nạp: stage chứa gì?

Đây là chỗ dễ sai nhất (bẫy V4, V6 của lab):

| Stage chứa | Ví dụ | Satellite đúng khi |
|---|---|---|
| **Trạng thái hiện tại** (1 dòng / key) | bảng nguồn ghi đè (`shop.orders`) | Mặc định đã đúng. Chạy đều đặn thì ghi đủ lịch sử |
| **Một lô mới** (delta) | file của hôm nay | Mặc định đã đúng |
| **Nhiều lô / toàn bộ lịch sử** | bảng nguồn nối thêm (`crm.customers` có mọi file) | `sat`: bật `apply_source_filter`. `ma_sat`, `eff_sat`: cho stage chỉ đọc **lô mới nhất**, hoặc dùng `vault_insert_by_period` / `vault_insert_by_rank` để đi từng lô |

Tại sao: satellite so mỗi bản ghi stage với bản ghi **liền trước trong stage**, riêng bản ghi đầu tiên so với dòng mới nhất của satellite. Stage chứa lịch sử cũ thì bản ghi cũ bị so sai và **chèn lại**.

## 7. Test cho vault

```yaml
models:
  - name: hub_customer
    columns:
      - {name: CUSTOMER_HK, data_tests: [unique, not_null]}
  - name: link_order_customer
    columns:
      - {name: LINK_ORDER_CUSTOMER_HK, data_tests: [unique, not_null]}
      - name: CUSTOMER_HK
        data_tests:
          - relationships:
              arguments: {to: ref('hub_customer'), field: CUSTOMER_HK}
  - name: sat_customer_crm_status
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns: [CUSTOMER_HK, LOAD_DATETIME]
```

Test đối soát số lượng: số business key trong hub = số key distinct ở các stage nguồn.

## 8. Lưu ý khi dùng trên Snowflake (adventure_works)

- Hash key là `BINARY(16)` (MD5). Khi xem bằng mắt: `HEX_ENCODE(CUSTOMER_HK)`.
- Không cần shim, không cần `dispatch`.
- Vault là `incremental`: `--full-refresh` sẽ **xoá lịch sử** chụp từ nguồn ghi đè. Cân nhắc `+full_refresh: false` cho folder `raw_vault` để chặn nhầm tay:
  ```yaml
  models:
    adventure_works:
      raw_vault:
        +full_refresh: false
  ```
- AdventureWorks là dữ liệu tĩnh, nên muốn thấy satellite có lịch sử bạn phải **giả lập thay đổi** (update vài dòng ở nguồn rồi chạy lại), giống cách bạn làm snapshot ở GĐ1.

## Lỗi hay gặp

- Gọi `nh_link` với danh sách nguồn → `The name argument to ref() must be a string, got <class 'list'>`.
- Tên satellite trong `pit(satellites=...)` viết hoa → automate_dv dùng tên đó trong `ref()` → lỗi "node not found". Dùng đúng tên model.
- Stage nhiều lô mà không `apply_source_filter` → satellite chèn lại lịch sử, test unique `(HK, LDTS)` đỏ.
- Eff_sat không bật `is_auto_end_dating` → link cũ không bao giờ đóng.
- Tự viết hàm hash riêng ở chỗ khác → hash không khớp với automate_dv.
- Shim DuckDB: khai báo `duckdb__hash` sẽ **đè** macro `dbt.hash` → `generate_surrogate_key` hỏng (lab đã ghi chú trong file shim).

## Áp dụng vào adventure_works

- [ ] Cài automate_dv, tạo `models/raw_vault/{stage,hubs,links,sats}`, config `+materialized: incremental` và `+full_refresh: false`
- [ ] Stage cho `Sales.Customer`, `Person.Person`, `Production.Product`, `Sales.SalesOrderHeader`, `SalesOrderDetail`, `Person.PersonPhone`
- [ ] 4–5 hub, 3–4 link (1 nh_link cho `SalesOrderDetail`), satellite tách PII của `Person`, 1 multi-active satellite cho số điện thoại
- [ ] Test unique `(HK, LOAD_DATETIME)` cho mọi satellite
- [ ] Giả lập 2 lần thay đổi ở nguồn (đổi `Product.ListPrice`, đổi `Person.LastName`), chạy lại, xem satellite

## Câu hỏi tự kiểm tra

1. Thứ tự xử lý bên trong `automate_dv.stage` là gì? Vì sao quan trọng?
2. `null_columns` required và optional khác nhau thế nào?
3. Khi nào cần `apply_source_filter`? Giải thích cơ chế gây ra dòng trùng.
4. `is_auto_end_dating` làm gì?
5. Khi nào dùng `vault_insert_by_period`?
6. Vì sao nên đặt `+full_refresh: false` cho raw vault?

## Tài liệu

- AutomateDV docs (macro, materialization, best practices): https://automate-dv.readthedocs.io/en/latest/
- AutomateDV trên dbt Hub: https://hub.getdbt.com/Datavault-UK/automate_dv/latest/
- Lab: [V1–V6](../../bai-tap-kimball-data-vault/bai-tap/04-data-vault-raw-vault.md), shim: `bai-tap-kimball-data-vault/lab/macros/automate_dv_duckdb.sql`
