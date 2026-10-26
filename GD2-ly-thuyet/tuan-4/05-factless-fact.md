# 4.5 Factless fact: ghi nhận sự kiện và "cái gì KHÔNG xảy ra"

## Khái niệm

**Factless fact table** là fact không có cột số đo nào. Chỉ có các khoá dimension. Bản thân việc **một dòng tồn tại** đã là thông tin.

Hai loại:

| Loại | Ghi nhận | Ví dụ |
|---|---|---|
| **Event tracking** (theo dõi sự kiện) | Một sự kiện đã xảy ra, không có con số đi kèm | Học sinh có mặt buổi học; khách xem trang sản phẩm; nhân viên tham gia khoá đào tạo |
| **Coverage** (phủ, điều kiện) | Một tình trạng / điều kiện **đang có hiệu lực**, dù có sự kiện nào xảy ra hay không | Sản phẩm đang được khuyến mãi; nhân viên được phân công phụ trách khu vực; phòng học được xếp lịch |

Đo bằng **đếm**: `count(*)`, `count(distinct ...)`. Một số nhóm thêm cột hằng `= 1` (vd `coverage_count`) cho BI dễ `sum`, đó là quy ước, không phải measure thật.

## Event tracking

```
fct_page_view (date_key, customer_key, product_key, channel_key)    ← mỗi lượt xem 1 dòng
```

Trả lời: "Sản phẩm nào được xem nhiều nhất tuần này?", "Bao nhiêu khách xem nhưng không mua?" (kết hợp với `fct_sales`).

Trong thực tế, rất nhiều bảng event (clickstream, log đăng nhập) chính là factless event tracking.

## Coverage: bài toán "cái gì KHÔNG xảy ra"

Câu hỏi: *"Sản phẩm nào đang khuyến mãi mà **không bán được**?"*

`fct_sales` không trả lời được: sản phẩm không bán thì **không có dòng nào** trong `fct_sales`. Bạn không thể tìm thứ không tồn tại.

Lời giải: một fact ghi nhận **điều kiện** (sản phẩm X được khuyến mãi ngày Y), rồi **trừ** đi những gì đã xảy ra:

```
coverage (được KM)   −   sales (đã bán)   =   KM mà không bán được
```

```sql
-- fct_promotion_coverage: 1 chương trình × 1 sản phẩm × 1 ngày
select d.date_key, p.product_key, pr.promotion_key
from {{ ref('stg_erp__promotions') }} s
join {{ ref('dim_date') }} d on d.full_date between s.start_date and s.end_date
join {{ ref('dim_product') }} p on p.sku = s.sku
join {{ ref('dim_promotion') }} pr on pr.promo_code = s.promo_code
```

```sql
-- rpt_promo_no_sales
select c.date_key, p.sku, pr.promo_code
from {{ ref('fct_promotion_coverage') }} c
join ... 
where not exists (
    select 1 from {{ ref('fct_sales') }} s
    where s.product_key = c.product_key and s.order_date_key = c.date_key
)
```

Các câu hỏi tương tự chỉ coverage trả lời được:
- Nhân viên được phân công khu vực nào mà **không có đơn** nào trong quý?
- Học sinh **vắng** buổi nào? (lịch học = coverage, điểm danh = event)
- Cửa hàng nào **có hàng** mà không bán được? (tồn kho cuối ngày đóng vai coverage)

## Coverage hay thêm cờ vào fact?

Một cách tắt: thêm `promotion_key` vào `fct_sales` (dòng bán đang được KM nào). Cách này đủ cho "doanh thu theo khuyến mãi" nhưng **không** trả lời được "KM mà không bán được". Thực tế dùng **cả hai**:
- `fct_sales.promotion_key` → hiệu quả của khuyến mãi trên các đơn đã bán.
- `fct_promotion_coverage` → phạm vi khuyến mãi, kể cả phần không ra đơn.

## Dữ liệu trễ và câu hỏi "không xảy ra"

Câu "không bán được" rất nhạy với **dữ liệu đến muộn**. Trong lab, POS đồng bộ 2 ngày một lần: ngày 1 báo cáo nói SKU03 ngày 02/03 không bán được, sang ngày 2 hoá đơn cửa hàng về, dòng đó biến mất.

Thực hành tốt:
- Ghi rõ trên báo cáo: "dữ liệu cửa hàng có độ trễ tới 2 ngày".
- Chỉ kết luận "không bán được" cho các ngày đã **đủ dữ liệu** (vd ngày ≤ hôm nay − độ trễ tối đa).
- Dùng **freshness** của source (GĐ1, 3.6) để biết độ trễ thật.

## Lỗi hay gặp

- Cố trả lời "cái gì không xảy ra" từ transaction fact.
- Coverage chỉ sinh cho ngày **đã qua** → không xem được kế hoạch KM tuần tới. (Tuỳ nhu cầu: coverage có thể gồm cả ngày tương lai, báo cáo tự lọc.)
- Không tính tới dữ liệu trễ khi kết luận "không xảy ra".
- Coverage dựng incremental mà nguồn đổi khoảng ngày (gia hạn KM) → dòng của ngày gia hạn không bao giờ được thêm.

## Áp dụng vào adventure_works

- [ ] `fct_special_offer_coverage` từ `Sales.SpecialOffer` (`StartDate`, `EndDate`) × `Sales.SpecialOfferProduct` × `dim_date`
- [ ] Báo cáo "sản phẩm có khuyến mãi mà không bán được theo tháng". Lưu ý dữ liệu AdventureWorks kéo dài nhiều năm → coverage theo **tháng** có thể hợp lý hơn theo ngày (cân nhắc grain!)
- [ ] (Tuỳ chọn) event tracking: `Sales.SalesOrderHeaderSalesReason` thực chất cũng là factless (đơn × lý do)

## Câu hỏi tự kiểm tra

1. Factless fact là gì? Hai loại khác nhau thế nào?
2. Vì sao "sản phẩm KM mà không bán được" không trả lời được bằng `fct_sales`?
3. Viết khung SQL trả lời câu đó bằng coverage + sales.
4. Đếm trên factless fact dùng hàm gì? Cột `= 1` có phải measure không?
5. Dữ liệu trễ ảnh hưởng thế nào tới báo cáo "không xảy ra"? Bạn xử lý ra sao?

## Tài liệu

- *The Data Warehouse Toolkit* — chương 3 (Retail sales: promotion coverage factless fact), chương 13 (Education: attendance event tracking)
- Kimball Group — danh mục kỹ thuật, mục "Factless Fact Tables": https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- Lab: [K10](../../bai-tap-kimball-data-vault/bai-tap/03-kimball-nang-cao.md)
