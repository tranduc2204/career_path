# 00 — Cài đặt, dữ liệu và quy trình làm bài

## 1. Môi trường

Folder này là một uv project ghim **dbt-core 1.x + dbt-duckdb 1.x** (giống GĐ1).

```bash
cd ~/Desktop/target_ae/bai-tap-kimball-data-vault
uv sync                      # tạo .venv theo pyproject.toml
```

Mỗi lần mở terminal mới:

```bash
cd ~/Desktop/target_ae/bai-tap-kimball-data-vault
source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.          # profiles.yml nằm ngay trong lab/
```

Lần đầu:

```bash
dbt deps                           # cài dbt_utils và automate_dv
python scripts/simulate.py reset   # tạo lab.duckdb, nạp dữ liệu ngày 0
dbt build                          # chỉ có staging: 14 view + 28 test, phải xanh
python scripts/check.py            # 21 bài, tất cả SKIP
```

`dbt build` sẽ in cảnh báo *"Configuration paths exist in your dbt_project.yml file which do not apply to any resources"*. Đó là vì `dbt_project.yml` đã cấu hình sẵn các folder `marts/`, `raw_vault/`... mà bạn chưa tạo model. Bình thường, bỏ qua.

## 2. Khác gì lab GĐ1

| | Lab GĐ1 | Lab GĐ2 |
|---|---|---|
| Trọng tâm | Kỹ thuật dbt: Jinja, incremental, snapshot | **Thiết kế mô hình**: Kimball, Data Vault |
| Staging | Bạn tự viết | **Dựng sẵn** (`models/staging/`), chỉ làm "hard rules" |
| Nguồn | 1 hệ thống, 6 bảng | **5 hệ thống, 14 bảng**, mỗi hệ thống nạp một kiểu |
| Số ngày | 12 (có giai đoạn sự cố ẩn) | 7, kịch bản **công khai** |
| Materialization | Nhiều incremental | Kimball: `table` (dựng lại được bất cứ lúc nào). Vault: `incremental` chỉ thêm |

Đọc lướt các file trong `models/staging/` trước khi làm. Đó là "hợp đồng" bạn dựa vào: tên cột, grain, cách làm sạch.

## 3. Năm hệ thống nguồn

Mọi thứ nằm trong `lab/lab.duckdb`. Mỗi hệ thống là một schema (giống Fivetran/Airbyte đặt mỗi connector một schema):

```
                 ┌──────────── CÁCH NẠP ────────────┐
crm   (CRM)      │ file FULL mỗi ngày, NỐI THÊM     │  customers, customer_phones
shop  (web/app)  │ bảng trạng thái hiện tại, GHI ĐÈ │  orders, order_lines, order_vouchers
pos   (cửa hàng) │ chỉ thêm, ĐỒNG BỘ 2 NGÀY/LẦN     │  sales
wms   (kho vận)  │ log chỉ thêm, có dòng VỀ TRỄ      │  shipment_events, stock_movements
erp   (dữ liệu chủ) │ bảng trạng thái hiện tại, GHI ĐÈ │  products, categories, promotions, vouchers, locations, sales_targets
_lab             │ CHỈ ĐỂ CHẤM BÀI — không dùng trong model
```

Cách nạp quyết định cách bạn mô hình hoá. Ví dụ:
- CRM gửi cả file mỗi ngày → **có lịch sử sẵn**, SCD2 dựng lại được từ đầu bất cứ lúc nào, không cần snapshot.
- Shop ghi đè trạng thái đơn → **không có lịch sử**. Muốn biết đơn từng ở trạng thái nào thì phải chụp lại mỗi ngày (snapshot hoặc satellite của vault). Lỡ một ngày là mất.
- POS về trễ, kho vận có sự kiện về trễ và sai thứ tự → **dữ liệu đến muộn** là chuyện thường ngày.

### Bảng nguồn và model staging tương ứng

Tiền là **VND, số nguyên**. Staging đã ép sang `bigint`. Nếu bạn tự nhân 2 cột tiền kiểu `integer` của DuckDB, sẽ gặp lỗi *Overflow in multiplication of INT32*.

| Model staging | Grain | Cột chính | Ghi chú |
|---|---|---|---|
| `stg_crm__customers` | khách × file ngày | `customer_code, full_name, email, city, loyalty_tier, extract_date, _loaded_at` | Mọi file, không có `updated_at` |
| `stg_crm__customer_phones` | khách × loại số × file ngày | `customer_code, phone_type, phone_number, extract_date` | 1 khách có thể có nhiều số |
| `stg_shop__orders` | đơn online | `order_number, customer_code, channel, payment_method, is_gift, shipping_fee, total_amount, order_status, order_ts, order_date, paid_at, cancelled_at, updated_at, _loaded_at` | `total_amount` = khách trả cả đơn |
| `stg_shop__order_lines` | dòng đơn | `order_number, line_no, sku, quantity, unit_price` | `unit_price` đã trừ khuyến mãi |
| `stg_shop__order_vouchers` | voucher × đơn | `order_number, voucher_code, discount_amount` | 0–3 voucher / đơn |
| `stg_pos__sales` | dòng hoá đơn | `receipt_no, store_code, customer_code, payment_method, sale_ts, sale_date, line_no, sku, quantity, unit_price` | `customer_code` null = khách vãng lai |
| `stg_wms__shipment_events` | sự kiện | `event_id, order_number, event_type, event_ts, warehouse_code` | packed, shipped, delivery_failed, delivered, returned |
| `stg_wms__stock_movements` | biến động | `movement_id, sku, warehouse_code, movement_date, qty_change, reason` | opening, ship, return, receipt, adjustment |
| `stg_erp__products` | sản phẩm | `sku, product_name, brand, category_code, list_price` | Trạng thái hiện tại |
| `stg_erp__categories` | danh mục | `category_code, category_name, parent_code` | Cây không đều (1–3 cấp) |
| `stg_erp__promotions` | KM × sản phẩm | `promo_code, promo_name, sku, start_date, end_date, discount_pct` | |
| `stg_erp__vouchers` | voucher | `voucher_code, voucher_type, voucher_name` | |
| `stg_erp__locations` | địa điểm | `location_code, location_name, location_type, city` | 2 kho + 2 cửa hàng |
| `stg_erp__sales_targets` | tháng × danh mục cấp 1 | `target_month, category_code, target_amount` | Grain khác hẳn bán hàng |

Cây danh mục:

```
TT  Thời trang ──┬── TT_AO  Áo ──┬── TT_AO_THUN  Áo thun      ← SKU01, SKU02
                 │               └── TT_AO_KHOAC Áo khoác     ← SKU03
                 ├── TT_GIAY Giày dép                          ← SKU04, SKU05
                 └── TT_TUI  Túi xách                          ← (SKU07 từ ngày 3)
DT  Điện tử ─────┬── DT_PK   Phụ kiện điện tử ── DT_PK_SAC Sạc & cáp ← SKU06
                 │           ↑ SKU07 gắn thẳng vào DT_PK (không phải lá) tới ngày 2
                 └── DT_TN   Tai nghe                          ← SKU08
NC  Nhà cửa (không có con)                                     ← SKU09, SKU10
```

## 4. Dòng thời gian: 7 ngày

`python scripts/simulate.py next` đẩy thời gian lên 1 ngày. Ngày N có **ngày nghiệp vụ 01/03/2026 + N**, được nạp vào kho lúc **06:00 sáng hôm sau**. Ngày 0 có sẵn lịch sử từ 27/02.

| Ngày | Nghiệp vụ | Chuyện gì xảy ra | Bài liên quan |
|---|---|---|---|
| **0** | 01/03 | Nạp ban đầu: CRM 12 khách, 10 sản phẩm, 3 chương trình KM, đơn online 27/02–01/03 (W0001–W0010), POS 27–28/02, sự kiện kho vận và tồn kho đầu kỳ | tất cả |
| **1** | 02/03 | C003 chuyển **Ha Noi → Da Nang**. W0012 dùng **2 voucher** | K4, K11 |
| **2** | 03/03 | **POS đồng bộ trễ** hoá đơn 01–02/03 (C003 mua ở Hà Nội ngày 01/03, trước khi chuyển). Đơn **W0015 của C013, CRM chưa có khách này**, dùng **3 voucher**. C002 **sửa lỗi gõ email**. W0006 có sự kiện `delivered` nhưng **`shipped` chưa về**. Thêm KM_TAINGHE | K4, K6, K7, K8, K10, K11 |
| **3** | 04/03 | **C013 xuất hiện trong CRM**. C005 lên hạng **Member → Silver**. `shipped` của W0006 **về trễ**. W0008 **giao thất bại**. Kiểm kê **ngày 02/03** mới nhập (thiếu 2 SKU04 ở KHO_HN). **SKU07 đổi danh mục** DT_PK → TT_TUI. KM_THANG3 gia hạn. W0013 **huỷ sau khi đã đóng gói** | K6, K8, K9, K12, V5 |
| **4** | 05/03 | C005 về lại **Silver → Member** (A → B → A). C001 đổi số di động. POS đồng bộ 03–04/03 (có **C014, CRM không hề có**). W0008 giao thành công. W0002 **bị trả hàng**. W0025 **huỷ trước khi đóng gói** | K4, K6, K8, V4, V6 |
| **5** | 06/03 | C013 chuyển **Ho Chi Minh → Binh Duong**. C008 bỏ số điện thoại công ty. SKU01 **giảm giá niêm yết** | K3, K4, V6 |
| **6** | 07/03 | C012 lên hạng Silver. POS đồng bộ 05–06/03. Hết kịch bản | tất cả |

Quy tắc kho vận cho đơn online: đặt ngày D → `packed` D+1 08:30 → `shipped` D+1 16:00 → `delivered` D+3 11:00. Thẻ/ví thanh toán ngay khi đặt, COD thanh toán lúc giao. Đơn đặt từ 05/03 chưa kịp giao trước khi hết kịch bản (vẫn "mở").

## 5. Quy trình làm bài

### Vòng lặp hằng ngày

```bash
python scripts/simulate.py next     # sang ngày mới
dbt build                           # build + test toàn bộ
python scripts/check.py             # chấm tất cả (hoặc: check.py K4 K5)
```

### Khi sửa logic

| Bạn sửa | Làm gì |
|---|---|
| Model Kimball (`marts/`, `intermediate/`) | `dbt build -s <model>+`. Mọi model Kimball là `table` dựng lại từ nguồn → đúng ngay ở ngày hiện tại |
| Model raw vault (`raw_vault/`) | `./scripts/replay.sh`: reset rồi sống lại từng ngày. Vault **chỉ thêm**, nhiều nguồn ghi đè → lịch sử bỏ lỡ không lấy lại được |
| Muốn dừng ở một ngày | `./scripts/replay.sh 3` (mặc định tới ngày 6) |

`replay.sh` chạy `check.py` ở cuối. Bài K6 có phần chỉ chấm được **đúng ngày 2** (`./scripts/replay.sh 2`), phần còn lại chấm từ ngày 3.

### Các lệnh simulate

| Lệnh | Tác dụng |
|---|---|
| `reset` | **Xoá toàn bộ `lab.duckdb`** (cả model dbt), nạp ngày 0 |
| `next` | Sang ngày kế tiếp |
| `status` | Đang ở ngày nào, đã xảy ra gì |
| `goto N` | Reset rồi nhảy thẳng tới ngày N. Kimball vẫn đúng (vì là `table`). Raw vault sẽ **thiếu** trạng thái các ngày ở giữa |

### Xem dữ liệu

```bash
dbt show --inline "select * from {{ ref('stg_crm__customers') }} where customer_code = 'C005' order by extract_date"
dbt show --inline "select * from {{ ref('stg_wms__shipment_events') }} where order_number = 'W0006'"
dbt show -s fct_sales --limit 20
```

DBeaver mở được `lab.duckdb`, nhưng **DuckDB chỉ cho một tiến trình ghi**: ngắt kết nối trước khi chạy dbt/simulate.

## 6. Quy ước của lab (check.py dựa vào đây)

| Quy ước | Giá trị |
|---|---|
| Tên model, tên cột | Đúng **y như** bảng trong đề |
| Khoá ngày | `integer` dạng `yyyymmdd`, ví dụ `20260301` |
| Khoá surrogate của dimension | `dbt_utils.generate_surrogate_key([...])` theo cột đề bài nêu |
| Thành viên đặc biệt | `'-1'` = không xác định (unknown). `'-2'` = không áp dụng (not applicable). Ngày: `-1` = "Chưa xảy ra" |
| Doanh thu | Đơn online **không huỷ** + mọi hoá đơn POS. Đơn trả hàng vẫn là một lần bán (việc trả được theo dõi ở K8) |
| Thời điểm của một giao dịch | `order_ts` (online) / `sale_ts` (POS), không phải lúc dữ liệu về kho |

Macro có sẵn: `{{ business_date() }}` trả về ngày nghiệp vụ mới nhất kho đã có (ngày của file CRM mới nhất). Dùng khi cần dãy ngày "tới hôm nay".

## 7. Cú pháp cần biết với dbt 1.10+

Tham số của generic test đặt dưới `arguments:`:

```yaml
data_tests:
  - relationships:
      arguments:
        to: ref('dim_customer')
        field: customer_key
```

## 8. Lỗi hay gặp khi setup

| Lỗi | Cách sửa |
|---|---|
| `Could not find profile named 'lab'` | Quên `export DBT_PROFILES_DIR=.` hoặc không đứng trong `lab/` |
| `Could not set lock on file lab.duckdb` | Đóng DBeaver / tiến trình dbt khác |
| `automate_dv is undefined` | Chưa `dbt deps` |
| `Overflow in multiplication of INT32` | Đang nhân cột tiền lấy thẳng từ nguồn. Dùng cột từ staging (đã là `bigint`) |
| `check.py` SKIP dù đã viết model | Chưa `dbt build`, hoặc tên model khác tên trong đề |
| Model đúng mà `check.py` vẫn chấm số cũ | `dbt build` đã **SKIP** model đó vì test phía trên đỏ. Đọc dòng SKIP trong output |
