# 4.1 Quy trình thiết kế 4 bước và grain

## Junior và Mid khác nhau ở đâu

| | Junior | Mid |
|---|---|---|
| Xuất phát điểm | Một yêu cầu báo cáo: "cho anh bảng doanh thu theo tháng" | Một **quy trình nghiệp vụ**: "bán hàng" |
| Kết quả | 1 bảng phục vụ đúng 1 báo cáo | 1 fact + các dimension dùng chung, trả lời được cả những báo cáo **chưa ai hỏi** |
| Khi có yêu cầu mới | Viết thêm bảng mới | Thường chỉ cần thêm cột hoặc viết query trên mô hình có sẵn |

Kimball gói cách nghĩ của Mid vào **4 bước**, làm **đúng thứ tự**.

## 4 bước thiết kế

```
1. Chọn QUY TRÌNH NGHIỆP VỤ   →  "bán hàng", không phải "báo cáo của phòng kinh doanh"
2. Khai báo GRAIN             →  "1 dòng = 1 dòng của một đơn hàng"
3. Xác định DIMENSION         →  ai, cái gì, ở đâu, khi nào, vì sao, bằng cách nào
4. Xác định FACT              →  các con số đúng ở grain đã khai báo
```

### Bước 1: chọn quy trình nghiệp vụ

Quy trình nghiệp vụ là một **hoạt động** mà tổ chức thực hiện và hệ thống nguồn ghi lại: nhận đơn, giao hàng, nhập kho, thanh toán, đặt chỉ tiêu. Mỗi quy trình thường thành **một fact table**.

Sai lầm hay gặp là chọn theo **phòng ban** ("mart cho phòng Marketing"). Một quy trình (bán hàng) phục vụ nhiều phòng; một phòng cần nhiều quy trình. Chia theo phòng ban dẫn tới nhiều bảng "doanh thu" với nhiều con số khác nhau.

### Bước 2: khai báo grain (quan trọng nhất)

**Grain** = một dòng trong fact table đại diện cho cái gì. Viết thành **một câu**, trước khi nghĩ tới cột:

| Fact | Grain |
|---|---|
| `fct_sales` | 1 dòng = 1 dòng đơn hàng (order line) |
| `fct_order_fulfillment` | 1 dòng = 1 đơn hàng, cập nhật khi đơn qua mốc mới |
| `fct_inventory_daily` | 1 dòng = 1 sản phẩm × 1 kho × 1 ngày |

Nguyên tắc: chọn **grain nguyên tử (atomic)**, tức mức chi tiết nhất nguồn cho phép. Lý do:
- Từ chi tiết luôn cộng lên được tổng; từ tổng không bao giờ tách lại được chi tiết.
- Người dùng sẽ hỏi những câu bạn không đoán trước ("doanh thu theo màu sản phẩm"). Grain chi tiết thì trả lời được.
- Bảng tổng hợp (aggregate) có thể làm **thêm** sau, từ fact nguyên tử, để tăng tốc.

Grain quyết định mọi thứ phía sau: dimension nào gắn được (phải **một giá trị** ở grain đó), measure nào hợp lệ.

### Bước 3: xác định dimension

Hỏi: ở grain này, **ai, cái gì, ở đâu, khi nào, vì sao, bằng cách nào**?

Dòng đơn hàng → khách nào, sản phẩm nào, ngày nào, kênh nào, khuyến mãi nào.

Kiểm tra: mỗi dimension phải có **đúng 1 giá trị** cho mỗi dòng fact. Một dòng đơn có 3 voucher → voucher **không** gắn thẳng vào fact được, cần **bridge table** (4.4).

### Bước 4: xác định fact

Fact là con số đo lường, **đúng ở grain**. Dòng đơn hàng có: số lượng, đơn giá, thành tiền, giảm giá phân bổ.

Con số không đúng grain → không đưa vào. Ví dụ "tổng tiền cả đơn" không thuộc grain dòng đơn (xem phần header/line bên dưới).

## Các loại fact table

| | Transaction | Periodic snapshot | Accumulating snapshot | Factless |
|---|---|---|---|---|
| Grain | 1 sự kiện | 1 thực thể × 1 kỳ (ngày/tháng) | 1 vòng đời của 1 thực thể (đơn, hồ sơ) | 1 sự kiện / 1 tình trạng phủ |
| Ví dụ | dòng đơn, giao dịch ngân hàng | tồn kho cuối ngày, số dư tài khoản cuối tháng | đơn hàng từ đặt → giao → trả | điểm danh, sản phẩm được khuyến mãi |
| Khoá ngày | 1 | 1 (ngày chụp) | **nhiều** (mỗi mốc 1 khoá) | 1 hoặc nhiều |
| Dòng cũ có bị sửa? | Không | Không (kỳ mới = dòng mới) | **Có**, mỗi khi qua mốc | Không |
| Mật độ | Thưa (chỉ khi có sự kiện) | **Dày** (mọi kỳ đều có dòng) | 1 dòng / thực thể | Thưa |
| Chi tiết | | 4.6 | 4.6 | 4.5 |

Ba loại đầu **bổ sung** nhau, không thay nhau. Kho của Mây Shop dùng cả bốn.

## Tính cộng dồn của measure

| Loại | Cộng được theo | Ví dụ | Cách tổng hợp đúng |
|---|---|---|---|
| **Additive** | mọi dimension | doanh thu, số lượng | `sum` |
| **Semi-additive** | một số dimension, **không** theo thời gian | tồn kho, số dư | theo thời gian dùng `avg` hoặc lấy giá trị **cuối kỳ** |
| **Non-additive** | không dimension nào | đơn giá, tỷ lệ %, biên lợi nhuận | lưu **tử số và mẫu số** riêng, tính tỷ lệ sau khi tổng hợp |

Ví dụ lỗi kinh điển: cộng tồn kho 7 ngày ra "tồn kho tuần". Hay lấy `avg(tỷ lệ chuyển đổi)` của các ngày thay vì `sum(đơn) / sum(lượt xem)`.

## Đầu đơn (header) và dòng đơn (line)

Nhiều con số nằm ở cấp **đầu đơn**: phí ship, voucher, thuế. Fact ở grain dòng đơn có 2 lựa chọn:

| Cách | Mô tả | Khi nào |
|---|---|---|
| **Phân bổ** (allocation) | Chia số đầu đơn xuống từng dòng theo tỷ trọng (thường theo thành tiền) | Khi nghiệp vụ chấp nhận được quy tắc phân bổ. Phổ biến nhất |
| **Fact riêng ở grain đầu đơn** | `fct_orders` 1 dòng / đơn giữ nguyên phí ship, voucher | Khi không ai đồng ý được cách chia |

Điều **không** được làm: lặp nguyên số đầu đơn ở mọi dòng. Đơn 3 dòng, phí ship 30.000 → `sum` ra 90.000.

Phân bổ phải **khớp từng đồng**: làm tròn từng dòng thì tổng có thể lệch 1 đồng. Cách xử lý chuẩn: dòng cuối nhận **phần còn lại** (tổng đầu đơn trừ tổng các dòng trước). Viết test đối soát `sum(dòng) = đầu đơn`.

```sql
case when not is_last_line
     then round(order_discount_total * gross_amount / order_gross_amount) end   as discount_part
...
coalesce(discount_part,
         order_discount_total - sum(discount_part) over (partition by order_number)) as discount_allocated
```

## Grain bị trộn (mixed grain)

Lỗi nặng nhất của fact table: **hai grain trong một bảng**.

| Biểu hiện | Hậu quả |
|---|---|
| Fact dòng đơn có thêm vài dòng "phí ship" với `product_key = null` | `count(*)` không còn là số dòng hàng; join sản phẩm làm rơi tiền ship |
| Fact theo ngày có thêm dòng "tổng tháng" | Cộng theo tháng ra gấp đôi |
| Gộp đơn hàng và dòng đơn vào 1 bảng, phân biệt bằng cột `row_type` | Mọi query phải nhớ `where row_type = ...`, sớm muộn có người quên |

Cách tránh: viết grain vào `description`, thêm test unique trên đúng tổ hợp cột của grain.

## Khai báo grain trong dbt

```yaml
models:
  - name: fct_sales
    description: >
      Transaction fact. GRAIN: 1 dòng = 1 dòng đơn online hoặc 1 dòng hoá đơn POS đã bán.
      Đơn huỷ không có mặt. Phí ship và voucher của đơn được phân bổ xuống dòng theo thành tiền.
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns: [order_number, line_no]
```

Test unique trên grain là test **quan trọng nhất** của một fact. Nó bắt được fan-out khi join sai (GĐ1, bài B6).

## Lỗi hay gặp

- Bắt đầu từ cột ("mình có những cột này") thay vì từ grain.
- Chọn grain đã tổng hợp sẵn ("doanh thu theo ngày theo sản phẩm") rồi sau đó không trả lời được câu hỏi theo khách.
- Gắn dimension nhiều giá trị thẳng vào fact → nhân dòng.
- Lưu tỷ lệ, đơn giá rồi `sum` chúng.
- Lặp số đầu đơn xuống mọi dòng.
- Không có test unique trên grain.

## Áp dụng vào adventure_works

AdventureWorks có đủ chất liệu cho cả 4 loại fact:

| Quy trình | Bảng nguồn | Grain gợi ý | Loại |
|---|---|---|---|
| Bán hàng | `Sales.SalesOrderHeader` + `SalesOrderDetail` | 1 dòng đơn | transaction |
| Thực hiện đơn | `SalesOrderHeader` (`OrderDate`, `ShipDate`, `DueDate`, `Status`) | 1 đơn | accumulating snapshot |
| Sản xuất | `Production.WorkOrder` (`StartDate`, `EndDate`, `DueDate`) | 1 lệnh sản xuất | accumulating snapshot |
| Tồn kho | `Production.TransactionHistory` (+ `ProductInventory`) | 1 sản phẩm × 1 ngày | periodic snapshot |
| Chỉ tiêu | `Sales.SalesPersonQuotaHistory` | 1 nhân viên × 1 quý | periodic snapshot |
| Khuyến mãi | `Sales.SpecialOfferProduct` + `SpecialOffer` | 1 khuyến mãi × 1 sản phẩm × 1 ngày | factless |

- [ ] Viết grain cho từng fact hiện có vào `description`, thêm test unique đúng grain
- [ ] `fct_sales`: phân bổ `Freight` và `TaxAmt` của `SalesOrderHeader` xuống dòng, có test đối soát với `TotalDue`
- [ ] Rà lại: có measure non-additive nào đang bị `sum` trên dashboard không? (gợi ý: `UnitPriceDiscount` là tỷ lệ)

## Câu hỏi tự kiểm tra

1. Kể 4 bước thiết kế theo đúng thứ tự. Vì sao grain phải đứng trước dimension và fact?
2. "Atomic grain" là gì? Vì sao không nên chọn grain đã tổng hợp?
3. So sánh transaction, periodic snapshot, accumulating snapshot về grain, khoá ngày, việc sửa dòng cũ.
4. Measure semi-additive là gì? Cho 2 ví dụ và cách tổng hợp đúng theo thời gian.
5. Đơn có phí ship 30.000 và 3 dòng. Bạn đưa phí ship vào fact dòng đơn thế nào để tổng vẫn đúng 30.000?
6. Mixed grain là gì? Làm sao phát hiện bằng test?

## Tài liệu

- Kimball & Ross, *The Data Warehouse Toolkit* (3rd ed.) — chương 1–3 (đặc biệt chương 3: Retail Sales, quy trình 4 bước)
- Kimball Group — Four-Step Dimensional Design Process: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/four-4-step-design-process/
- Kimball Group — danh mục kỹ thuật mô hình hoá: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- Lab: [K1, K5](../../bai-tap-kimball-data-vault/bai-tap/01-kimball-thiet-ke-va-dimension.md)
