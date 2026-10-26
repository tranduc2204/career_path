# 04 — Data Vault: raw vault với automate_dv (V1–V6)

> Lý thuyết: [6.1 tổng quan](../../GD2-ly-thuyet/tuan-6/01-data-vault-tong-quan.md) · [6.2 hub, link, satellite](../../GD2-ly-thuyet/tuan-6/02-hub-link-satellite.md) · [6.3 automate_dv](../../GD2-ly-thuyet/tuan-6/03-automate-dv.md)

**Tình huống:** công ty sắp mua thêm một sàn thương mại điện tử và một chuỗi cửa hàng nữa, mỗi bên một hệ thống riêng. Kiến trúc sư dữ liệu muốn thử một tầng tích hợp chịu được việc nguồn thêm/bớt liên tục, giữ được toàn bộ lịch sử để kiểm toán. Bạn dựng lại dữ liệu Mây Shop bằng **Data Vault 2.0**, dùng package `automate_dv` (đã cài qua `dbt deps`).

## Trước khi làm

- `automate_dv` chưa hỗ trợ DuckDB. Lab đã có sẵn **shim** ở `macros/automate_dv_duckdb.sql` + khối `dispatch` trong `dbt_project.yml` (đọc để hiểu, đừng sửa). Trên Snowflake (`adventure_works`) không cần shim.
- Folder `models/raw_vault/` mặc định là `incremental` (vault **chỉ thêm**), riêng `models/raw_vault/stage/` là `view`.
- Vault **không dựng lại được** từ nguồn ghi đè. Mỗi lần tạo hoặc sửa model vault: `./scripts/replay.sh`.
- Hash key trên DuckDB là chuỗi hex IN HOA 32 ký tự. Trên Snowflake là `BINARY(16)`.

Cấu trúc nên dùng:

```
models/raw_vault/
├── stage/   v_stg_*.sql          (view: hash key, hashdiff, nguồn, thời điểm nạp)
├── hubs/    hub_*.sql
├── links/   link_*.sql, nh_link_*.sql
└── sats/    sat_*.sql, eff_sat_*.sql, ma_sat_*.sql
```

Quy ước chung (check.py dựa vào):

| Cột kỹ thuật | Giá trị |
|---|---|
| Hash key | `<THỰC THỂ>_HK`, vd `CUSTOMER_HK`, `LINK_ORDER_CUSTOMER_HK` |
| `RECORD_SOURCE` | `'<HỆ THỐNG>.<BẢNG>'` in hoa, vd `CRM.CUSTOMERS`, `SHOP.ORDERS`, `POS.SALES`, `ERP.PRODUCTS` |
| `LOAD_DATETIME` | `_loaded_at` của dòng nguồn |
| `EFFECTIVE_FROM` | thời điểm nghiệp vụ: CRM = `extract_date`, shop = `updated_at`, POS = `sale_ts`, ERP = `_loaded_at` |

---

## V1 ⭐⭐ Stage: hash key, hashdiff, nguồn bản ghi

**Mẫu đầy đủ** `models/raw_vault/stage/v_stg_crm__customers.sql`:

```sql
{%- set yaml_metadata -%}
source_model: stg_crm__customers
derived_columns:
  RECORD_SOURCE: "!CRM.CUSTOMERS"              # dấu ! = hằng số chuỗi
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: "CAST(extract_date AS TIMESTAMP)"
hashed_columns:
  CUSTOMER_HK: customer_code
  CUSTOMER_PROFILE_HASHDIFF:
    is_hashdiff: true
    columns: [full_name, email]
  CUSTOMER_STATUS_HASHDIFF:
    is_hashdiff: true
    columns: [city, loyalty_tier]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}
```

**Yêu cầu:** viết thêm các stage sau (chọn hashdiff phù hợp với satellite bạn định làm ở V4):

| Stage | `source_model` | Hash key cần có | Ghi chú |
|---|---|---|---|
| `v_stg_shop__orders` | `stg_shop__orders` | `ORDER_HK`, `CUSTOMER_HK`, `LINK_ORDER_CUSTOMER_HK` (order_number, customer_code), `ORDER_SHOP_HASHDIFF` | |
| `v_stg_shop__order_lines` | `stg_shop__order_lines` | `ORDER_HK`, `PRODUCT_HK`, `ORDER_LINE_HK` (order_number, sku, line_no) | |
| `v_stg_shop__order_vouchers` | `stg_shop__order_vouchers` | `ORDER_HK`, `VOUCHER_HK`, `ORDER_VOUCHER_HK` | |
| `v_stg_pos__sales` | `stg_pos__sales` | `ORDER_HK`, `CUSTOMER_HK`, `PRODUCT_HK`, `LINK_ORDER_CUSTOMER_HK`, `ORDER_LINE_HK`, `ORDER_POS_HASHDIFF` | xem 2 ghi chú dưới |
| `v_stg_erp__products` | `stg_erp__products` | `PRODUCT_HK`, `CATEGORY_HK`, `LINK_PRODUCT_CATEGORY_HK`, `PRODUCT_HASHDIFF` | cần thêm `START_DATE`, `END_DATE` cho V5 |
| `v_stg_erp__categories` | `stg_erp__categories` | `CATEGORY_HK`, `CATEGORY_HASHDIFF` | |

Hai ghi chú cho POS:
1. **Hub đơn hàng gom 2 nguồn** nên cột business key phải **trùng tên**. POS gọi là `receipt_no` → thêm derived column `order_number: receipt_no` rồi hash `ORDER_HK: order_number`.
2. **Khách vãng lai** (`customer_code` null) → không được để `CUSTOMER_HK` null. Dùng `null_columns` để thay bằng *zero key*:
   ```yaml
   null_columns:
     optional:          # optional → '-2', required → '-1'; giá trị gốc giữ ở customer_code_ORIGINAL
       - customer_code
   ```
   và truyền `null_columns=metadata['null_columns']` vào `automate_dv.stage`.

**Kiểm tra:** `dbt build -s raw_vault.stage` → `check.py V1`. Xem thử:

```bash
dbt show --inline "select customer_code, CUSTOMER_HK, CUSTOMER_STATUS_HASHDIFF, RECORD_SOURCE, LOAD_DATETIME from {{ ref('v_stg_crm__customers') }} where customer_code = 'C003'"
dbt show --inline "select receipt_no, order_number, customer_code, customer_code_ORIGINAL, CUSTOMER_HK from {{ ref('v_stg_pos__sales') }}"
```

**Câu hỏi suy ngẫm**
1. Vì sao hash key được tính **một lần** ở stage chứ không ở hub/link?
2. `' c003'` và `'C003'` có cùng hash không? Ai lo việc đó: staging của bạn hay automate_dv?
3. Hashdiff dùng để làm gì? Vì sao cột của hashdiff được **sắp xếp** trước khi băm?

---

## V2 ⭐⭐ Hub: một business key, một dòng, mọi nguồn

**Yêu cầu:** 5 hub trong `models/raw_vault/hubs/`.

| Hub | `src_pk` | `src_nk` | `source_model` (danh sách) |
|---|---|---|---|
| `hub_customer` | `CUSTOMER_HK` | `customer_code` | CRM, shop orders, POS |
| `hub_order` | `ORDER_HK` | `order_number` | shop orders, POS |
| `hub_product` | `PRODUCT_HK` | `sku` | ERP products, shop order lines, POS |
| `hub_category` | `CATEGORY_HK` | `category_code` | ERP categories, ERP products |
| `hub_voucher` | `VOUCHER_HK` | `voucher_code` | shop order vouchers |

```sql
{{ automate_dv.hub(src_pk='CUSTOMER_HK', src_nk='customer_code',
                   src_ldts='LOAD_DATETIME', src_source='RECORD_SOURCE',
                   source_model=['v_stg_crm__customers', 'v_stg_shop__orders', 'v_stg_pos__sales']) }}
```

**Kiểm tra:** `./scripts/replay.sh` → `check.py V2`.

```bash
dbt show --inline "select customer_code, LOAD_DATETIME, RECORD_SOURCE from {{ ref('hub_customer') }} order by 1"
```

Kỳ vọng: C013 lần đầu thấy ở `SHOP.ORDERS` (ngày 2) dù sau đó CRM mới có. C014 chỉ có từ `POS.SALES`. Có thêm 1 dòng `-2` (zero key của khách vãng lai).

**Câu hỏi suy ngẫm**
1. Hub không có cột thuộc tính nào. Vì sao thiết kế như vậy lại giúp thêm nguồn mới dễ dàng?
2. So với K6 (inferred member): trong vault, "khách tới trước CRM" có còn là vấn đề không?
3. Nếu sàn TMĐT mới mua về dùng mã khách `TIKI_8812` thay vì `C013` cho cùng một người, hub xử lý thế nào? (gợi ý: same-as link, xem lý thuyết 6.2)

---

## V3 ⭐⭐⭐ Link và non-historized link

**Yêu cầu:** trong `models/raw_vault/links/`.

| Model | Macro | `src_pk` | `src_fk` | Payload | Nguồn |
|---|---|---|---|---|---|
| `link_order_customer` | `link` | `LINK_ORDER_CUSTOMER_HK` | `ORDER_HK, CUSTOMER_HK` | — | shop orders, POS |
| `link_product_category` | `link` | `LINK_PRODUCT_CATEGORY_HK` | `PRODUCT_HK, CATEGORY_HK` | — | ERP products |
| `nh_link_order_line` | `nh_link` | `ORDER_LINE_HK` | `ORDER_HK, PRODUCT_HK` | `line_no, quantity, unit_price` | dòng đơn shop + POS |
| `nh_link_order_voucher` | `nh_link` | `ORDER_VOUCHER_HK` | `ORDER_HK, VOUCHER_HK` | `discount_amount` | shop order vouchers |

Bạn sẽ gặp lỗi khi đưa danh sách 2 nguồn vào `nh_link`: `The name argument to ref() must be a string, got <class 'list'>`. **`automate_dv.nh_link` chỉ nhận 1 `source_model`.** Cách xử lý: tạo `models/raw_vault/stage/v_stg_union__order_lines.sql` gộp 2 stage (`union all`, chọn đúng các cột cần), rồi trỏ `nh_link_order_line` vào đó.

**Kiểm tra:** `./scripts/replay.sh` → `check.py V3`. Sau ngày 3, `link_product_category` có **11 dòng** cho 10 sản phẩm: cặp cũ SKU07–DT_PK vẫn còn.

**Câu hỏi suy ngẫm**
1. Link luôn là quan hệ nhiều-nhiều, kể cả khi nghiệp vụ là một-nhiều (1 đơn có 1 khách). Lợi gì?
2. Khi nào dùng link thường + satellite, khi nào dùng non-historized link? (gợi ý: dòng đơn có bao giờ sửa không?)
3. Sau ngày 3, nhìn `link_product_category` có biết SKU07 **đang** thuộc danh mục nào không? (→ V5)

---

## V4 ⭐⭐⭐⭐ Satellite và cái bẫy của stage nhiều lần nạp

**Yêu cầu:** trong `models/raw_vault/sats/`. Tách satellite của khách theo **tốc độ thay đổi và độ nhạy**:

| Satellite | `src_pk` | `src_hashdiff` | `src_payload` | `source_model` |
|---|---|---|---|---|
| `sat_customer_crm_profile` | `CUSTOMER_HK` | `CUSTOMER_PROFILE_HASHDIFF` | `full_name, email` | `v_stg_crm__customers` |
| `sat_customer_crm_status` | `CUSTOMER_HK` | `CUSTOMER_STATUS_HASHDIFF` | `city, loyalty_tier` | `v_stg_crm__customers` |
| `sat_order_shop` | `ORDER_HK` | `ORDER_SHOP_HASHDIFF` | các cột đầu đơn, **phải có** `order_status, paid_at, cancelled_at` | `v_stg_shop__orders` |
| `sat_order_pos` | `ORDER_HK` | `ORDER_POS_HASHDIFF` | `store_code, payment_method, sale_ts` | `v_stg_pos__sales` |
| `sat_product_erp` | `PRODUCT_HK` | `PRODUCT_HASHDIFF` | `product_name, brand, list_price` | `v_stg_erp__products` |
| `sat_category_erp` | `CATEGORY_HK` | `CATEGORY_HASHDIFF` | `category_name, parent_code` | `v_stg_erp__categories` |

Mẫu:

```sql
{{ automate_dv.sat(src_pk='CUSTOMER_HK', src_hashdiff='CUSTOMER_STATUS_HASHDIFF',
                   src_payload=['city', 'loyalty_tier'], src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME', src_source='RECORD_SOURCE',
                   source_model='v_stg_crm__customers') }}
```

Thêm test cho **mỗi** satellite: `dbt_utils.unique_combination_of_columns` trên `(<hash key>, LOAD_DATETIME)`.

**Làm theo đúng thứ tự này:**
1. Viết 6 satellite theo mẫu, chưa thêm gì khác.
2. `./scripts/replay.sh`. Quan sát: từ **ngày 2**, test unique của `sat_customer_crm_status` **đỏ**, và các model phía sau bị SKIP.
3. Điều tra trước khi đọc gợi ý:
   ```bash
   dbt show --inline "select h.customer_code, s.city, s.LOAD_DATETIME from {{ ref('sat_customer_crm_status') }} s join {{ ref('hub_customer') }} h using (CUSTOMER_HK) where h.customer_code = 'C003' order by 3"
   ```
   C003 đổi thành phố 1 lần mà satellite có mấy dòng? Dòng nào bị chèn lại?
4. Sửa, replay, `check.py V4` PASS.

**Câu hỏi suy ngẫm**
1. Satellite so bản ghi mới với **dòng gần nhất** trong satellite. Stage `v_stg_crm__customers` chứa gì mà khiến phép so này sai? Vì sao `sat_order_shop` không bị?
2. Hai cách sửa: (a) `{{ config(apply_source_filter=true) }}`, (b) cho stage chỉ đọc file CRM mới nhất. Nếu một hôm dbt không chạy, cách nào vẫn ghi đủ lịch sử?
3. C005 đổi Member → Silver → Member. Satellite có mấy dòng? Vì sao không được "nhận ra" dòng 3 giống dòng 1 mà bỏ qua?
4. Vì sao tách `profile` (tên, email) khỏi `status` (thành phố, hạng)? Nghĩ tới yêu cầu "xoá dữ liệu cá nhân khi khách yêu cầu".
5. `sat_order_shop` đọc nguồn ghi đè. Nếu bạn dùng `simulate.py goto 6` thay vì `replay.sh`, satellite mất gì?

<details><summary>Gợi ý</summary>

Stage chứa **mọi file** CRM. Ở lần chạy ngày 2, với C003, các file là Ha Noi (ngày 0), Da Nang (ngày 1), Da Nang (ngày 2). automate_dv so từng dòng với dòng liền trước **trong stage**, riêng dòng đầu tiên so với dòng mới nhất của satellite (Da Nang). Ha Noi ≠ Da Nang → chèn lại; Da Nang ≠ Ha Noi → chèn lại. `apply_source_filter=true` bỏ các dòng stage cũ hơn dòng mới nhất đã có trong satellite. Thêm vào cả `sat_customer_crm_profile` và (cho chắc) `sat_order_pos`.
</details>

---

## V5 ⭐⭐⭐ Effectivity satellite: link nào đang hiệu lực

**Bối cảnh:** ngày 3, SKU07 chuyển `DT_PK` → `TT_TUI`. `link_product_category` giờ có 2 dòng cho SKU07 và không cho biết dòng nào còn hiệu lực.

**Yêu cầu:** `models/raw_vault/sats/eff_sat_product_category.sql`

```sql
{{ automate_dv.eff_sat(src_pk='LINK_PRODUCT_CATEGORY_HK',
                       src_dfk=['PRODUCT_HK'],       -- driving key: 1 sản phẩm chỉ thuộc 1 danh mục tại 1 thời điểm
                       src_sfk=['CATEGORY_HK'],
                       src_start_date='START_DATE', src_end_date='END_DATE',
                       src_eff='EFFECTIVE_FROM', src_ldts='LOAD_DATETIME', src_source='RECORD_SOURCE',
                       source_model='v_stg_erp__products') }}
```

Stage cần 2 derived column: `START_DATE: _loaded_at` và `END_DATE: "CAST('9999-12-31 23:59:59.999999' AS TIMESTAMP)"`.

Replay rồi xem SKU07. Có dòng nào đóng (`END_DATE` khác 9999) không? Nếu không, tìm trong [lý thuyết 6.3](../../GD2-ly-thuyet/tuan-6/03-automate-dv.md) cấu hình để eff_sat **tự đóng** link cũ khi driving key xuất hiện với danh mục mới.

**Kiểm tra:** `check.py V5` (phần đóng link chấm từ ngày 3).

**Câu hỏi suy ngẫm**
1. "Driving key" là gì? Nếu chọn sai driving key (chọn `CATEGORY_HK`), chuyện gì xảy ra khi thêm sản phẩm mới vào `TT_TUI`?
2. Trong Kimball (K3) bạn xử lý việc đổi danh mục bằng gì? So độ phức tạp.

---

## V6 ⭐⭐⭐ Multi-active satellite: nhiều số điện thoại cùng lúc

**Bối cảnh:** C001 có 2 số (di động, nhà riêng) cùng lúc. Satellite thường chỉ giữ 1 dòng / khách / thời điểm.

**Yêu cầu:**
- `models/raw_vault/stage/v_stg_crm__customer_phones.sql`: hash `CUSTOMER_HK`, `PHONE_HASHDIFF` trên `[phone_type, phone_number]`.
- `models/raw_vault/sats/ma_sat_customer_crm_phones.sql`:
  ```sql
  {{ automate_dv.ma_sat(src_pk='CUSTOMER_HK', src_cdk=['phone_type'], src_hashdiff='PHONE_HASHDIFF',
                        src_payload=['phone_number'], src_eff='EFFECTIVE_FROM', src_ldts='LOAD_DATETIME',
                        src_source='RECORD_SOURCE', source_model='v_stg_crm__customer_phones') }}
  ```
- Test unique `(CUSTOMER_HK, phone_type, LOAD_DATETIME)`.

Thử cho stage đọc thẳng `stg_crm__customer_phones` (mọi file), replay, chấm V6. Rồi tìm cách sửa: multi-active satellite **không có** `apply_source_filter`.

**Kiểm tra:** `check.py V6`. C001 phải có 2 **tập** số: tập ban đầu và tập từ ngày 4 (đổi di động, số nhà giữ nguyên nhưng vẫn được ghi lại trong tập mới). C008: tập từ ngày 5 chỉ còn số di động.

**Câu hỏi suy ngẫm**
1. Vì sao khi C001 chỉ đổi số di động, cả số nhà riêng cũng được ghi lại?
2. Khoá con (`src_cdk`) là gì? Chọn sai (vd chọn `phone_number`) thì sao?
3. Kimball làm gì với "nhiều số điện thoại"? (gợi ý: bridge như K11, hoặc chỉ giữ số chính)

<details><summary>Gợi ý sửa V6</summary>

Tạo model trung gian `models/raw_vault/stage/latest_crm__customer_phones.sql` chỉ lấy `extract_date = max(extract_date)`, rồi cho stage đọc model đó.
</details>

---

✅ Xong V1–V6: `./scripts/replay.sh` → V1–V6 PASS. Sang [05-data-vault-business-vault-va-mart.md](05-data-vault-business-vault-va-mart.md).
