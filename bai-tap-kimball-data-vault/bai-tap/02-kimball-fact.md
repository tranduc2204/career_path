# 02 — Kimball: các loại fact và dữ liệu đến muộn (K5–K9)

> Lý thuyết: [4.1 grain & loại fact](../../GD2-ly-thuyet/tuan-4/01-quy-trinh-4-buoc-va-grain.md) · [4.3 junk / degenerate](../../GD2-ly-thuyet/tuan-4/03-ky-thuat-dimension.md) · [4.6 accumulating & periodic snapshot](../../GD2-ly-thuyet/tuan-4/06-accumulating-va-periodic-snapshot.md) · [4.7 late-arriving](../../GD2-ly-thuyet/tuan-4/07-late-arriving-facts-va-dimensions.md)

**Tình huống:** dimension đã xong. Ba nhóm đang chờ bạn:
- 🗨️ Kế toán: *"Doanh thu phải khớp từng đồng với số tiền khách trả."*
- 🗨️ Vận hành: *"Đơn mất bao nhiêu ngày từ lúc đặt tới lúc giao? Đơn nào đang kẹt?"*
- 🗨️ Kho: *"Tồn kho cuối mỗi ngày của từng sản phẩm ở từng kho là bao nhiêu?"*

⭐⭐ trung bình · ⭐⭐⭐ khá · ⭐⭐⭐⭐ nâng cao

---

## K5 ⭐⭐⭐ `fct_sales` + junk dimension `dim_order_profile`

**Grain (viết vào description):** *1 dòng = 1 dòng đơn online hoặc 1 dòng hoá đơn POS đã bán. Đơn huỷ không có mặt.*

**Bước 1 (khuyên dùng):** `models/intermediate/int_sales__lines.sql` gộp 2 nguồn về cùng hình dạng: dòng đơn online (join đầu đơn + tổng voucher) `union all` dòng POS (kênh `'store'`, không quà tặng, không voucher, không phí ship). Giữ cả đơn huỷ với cờ `is_cancelled`.

**Bước 2:** `models/marts/core/dim_order_profile.sql`: **junk dimension** gom 3 thuộc tính ít giá trị.

| Cột | |
|---|---|
| `order_profile_key` | `generate_surrogate_key(['channel', 'payment_method', 'is_gift'])` |
| `channel` | `web`, `app`, `store` |
| `payment_method` | `cod`, `card`, `ewallet`, `cash` |
| `is_gift` | |

Chỉ lấy các tổ hợp **thực sự xuất hiện**.

**Bước 3:** `models/marts/sales/fct_sales.sql`

| Cột | Cách tính |
|---|---|
| `order_date_key` | khoá ngày của ngày đặt / ngày bán |
| `customer_key` | phiên bản khách **hiệu lực tại `order_ts`**: `valid_from <= order_ts < valid_to`. Khách vãng lai → `'-1'` |
| `product_key` | theo `sku` |
| `order_profile_key` | theo (channel, payment_method, is_gift) |
| `store_location_key` | POS: cửa hàng. Online: `'-2'` (không áp dụng) |
| `source_system` | `'shop'` / `'pos'` |
| `order_number`, `line_no` | **degenerate dimension**: POS dùng `receipt_no` làm `order_number` |
| `order_ts` | |
| `quantity`, `unit_price`, `gross_amount` | `gross_amount = quantity * unit_price` |
| `discount_allocated` | tổng voucher của đơn **phân bổ** xuống dòng |
| `shipping_fee_allocated` | phí ship của đơn phân bổ xuống dòng |
| `net_amount` | `gross_amount - discount_allocated + shipping_fee_allocated` |

**Quy tắc phân bổ** (cho cả voucher và phí ship): theo tỷ trọng `gross_amount` của dòng trong đơn, làm tròn tới đồng (`round`). **Dòng có `line_no` lớn nhất nhận phần còn lại** để tổng các dòng luôn khớp đúng số của đầu đơn.

Test:
- `dbt_utils.unique_combination_of_columns` trên `(order_number, line_no)`
- `relationships` từ mọi cột khoá tới dimension tương ứng
- Singular test `tests/assert_fct_sales_reconciles_with_orders.sql`: với mỗi đơn online, `sum(net_amount)` = `stg_shop__orders.total_amount`. Trả về các đơn lệch.

**Kiểm tra:** `check.py K5`. Thử ở ngày 1 với đơn W0012 (2 voucher, 2 dòng):

```bash
dbt show --inline "select order_number, line_no, gross_amount, discount_allocated, shipping_fee_allocated, net_amount from {{ ref('fct_sales') }} where order_number = 'W0012'"
```

**Câu hỏi suy ngẫm**
1. Vì sao không để nguyên `order_discount_total` và `shipping_fee` ở mọi dòng? Thử `sum()` cột đó cho W0012 sẽ thấy.
2. Junk dimension khác gì để 3 cột cờ ngay trong fact? Khác gì làm 3 dimension tí hon?
3. Vì sao `order_number` không cần bảng dimension riêng?
4. Nếu sau này shop có giảm giá **theo dòng** (line discount) thì có còn phải phân bổ không?
5. Đơn W0013 bị huỷ ở ngày 3. Với fact là `table` dựng lại mỗi ngày thì nó tự biến mất. Nếu fact là `incremental`, bạn xử lý thế nào?

<details><summary>Gợi ý phân bổ</summary>

```sql
shares as (
    select *,
        sum(gross_amount) over (partition by order_number)        as order_gross_amount,
        line_no = max(line_no) over (partition by order_number)   as is_last_line
    from lines
),
parts as (
    select *,
        case when not is_last_line
             then round(order_discount_total * gross_amount / order_gross_amount) end as discount_part
    from shares
)
select *,
    coalesce(discount_part,
             order_discount_total - coalesce(sum(discount_part) over (partition by order_number), 0)) as discount_allocated
from parts
```
</details>

---

## K6 ⭐⭐⭐ Late-arriving dimension: inferred member

**Bối cảnh:** ngày 2, khách C013 đặt đơn W0015 trên app. CRM chỉ có C013 từ file ngày 3. Fact tới **trước** dimension.

3 lựa chọn phổ biến:

| Cách | Hệ quả |
|---|---|
| Gán `'-1'` (không xác định), sửa sau | Doanh thu C013 nằm ở "không xác định" cho tới khi bạn sửa. Fact incremental thì phải tự viết logic gán lại |
| Giữ fact lại ở bảng chờ (suspense) | Doanh thu ngày 2 **thiếu** W0015 |
| **Inferred member** | Tạo sẵn 1 dòng dimension cho C013 với thuộc tính "Chưa xác định". Khi CRM gửi C013, **ghi đè** chính dòng đó (không tạo phiên bản mới). Fact không phải đổi khoá |

**Yêu cầu:** sửa `dim_customer`:
- Mọi `customer_code` có trong `stg_shop__orders` hoặc `stg_pos__sales` mà CRM **chưa từng có** → 1 dòng: `full_name`, `city`, `loyalty_tier` = `'Chưa xác định'`, `email` null, hiệu lực 1900 → 9999, `is_inferred = true`.
- Khi CRM có khách, dòng inferred biến mất, thay bằng phiên bản thật. Vì phiên bản thật đầu tiên cũng bắt đầu từ `1900-01-01` nên **`customer_key` giữ nguyên**.

**Kiểm tra:** chấm ở 2 thời điểm.

```bash
./scripts/replay.sh 2 -s +dim_customer+      # dừng ở ngày 2: C013 là inferred, W0015 gắn vào nó
python scripts/simulate.py next && dbt build && python scripts/check.py K6   # ngày 3: C013 thật, cùng khoá
```

Từ ngày 4 còn có C014: khách chỉ mua ở cửa hàng, CRM **không bao giờ** có. Nó mãi là inferred.

**Câu hỏi suy ngẫm**
1. Nếu bạn để phiên bản đầu bắt đầu từ ngày file CRM đầu tiên của khách (04/03 với C013), chuyện gì xảy ra với `customer_key` của W0015 khi sang ngày 3? Với fact `table` có sao không? Với fact `incremental` thì sao?
2. Trong cách inferred member, "ghi đè dòng inferred" là Type 1 hay Type 2? Vì sao Kimball chọn vậy?
3. Ai nên được báo khi số khách inferred tăng bất thường? Viết 1 test cảnh báo (`severity: warn`) khi có hơn 2 khách inferred.

---

## K7 ⭐⭐⭐ Late-arriving fact: hoá đơn POS về trễ

**Bối cảnh:** POS đồng bộ 2 ngày một lần. Ngày 2 kho mới nhận hoá đơn HN-0003 của C003, mua ngày **01/03** ở Hà Nội. Lúc dữ liệu về, C003 đã chuyển vào Đà Nẵng (từ 02/03).

**Yêu cầu:** không cần model mới. `fct_sales` của bạn phải gán đúng:
- HN-0003 (01/03) → phiên bản Ha Noi
- HN-0004 (02/03) → phiên bản Da Nang
- Từ ngày 4: W0019 (C005 mua 04/03) → hạng Silver, dù sau đó C005 về Member

**Kiểm tra:** `check.py K7` từ ngày 2.

**Thí nghiệm (nên làm):** tạm đổi điều kiện join trong `fct_sales` thành `c.customer_code = a.customer_code and c.is_current`, build, chấm K5 và K7. Đọc thông báo lỗi. Rồi đổi lại.

**Câu hỏi suy ngẫm**
1. Join theo `is_current` hay theo `valid_from <= order_ts < valid_to`: báo cáo "doanh thu theo thành phố" khác nhau thế nào? Mỗi cách trả lời câu hỏi kinh doanh nào?
2. Nếu `fct_sales` là incremental với watermark `_loaded_at` (như GĐ1), HN-0003 có được nạp không? Nếu watermark là `sale_ts` với lookback 1 ngày thì sao?
3. Doanh thu ngày 01/03 bạn báo cáo ở sáng ngày 1 và sáng ngày 2 khác nhau. Kế toán đã "khoá sổ" ngày 01/03 rồi thì làm gì?

---

## K8 ⭐⭐⭐⭐ Accumulating snapshot `fct_order_fulfillment`

**Grain:** *1 dòng = 1 đơn online (kể cả đơn huỷ), được cập nhật mỗi khi đơn qua một mốc mới.*

**Yêu cầu:** `models/marts/ops/fct_order_fulfillment.sql`

| Cột | Quy tắc |
|---|---|
| `order_number` | |
| `customer_key` | phiên bản khách tại `order_ts` |
| `order_profile_key` | |
| `warehouse_location_key` | kho trong sự kiện kho vận của đơn; chưa có sự kiện nào → `'-1'` |
| `order_date_key` | từ `order_ts` |
| `paid_date_key` | từ `paid_at` |
| `packed_date_key`, `shipped_date_key`, `delivered_date_key`, `returned_date_key` | ngày của sự kiện tương ứng **sớm nhất** |
| `cancelled_date_key` | từ `cancelled_at` |
| `current_status` | ưu tiên: `cancelled` > `returned` > `delivered` > `shipped` > `packed` > `paid` > `placed` |
| `order_total_amount` | `total_amount` |
| `item_quantity` | tổng số lượng các dòng |
| `failed_delivery_count` | số sự kiện `delivery_failed` |
| `days_to_ship` | số ngày từ ngày đặt tới ngày gửi; chưa gửi → null |
| `days_to_deliver` | số ngày từ ngày đặt tới ngày giao; chưa giao → null |

Mốc chưa xảy ra → khoá ngày `-1`, **không để null**. Thêm test `not_null` + `relationships` tới `dim_date` cho cả 7 khoá ngày.

**Kiểm tra:** `check.py K8` mỗi ngày. Theo dõi các đơn đặc biệt:

```bash
dbt show --inline "select order_number, current_status, order_date_key, packed_date_key, shipped_date_key, delivered_date_key, returned_date_key, cancelled_date_key, failed_delivery_count, days_to_deliver from {{ ref('fct_order_fulfillment') }} where order_number in ('W0002','W0006','W0008','W0013','W0025')"
```

| Đơn | Ngày 2 | Ngày 3 | Ngày 4 |
|---|---|---|---|
| W0006 | đã giao nhưng chưa có ngày gửi | ngày gửi được điền (01/03) | |
| W0008 | đang giao | giao hỏng 1 lần | giao thành công 05/03 |
| W0013 | đã đóng gói | huỷ | |
| W0002 | đã giao | | trả hàng |

**Câu hỏi suy ngẫm**
1. Transaction fact chỉ thêm dòng. Vì sao accumulating snapshot lại **sửa** dòng cũ?
2. W0006 ở ngày 2 có `shipped_date_key = -1` nhưng `delivered_date_key` có giá trị. `days_to_ship` lúc đó là null. Báo cáo "trung bình ngày gửi hàng" có bị lệch không? Xử lý thế nào?
3. Viết lại model này dạng **incremental** `merge` theo `order_number`: mỗi lần chạy cần xử lý những đơn nào? (gợi ý: đơn có sự kiện mới HOẶC đầu đơn đổi, theo `_loaded_at`)
4. Vì sao lấy sự kiện **sớm nhất** chứ không phải sự kiện **về kho sau cùng**?

---

## K9 ⭐⭐⭐ Periodic snapshot `fct_inventory_daily`

**Grain:** *1 dòng = 1 sản phẩm × 1 kho × 1 ngày.* **Dày đặc**: ngày không có biến động vẫn có dòng.

**Yêu cầu:** `models/marts/ops/fct_inventory_daily.sql`

| Cột | Quy tắc |
|---|---|
| `snapshot_date_key` | mỗi ngày từ ngày biến động đầu tiên (27/02) tới `{{ business_date() }}` |
| `product_key` | mọi sản phẩm |
| `warehouse_location_key` | 2 kho (`location_type = 'warehouse'`) |
| `quantity_on_hand` | tồn **cuối ngày** = cộng dồn `qty_change` tới hết ngày đó |
| `quantity_in` | tổng `qty_change` dương trong ngày |
| `quantity_out` | tổng trị tuyệt đối `qty_change` âm trong ngày |

Test: unique `(snapshot_date_key, product_key, warehouse_location_key)`; `dbt_utils.expression_is_true` với `quantity_on_hand >= 0`.

**Kiểm tra:** `check.py K9`. Sang ngày 3 build lại: tồn SKU04 ở KHO_HN từ ngày 02/03 trở đi giảm 2 vì điều chỉnh kiểm kê **lùi ngày**.

**Câu hỏi suy ngẫm**
1. `quantity_on_hand` cộng theo sản phẩm có nghĩa không? Cộng theo kho? Cộng theo ngày? Báo cáo "tồn kho tháng 3" nên dùng phép gì?
2. `quantity_in`, `quantity_out` có cùng tính chất đó không?
3. Nếu bảng này là incremental (chỉ thêm ngày mới), điều chỉnh lùi ngày 02/03 ở ngày 3 sẽ bị bỏ qua. Thiết kế cách xử lý.
4. Dày đặc vs thưa (chỉ ngày có biến động): mỗi cách tốn gì, lợi gì? Với 50.000 sản phẩm × 30 kho × 3 năm thì sao?

<details><summary>Gợi ý</summary>

Lưới = `dim_date` (lọc khoảng ngày) × danh sách sản phẩm × danh sách kho, `left join` biến động đã gộp theo ngày, rồi:
```sql
sum(net_change) over (partition by sku, warehouse_code order by full_date
                      rows between unbounded preceding and current row) as quantity_on_hand
```
</details>

---

✅ Xong K5–K9 (K6, K7 cần ngày ≥ 2). Sang [03-kimball-nang-cao.md](03-kimball-nang-cao.md).
