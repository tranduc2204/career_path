# 00 — Cài đặt, dữ liệu, đồng hồ của lab và quy trình làm bài

## 1. Môi trường

Folder này là một uv project ghim **dbt-core 1.x + dbt-duckdb + dbt-metricflow + dagster + dagster-dbt**.

```bash
cd ~/Desktop/target_ae/bai-tap-semantic-dq-governance
uv sync                      # lần đầu mất vài phút (dagster khá nặng)
```

Mỗi lần mở terminal mới:

```bash
cd ~/Desktop/target_ae/bai-tap-semantic-dq-governance
source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.
```

Lần đầu:

```bash
dbt deps
python scripts/simulate.py reset   # tạo lab.duckdb, nạp ngày 0
dbt build                          # 16 model + 30 test, phải xanh
python scripts/check.py            # 26 bài, tất cả SKIP
```

Phiên bản đã kiểm chứng (07/11/2026): dbt-core 1.12.6, dbt-duckdb 1.11.1, DuckDB 1.5.6, dbt-metricflow 0.15.0 (metricflow 0.213.0), Elementary 0.26.1, dagster 1.13.29 + dagster-dbt 0.29.29. Airflow 3.4.0 + astronomer-cosmos 1.16.0 chạy trong venv riêng (bài O5).

> **DuckDB chỉ cho 1 tiến trình ghi.** Đừng mở `lab.duckdb` bằng DBeaver/DuckDB CLI ở chế độ ghi trong lúc chạy `dbt` hoặc `mf`. Muốn xem dữ liệu thì dùng `dbt show --inline "select ..."` hoặc `duckdb -readonly lab.duckdb`.

## 2. Khác gì lab GĐ1–GĐ2

| | Lab GĐ2 | Lab GĐ3 |
|---|---|---|
| Trọng tâm | Thiết kế mô hình | **Vận hành nền tảng**: metric, chất lượng, quyền, lịch chạy |
| Model | Bạn tự dựng mart | **Mart dựng sẵn**, bạn viết YAML + test + cấu hình |
| Dữ liệu | 34 đơn, 7 ngày | **~7.300 đơn, 76.000 phiên**, 60 ngày lịch sử + 8 ngày lab |
| Sự cố | Bẫy mô hình hoá | **6 sự cố production thật** (connector chết, mất dữ liệu, đổi schema...) |
| Chấm | So bảng kết quả | So kết quả `mf query`, **kết quả test theo từng ngày**, manifest |

## 3. Nguồn dữ liệu

Mọi thứ nằm trong `lab/lab.duckdb`. Mỗi connector là một schema:

| Schema.bảng | Grain | Cột chính | Cách nạp |
|---|---|---|---|
| `shop.orders` | đơn | `order_id, customer_id, session_id, order_ts, channel (web/app), utm_source, payment_method, shipping_fee, status, updated_at, _loaded_at` | Ghi đè trạng thái: placed → shipped/cancelled (D+1) → completed (D+3) |
| `shop.order_items` | dòng hàng | `order_id, line_no, product_id, quantity, unit_price, unit_cost, _loaded_at` | Chỉ thêm (trừ khi đội app restate) |
| `shop.refunds` | lần hoàn tiền | `refund_id, order_id, refund_ts, amount, reason, _loaded_at` | Chỉ thêm. **Thưa**: 0–5 dòng/ngày, có ngày không có dòng nào |
| `crm.customers` | khách | `customer_id, full_name, email, phone, city, segment, birth_date, signup_date, updated_at, _loaded_at` | Ghi đè. **Chứa PII** |
| `erp.products` | sản phẩm | `product_id, product_name, category, brand, list_price, unit_cost, _loaded_at` | Ghi đè. Gần như không đổi |
| `web.sessions` | phiên | `session_id, customer_id (NULL ~40% = chưa đăng nhập), session_start, device, utm_source, landing_page, _loaded_at` | Chỉ thêm |
| `mkt.ad_spend` | ngày × nguồn | `spend_date, utm_source (google/facebook/tiktok), spend, _loaded_at` | Chỉ thêm |
| `ingest.sync_log` | lần chạy connector × bảng | `connector, table_name, synced_at, rows_synced, status (success/failed), error_message` | Mỗi lần connector chạy ghi 1 dòng **kể cả khi 0 dòng mới hoặc lỗi** (giống `fivetran_audit`) |
| `_lab.state` | | | **Chỉ để chấm**, không dùng trong model |

`_loaded_at` = lúc connector ghi dòng đó vào kho. Tiền là VND, số nguyên.

### Model dựng sẵn

```
staging (view, private sau bài G2)          marts (table, public sau bài G2)
stg_shop__orders ────────────────┬──▶ fct_orders            (1 dòng / đơn, mọi trạng thái, có is_cancelled)
stg_shop__order_items ───────────┼──▶ fct_order_items       (1 dòng / dòng hàng, KHÔNG có trạng thái đơn)
stg_shop__refunds ───────────────┼──▶ fct_refunds           (thời gian = ngày hoàn tiền)
stg_erp__products ───────────────┼──▶ dim_products
stg_crm__customers ──────────────┼──▶ dim_customers         (PII)
stg_web__sessions ───────────────┼──▶ fct_sessions
stg_mkt__ad_spend ───────────────┴──▶ fct_ad_spend
                                      dim_marketing_channels (5 utm_source → channel_group paid/organic/owned)
models/growth/growth_campaign_daily   ← của đội Growth, đang ref thẳng staging của Commerce (bài G2)
```

Định nghĩa nghiệp vụ dùng chung (đề bài M dựa vào đây):

- **Doanh thu (revenue)** = tổng `line_amount` (= quantity × unit_price) của các dòng hàng thuộc đơn **không bị huỷ**, tính theo **ngày đặt**. Không gồm phí ship.
- **Đơn (orders)** = số đơn không bị huỷ. **Người mua (buyers)** = số khách distinct có đơn không bị huỷ.
- **Hoàn tiền (refunds)** = tổng tiền hoàn, tính theo **ngày hoàn tiền**.

## 4. Đồng hồ của lab

Freshness và anomaly detection đều so với "bây giờ". Lab nén 8 ngày vào vài phút, nên **"bây giờ" là giờ giả lập**:

- Ngày lab N có ngày nghiệp vụ **30/11/2026 + N**. Connector nạp lúc **06:00 sáng hôm sau**, dbt chạy lúc **06:30**.
- `simulate.py` ghi giờ 06:30 đó vào 2 dòng `# LAB_CLOCK` trong `dbt_project.yml`:
  - `lab_now` → macro `macros/lab_clock.sql` ghi đè `current_timestamp()` của dbt-duckdb, nên `dbt source freshness` tính tuổi dữ liệu theo giờ lab.
  - `custom_run_started_at` → biến có sẵn của Elementary, dùng làm "thời điểm chạy" cho anomaly test.
- **Đừng sửa tay 2 dòng đó**, và đừng xoá dấu `# LAB_CLOCK` khi chép `dbt_project.yml` của đáp án.

Ở công ty thật bạn không làm thế này. Đây chỉ là cách để kịch bản nhiều ngày chạy được trên máy.

## 5. Dòng thời gian: 8 ngày, 6 sự cố

`python scripts/simulate.py next` đẩy thời gian lên 1 ngày. Kịch bản **công khai**: bạn biết trước sự cố nào xảy ra ngày nào. Cái khó là viết **một bộ test duy nhất** bật đúng ngày có sự cố và im lặng mọi ngày khác.

| Ngày | Nghiệp vụ | Chuyện gì xảy ra | Bài |
|---|---|---|---|
| **0** | 30/11 | Nạp ban đầu: 60 ngày lịch sử (01/10 → 29/11) + ngày 30/11 | tất cả |
| **1** | 01/12 | Ngày bình thường | Q7 |
| **2** | 02/12 | Connector shop chỉ kịp kéo **~30% đơn** ngày 02/12 (và dòng hàng của chúng) | Q2 |
| **3** | 03/12 | 70% đơn ngày 02/12 **về trễ**. Lỗi tracking: **~90% phiên mất customer_id** (khách vẫn mua bình thường). P007 giảm giá | Q2, Q3 |
| **4** | 04/12 | Connector **mkt hết hạn token**, không nạp được (sync_log ghi `failed`). Website mở thanh toán **`bnpl`** | Q1, Q4 |
| **5** | 05/12 | mkt vẫn lỗi. CRM nâng cấp: cột **`phone` đổi tên thành `phone_number`** | Q1, Q5 |
| **6** | 06/12 | mkt vẫn lỗi. App lỗi: đơn kênh app ghi **unit_price theo nghìn đồng** (299 thay vì 299000). P021 tăng giá | Q1, Q6 |
| **7** | 07/12 | mkt chạy lại, **nạp bù** 04 → 07/12. Đội app **restate** đúng giá các dòng ngày 06/12. Ngày này **không có hoàn tiền nào** | Q1, Q7 |

## 6. Quy trình làm bài

### Phần M và G: không cần đi qua các ngày

```bash
dbt build                     # hoặc dbt parse nếu chỉ sửa YAML semantic
python scripts/check.py M     # chấm cả nhóm M (gọi mf query thật, mỗi lần vài giây)
python scripts/check.py M4 G2 # vài bài
```

**Sửa YAML semantic mà `dbt parse` báo lỗi lạ kiểu "trùng tên metric"?** Đó là partial parsing chưa theo kịp. Chạy `dbt parse --no-partial-parse`.

### Phần Q: phải đi qua từng ngày

Elementary học từ kết quả các lần chạy trước, còn `check.py` cần kết quả test của **từng ngày**. Vì vậy:

```bash
# đi tay, để quan sát
python scripts/simulate.py next
./scripts/run_day.sh          # freshness + build, lưu .replay/day_N/, in tóm tắt tín hiệu của ngày

# chấm thật: làm lại từ đầu
./scripts/replay.sh           # ngày 0 → 7, khoảng 3–4 phút, cuối cùng chạy check.py
./scripts/replay.sh 3         # dừng ở ngày 3
```

Mỗi ngày `run_day.sh` in một dòng kiểu:

```
📋 Ngày 2: freshness xanh · test bật ['volume_anomalies@shop.orders=warn'] · model lỗi/skip không
```

Mỗi lần sửa test hay ngưỡng ở phần Q, chạy lại `replay.sh`. Đừng dùng `goto N` để chấm Q: nó bỏ qua lịch sử các ngày ở giữa.

### Phần O

```bash
python scripts/check.py O     # O4 chạy thật 1 lần materialize (~15 giây)
dagster dev -m orchestration.dagster_maystore.definitions   # mở UI http://localhost:3000
```

## 7. Câu hỏi tự kiểm tra trước khi làm

1. Vì sao `fct_order_items` không có cột `status`, và semantic layer lọc đơn huỷ bằng cách nào?
2. `shop.refunds` có ngày 0 dòng. Freshness đo theo `_loaded_at` sẽ ra sao vào hôm sau ngày đó?
3. Cột `web.sessions.customer_id` có NULL ~40%. Test nào **không** dùng được cho cột này?
4. Nếu `dbt build` gặp test lỗi (severity error) trên `stg_shop__order_items`, những model nào bị skip?
