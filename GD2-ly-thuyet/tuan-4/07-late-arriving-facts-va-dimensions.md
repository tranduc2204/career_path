# 4.7 Late-arriving facts và late-arriving dimensions

> GĐ1 (2.2) đã xử lý dữ liệu đến muộn ở góc độ **kỹ thuật incremental** (lookback, backfill). File này nhìn từ góc độ **mô hình**: dữ liệu trễ làm sai **khoá dimension** và các **snapshot** thế nào.

## Hai bài toán ngược chiều nhau

| | Late-arriving **fact** | Late-arriving **dimension** (= early-arriving fact) |
|---|---|---|
| Chuyện gì | Sự kiện xảy ra lâu rồi mới về kho | Fact về kho **trước** khi dimension của nó tồn tại |
| Ví dụ lab | Hoá đơn POS ngày 01/03 tới sáng 04/03 (ngày 2 của lab) mới về kho | Đơn W0015 của C013 về ở ngày 2, CRM có C013 từ ngày 3 |
| Rủi ro | Gắn **sai phiên bản** dimension (phiên bản hiện tại thay vì lúc phát sinh) | **Không có** dòng dimension để gắn → rơi dòng hoặc rơi vào `-1` |
| Lời giải chính | Join theo **thời điểm phát sinh** | **Inferred member** |

## Phần 1. Late-arriving fact

### Gắn đúng phiên bản dimension

Nguyên tắc: phiên bản dimension được chọn theo **thời điểm nghiệp vụ của fact** (`order_ts`, `sale_ts`), không theo lúc dữ liệu về, không theo `is_current`.

```sql
left join {{ ref('dim_customer') }} c
    on  c.customer_code = a.customer_code
    and a.order_ts >= c.valid_from
    and a.order_ts <  c.valid_to
```

Hoá đơn HN-0003 (C003 mua 01/03, sáng 04/03 mới về kho) → phiên bản Ha Noi, dù lúc dữ liệu về C003 đã ở Da Nang.

Với fact `table` dựng lại mỗi lần chạy, chỉ cần join đúng là xong. Với fact **incremental**:
- Watermark theo `_loaded_at` (lúc về kho) → dòng trễ vẫn được nạp ✅, nhưng join phải theo `sale_ts`.
- Watermark theo `sale_ts` + lookback N ngày → dòng trễ hơn N ngày bị **bỏ sót** ❌ (GĐ1, bài I6 và sự cố P5).

### Dữ liệu trễ làm đổi số đã báo cáo

Doanh thu ngày 01/03 báo cáo sáng 02/03 khác báo cáo sáng 04/03 (thêm POS). Đây là đúng, nhưng phải được quản lý:
- **Ghi rõ độ trễ** của từng nguồn trên dashboard ("cửa hàng: trễ tối đa 2 ngày").
- **Khoá sổ**: kế toán chốt số tháng vào ngày X. Dữ liệu trễ sau ngày chốt → ghi vào kỳ sau dưới dạng điều chỉnh, hoặc mở sổ có kiểm soát. Đây là **quyết định nghiệp vụ**, AE không tự quyết.
- **Snapshot báo cáo**: lưu bản chụp số liệu đã gửi (vd `rpt_revenue_daily_published`) để trả lời "hôm đó chúng ta đã báo con số nào".

### Ảnh hưởng tới các loại fact

| Fact | Dữ liệu trễ làm gì |
|---|---|
| Transaction | Thêm dòng cho ngày cũ |
| Periodic snapshot | **Mọi** kỳ từ ngày phát sinh tới nay phải tính lại (tồn kho 02/03, 03/03, 04/03...) |
| Accumulating snapshot | Một mốc được điền muộn, có thể **trước** mốc đã có (W0006: `shipped` về sau `delivered`) |
| Bảng tổng hợp (aggregate) | Các bucket ngày cũ phải cập nhật |

## Phần 2. Late-arriving dimension

### Các lựa chọn

| Cách | Làm gì | Ưu | Nhược |
|---|---|---|---|
| **A. Gán `-1`, sửa sau** | Fact trỏ vào thành viên "không xác định". Khi dimension tới, cập nhật lại khoá trong fact | Đơn giản | Doanh thu của khách nằm ở "không xác định" một thời gian. Fact incremental phải có job "gán lại khoá" |
| **B. Giữ fact chờ** (suspense) | Fact chưa có dimension nằm ở bảng chờ, chưa vào fact chính | Fact luôn "sạch" | Doanh thu **thiếu** trong lúc chờ. Dễ quên bảng chờ |
| **C. Inferred member** | Tạo ngay 1 dòng dimension cho mã mới với thuộc tính "Chưa xác định". Khi dimension tới, **ghi đè chính dòng đó** | Doanh thu đủ, gắn đúng khách ngay từ đầu, fact không phải đổi khoá | Cần thiết kế khoá cẩn thận |

Kimball khuyến nghị **C** cho phần lớn trường hợp.

### Inferred member chi tiết

```
Ngày 2: CRM chưa có C013, đơn W0015 về
  dim_customer: C013 | Chưa xác định | Chưa xác định | 1900-01-01 → 9999-12-31 | is_inferred = true
  fct_sales:    W0015 → customer_key = hash('C013', '1900-01-01')

Ngày 3: CRM có C013 (Ho Chi Minh, Member)
  dim_customer: C013 | Ho Chi Minh | Member | 1900-01-01 → ... | is_inferred = false   ← CÙNG khoá
  fct_sales:    W0015 → vẫn hash('C013', '1900-01-01') → giờ trỏ vào dữ liệu thật
```

3 điểm then chốt:
1. **Ghi đè dòng inferred là Type 1**, không phải Type 2. Thuộc tính "Chưa xác định" chưa bao giờ đúng, không phải lịch sử cần giữ.
2. **Khoá phải ổn định**: hash từ `(customer_code, valid_from)` với phiên bản đầu luôn bắt đầu từ `1900-01-01`. Nếu phiên bản đầu bắt đầu từ ngày file CRM đầu tiên (04/03), khoá đổi → fact incremental trỏ vào khoảng không.
3. **Cờ `is_inferred`** để theo dõi: số khách inferred tăng bất thường = nguồn dimension đang trễ hoặc lỗi. Viết test `warn`.

### Khi dùng dbt (fact là `table` hay incremental)

| Fact | Cần làm gì thêm |
|---|---|
| `table` (dựng lại mỗi lần) | Không cần gì: mỗi lần chạy join lại từ đầu |
| Incremental | Khoá phải ổn định (điểm 2 ở trên). Hoặc mỗi lần chạy **xử lý lại** các dòng đang trỏ vào inferred / `-1` (thử thách C1 của lab) |

### Data Vault làm việc này thế nào

Trong Data Vault, hub nhận business key từ **mọi** nguồn: đơn hàng mang theo `customer_code` → `hub_customer` có C013 ngay từ ngày 2, dù satellite CRM chưa có dòng nào. Information mart nhìn "hub có, satellite chưa có" là biết đó là inferred member. Bạn sẽ thấy ở bài V8.

## Lỗi hay gặp

- Join dimension SCD2 theo `is_current` cho dữ liệu lịch sử → dòng trễ mang thuộc tính hiện tại.
- `inner join` dimension → dòng của khách chưa có trong dimension biến mất khỏi fact.
- Phiên bản thật đầu tiên tạo khoá mới, bỏ rơi dòng inferred → 2 khoá cho cùng 1 khách.
- Không theo dõi số inferred member → dimension nguồn chết cả tuần không ai biết.
- Periodic snapshot incremental không tính lại kỳ cũ khi có dữ liệu trễ.
- Tự ý sửa số liệu tháng đã khoá sổ.

## Áp dụng vào adventure_works

Dữ liệu AdventureWorks tĩnh, nên phải **giả lập**:

- [ ] Tạo seed `late_orders.csv` gồm vài đơn có `OrderDate` cũ và một `CustomerID` chưa có trong `Sales.Customer`. Union vào staging đơn hàng (đánh dấu nguồn)
- [ ] `dim_customer`: inferred member cho mọi khách có trong đơn mà chưa có trong dimension, cờ `is_inferred`, khoá ổn định
- [ ] Test `warn` khi số khách inferred > 0, ghi chú cách xử lý trong README
- [ ] Viết 1 đoạn trong README: chính sách xử lý dữ liệu trễ (độ trễ chấp nhận được, khoá sổ, ai quyết định)

## Câu hỏi tự kiểm tra

1. Late-arriving fact và late-arriving dimension khác nhau thế nào? Cho ví dụ mỗi loại.
2. Fact đến trễ 3 ngày, dimension là SCD2: join thế nào để gắn đúng phiên bản?
3. Kể 3 cách xử lý dimension đến trễ. Vì sao Kimball chọn inferred member?
4. Vì sao ghi đè dòng inferred là Type 1?
5. Thiết kế khoá thế nào để inferred member và phiên bản thật đầu tiên trùng khoá?
6. Dữ liệu trễ ảnh hưởng gì tới periodic snapshot và accumulating snapshot?
7. Kế toán đã khoá sổ tháng 2, hôm nay có 5 hoá đơn tháng 2 về. Bạn làm gì?

## Tài liệu

- *The Data Warehouse Toolkit* — chương 19 (ETL subsystems: late arriving data handler), chương 5 (SCD)
- Kimball Group — Design Tip "Late Arriving Dimension Rows" và các bài về *inferred members* (tìm trên kimballgroup.com)
- GĐ1: [2.2 late-arriving data và backfill](../../GD1-ly-thuyet/tuan-2/02-late-arriving-data-va-backfill.md)
- Lab: [K6, K7](../../bai-tap-kimball-data-vault/bai-tap/02-kimball-fact.md), [V8](../../bai-tap-kimball-data-vault/bai-tap/05-data-vault-business-vault-va-mart.md)
