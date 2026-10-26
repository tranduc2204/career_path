# 4.6 Accumulating snapshot và periodic snapshot

> 4.1 đã giới thiệu 3 loại fact. File này đi sâu 2 loại "snapshot", thứ phân biệt Junior với Mid trong phỏng vấn mô hình hoá.

## Phần 1. Accumulating snapshot

### Khi nào dùng

Khi quy trình là một **đường ống (pipeline) có điểm đầu, điểm cuối và các mốc ở giữa**, và câu hỏi xoay quanh **thời gian giữa các mốc**:

| Quy trình | Các mốc |
|---|---|
| Thực hiện đơn hàng | đặt → thanh toán → đóng gói → gửi → giao → (trả hàng / huỷ) |
| Xét duyệt khoản vay | nộp hồ sơ → thẩm định → phê duyệt → giải ngân |
| Tuyển dụng | nhận CV → phỏng vấn → offer → nhận việc |
| Bồi thường bảo hiểm | báo tổn thất → giám định → duyệt → chi trả |
| Lệnh sản xuất (AdventureWorks `WorkOrder`) | bắt đầu → hạn → hoàn thành |

Câu hỏi điển hình: "Trung bình mất bao nhiêu ngày từ lúc đặt tới lúc giao?", "Bao nhiêu đơn đang kẹt ở bước đóng gói quá 2 ngày?".

### Cấu trúc

**Grain: 1 dòng = 1 thực thể đi qua đường ống** (1 đơn). Dòng được **cập nhật** mỗi khi thực thể qua mốc mới. Đây là loại fact duy nhất sửa dòng cũ.

```
fct_order_fulfillment
├── order_number                    (degenerate)
├── customer_key, order_profile_key, warehouse_location_key
├── order_date_key      ─┐
├── paid_date_key        │
├── packed_date_key      │  7 khoá ngày = dim_date đóng 7 VAI
├── shipped_date_key     │  mốc chưa tới → -1 ("Chưa xảy ra")
├── delivered_date_key   │
├── returned_date_key    │
├── cancelled_date_key  ─┘
├── current_status
└── measures: order_total_amount, item_quantity, failed_delivery_count,
              days_to_ship, days_to_deliver          ← "lag" giữa các mốc
```

| Thành phần | Ghi chú |
|---|---|
| Khoá ngày mỗi mốc | **Không null**, dùng `-1` |
| Lag (độ trễ) | Tính sẵn (`days_to_ship`) để BI không phải tính hiệu 2 ngày. Mốc chưa tới → lag `null` (không phải 0) |
| `current_status` | Mốc xa nhất đã đạt, theo thứ tự ưu tiên nghiệp vụ |
| Đếm theo trạng thái | "Đơn đang ở bước X" = `count(*) where current_status = 'X'` |

### Quy tắc khó: sự kiện về trễ, sai thứ tự, lặp lại

| Tình huống (có trong lab) | Quy tắc |
|---|---|
| `delivered` về kho **trước** `shipped` (W0006) | Mốc = thời điểm **xảy ra** sớm nhất của sự kiện (`min(event_ts)`), không phụ thuộc thứ tự về kho. Khi `shipped` về, dòng được sửa lại |
| Giao thất bại rồi giao lại (W0008) | `delivered_date` = lần giao **thành công**. Đếm lần thất bại thành measure |
| Huỷ sau khi đã đóng gói (W0013) | Giữ `packed_date`, thêm `cancelled_date`, status `cancelled` |
| Trả hàng sau khi đã giao (W0002) | Giữ `delivered_date`, thêm `returned_date` |

Viết các quy tắc này vào description của model. Nhóm vận hành và nhóm BI phải đồng ý với chúng.

### Cài đặt trong dbt

| Cách | Mô tả | Khi nào |
|---|---|---|
| **Dựng lại toàn bộ** (`table`) | Mỗi lần chạy tính lại từ toàn bộ đơn + toàn bộ sự kiện | Vài triệu đơn trở xuống. **Đơn giản, idempotent, tự sửa sai**. Lab dùng cách này |
| **Incremental `merge`** theo `order_number` | Mỗi lần chạy chỉ xử lý các đơn **có thay đổi**: đầu đơn đổi, hoặc có sự kiện mới (lọc theo `_loaded_at` của cả 2 nguồn) | Bảng rất lớn |

Incremental cho accumulating snapshot dễ sai:

```sql
-- fact lưu thêm cột _loaded_at_max = _loaded_at lớn nhất của đầu đơn và mọi sự kiện của đơn đó
{% if is_incremental() %}
with changed_orders as (
    select order_number from {{ ref('stg_shop__orders') }}
    where _loaded_at > (select max(_loaded_at_max) from {{ this }})
    union
    select order_number from {{ ref('stg_wms__shipment_events') }}
    where _loaded_at > (select max(_loaded_at_max) from {{ this }})
)
{% endif %}
-- rồi tính lại ĐẦY ĐỦ mốc của các đơn này từ TOÀN BỘ sự kiện của chúng (không chỉ sự kiện mới!)
```

Lỗi điển hình: chỉ tính mốc từ **sự kiện mới** → `merge` ghi đè `packed_date` thành `-1` vì lần chạy này không thấy sự kiện `packed`. Luôn tính lại từ toàn bộ lịch sử của đơn.

### Đóng đơn

Đường ống có điểm cuối (giao xong, huỷ, trả). Có thể đánh dấu `is_closed` để:
- Báo cáo "đơn đang mở".
- Incremental bỏ qua đơn đã đóng quá N ngày (tăng tốc).

## Phần 2. Periodic snapshot

### Khi nào dùng

Khi cần **trạng thái tại các mốc đều đặn**: cuối ngày, cuối tháng.

| Quy trình | Grain |
|---|---|
| Tồn kho | sản phẩm × kho × ngày |
| Số dư tài khoản | tài khoản × tháng |
| Số thuê bao đang hoạt động | gói cước × ngày |
| Công nợ phải thu | khách hàng × tháng |

Transaction fact (biến động) trả lời "hôm nay nhập/xuất bao nhiêu". Periodic snapshot trả lời "cuối ngày còn bao nhiêu" mà **không phải cộng dồn lại từ đầu** mỗi lần hỏi.

### Dày đặc (dense)

Periodic snapshot thường **dày đặc**: mọi thực thể × mọi kỳ đều có dòng, kể cả kỳ không có biến động. Lý do: "tồn kho SKU04 ngày 03/03" phải có câu trả lời ngay cả khi hôm đó không nhập không xuất.

```sql
grid as (                                   -- lưới đầy đủ
    select d.date_key, d.full_date, p.sku, w.location_code as warehouse_code
    from days d cross join products p cross join warehouses w
),
...
sum(net_change) over (partition by sku, warehouse_code order by full_date
                      rows between unbounded preceding and current row) as quantity_on_hand
```

Kích thước = số thực thể × số kỳ. 50.000 sản phẩm × 30 kho × 365 ngày ≈ 550 triệu dòng/năm. Lúc đó cân nhắc: snapshot theo tuần/tháng cho dữ liệu cũ, hoặc chỉ giữ dòng có tồn > 0.

### Measure semi-additive

`quantity_on_hand` cộng theo sản phẩm, theo kho được. **Không** cộng theo ngày:

| Câu hỏi | Đúng | Sai |
|---|---|---|
| Tồn kho toàn công ty ngày 05/03 | `sum(on_hand) where date = 05/03` | |
| Tồn kho tháng 3 | `on_hand` của **ngày cuối** tháng, hoặc `avg(on_hand)` các ngày | `sum(on_hand)` cả tháng |
| Nhập trong tháng 3 | `sum(quantity_in)` (flow → additive) | |

Một snapshot thường có cả 2 loại: **số dư** (semi-additive) và **dòng chảy trong kỳ** (additive: nhập, xuất).

### Dữ liệu trễ làm thay đổi quá khứ

Điều chỉnh kiểm kê **ngày 02/03** về kho ngày 04/03 (lab ngày 3) → tồn kho của 02/03, 03/03, 04/03 đều phải sửa.

| Cài đặt | Xử lý |
|---|---|
| `table` dựng lại toàn bộ | Tự đúng |
| Incremental (chỉ thêm ngày mới) | **Sai im lặng**. Phải tính lại từ `min(movement_date)` của các dòng mới nạp: `delete+insert` theo khoảng ngày đó, hoặc `insert_overwrite` các partition ngày bị ảnh hưởng (BigQuery, tuần 7) |

## So sánh nhanh 3 loại fact (bản đầy đủ)

| | Transaction | Periodic snapshot | Accumulating snapshot |
|---|---|---|---|
| Grain | 1 sự kiện | thực thể × kỳ | 1 vòng đời |
| Số dòng tăng theo | số sự kiện | số thực thể × số kỳ | số thực thể |
| Khoá ngày | 1 | 1 (ngày chụp) | nhiều (mỗi mốc) |
| Dòng cũ | không đổi | không đổi (trừ dữ liệu trễ) | **sửa** khi qua mốc |
| Measure điển hình | additive | semi-additive (số dư) + additive (dòng chảy) | lag, số lần, giá trị đơn |
| Ví dụ lab | `fct_sales` | `fct_inventory_daily` | `fct_order_fulfillment` |

## Lỗi hay gặp

- Accumulating snapshot để mốc chưa tới là `null` → join `dim_date` rơi dòng.
- Lag = 0 cho mốc chưa tới → kéo trung bình xuống.
- Tính mốc theo sự kiện **về kho sau cùng** thay vì **xảy ra sớm nhất**.
- Incremental chỉ nhìn sự kiện mới → xoá mất mốc cũ.
- Periodic snapshot thưa (chỉ ngày có biến động) → "tồn kho ngày X" không có câu trả lời.
- `sum` số dư theo thời gian.
- Snapshot incremental bỏ qua điều chỉnh lùi ngày.

## Áp dụng vào adventure_works

- [ ] `fct_order_fulfillment` (accumulating) từ `SalesOrderHeader`: `order_date_key`, `due_date_key`, `ship_date_key`, `days_to_ship`, cờ `is_shipped_late` (`ShipDate > DueDate`). Lưu ý dữ liệu AdventureWorks tĩnh: mốc đã đủ, nên cố ý thử thêm vài đơn chưa gửi (seed) để thấy dòng `-1`
- [ ] `fct_work_order` (accumulating) từ `Production.WorkOrder` (+ `WorkOrderRouting` nếu muốn mốc theo công đoạn): `start_date_key`, `end_date_key`, `due_date_key`, `scrapped_qty`
- [ ] `fct_inventory_daily` (periodic) từ `Production.TransactionHistory` (+ `TransactionHistoryArchive`): cộng dồn theo sản phẩm. Chọn khoảng ngày hợp lý để bảng không quá lớn trên Snowflake
- [ ] Ghi rõ trong description: measure nào semi-additive, phải tổng hợp theo thời gian thế nào

## Câu hỏi tự kiểm tra

1. Vì sao accumulating snapshot là loại fact duy nhất sửa dòng cũ?
2. Sự kiện về sai thứ tự xử lý thế nào để mốc luôn đúng?
3. Viết incremental cho accumulating snapshot: cần xử lý những đơn nào? Lỗi điển hình là gì?
4. Periodic snapshot "dày đặc" nghĩa là gì? Đánh đổi gì?
5. "Tồn kho tháng 3" tính thế nào? Vì sao không `sum`?
6. Điều chỉnh tồn kho lùi ngày ảnh hưởng gì tới snapshot incremental? Sửa thế nào?

## Tài liệu

- *The Data Warehouse Toolkit* — chương 4 (Inventory: periodic snapshot, transaction, accumulating snapshot, semi-additive), chương 6 (Order management: accumulating snapshot cho đường ống đơn hàng)
- Kimball Group — danh mục kỹ thuật, mục "Fact Table Techniques": https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- Lab: [K8, K9](../../bai-tap-kimball-data-vault/bai-tap/02-kimball-fact.md)
