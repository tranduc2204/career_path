# 4.3 Kỹ thuật dimension: khoá, thành viên đặc biệt, role-playing, junk, degenerate, mini-dimension, SCD 0–7

> GĐ1 (2.3) đã học SCD Type 2 bằng snapshot. File này tổng hợp các kỹ thuật dimension còn lại mà phỏng vấn Mid hay hỏi.

## Surrogate key, natural key, durable key

| Loại khoá | Là gì | Ví dụ |
|---|---|---|
| **Natural key** (business key) | Khoá của hệ thống nguồn | `customer_code = 'C003'` |
| **Surrogate key** | Khoá của kho, **mỗi dòng dimension** một giá trị | `customer_key = md5('C003' + '2026-03-02')` (phiên bản Da Nang) |
| **Durable key** | Định danh **thực thể** ổn định qua mọi phiên bản (thường chính là natural key đã chuẩn hoá) | `C003` |

Vì sao fact trỏ vào surrogate key chứ không phải natural key:
- Dimension SCD2 có **nhiều dòng** cho 1 natural key. Surrogate key chỉ đúng **một phiên bản**.
- Tách kho khỏi hệ thống nguồn: nguồn đổi mã, dùng lại mã cũ, 2 nguồn trùng mã → kho không vỡ.
- Có chỗ cho thành viên đặc biệt (`-1`, `-2`).

Trong dbt thường dùng `dbt_utils.generate_surrogate_key([...])` (hash), không dùng số tự tăng: hash **tính lại được** mỗi lần build, không phụ thuộc thứ tự chạy. Điều kiện: các cột đưa vào hash phải **ổn định**. Ví dụ `['customer_code', 'valid_from']` chỉ ổn định nếu `valid_from` của một phiên bản không bao giờ đổi (xem 4.7 inferred member).

## Thành viên đặc biệt (special members)

| Khoá | Ý nghĩa | Ví dụ |
|---|---|---|
| `-1` | **Không xác định** (unknown): có giá trị nhưng kho không biết | khách vãng lai, sản phẩm có mã lạ |
| `-2` | **Không áp dụng** (not applicable): khái niệm không tồn tại cho dòng này | đơn online không có cửa hàng; đơn không dùng voucher |
| `-1` trong `dim_date` | **Chưa xảy ra** | đơn chưa giao → `delivered_date_key = -1` |

Lý do: khoá ngoại trong fact **không bao giờ null**. Null làm `inner join` rơi dòng, BI đếm sai, người dùng thấy ô trống không hiểu nghĩa. Dòng đặc biệt hiện ra chữ rõ ràng ("Khách vãng lai", "Chưa xảy ra").

## Date dimension và role-playing

`dim_date` gần như dự án nào cũng có. Cột hay dùng: khoá `yyyymmdd`, thứ trong tuần, cuối tuần, tuần ISO, tháng, quý, năm, ngày đầu tháng; thêm **ngày lễ / Tết**, mùa sale (11.11, 12.12), kỳ kế toán nếu công ty dùng năm tài chính khác năm dương lịch.

Vì sao không dùng thẳng hàm ngày của SQL? Thuộc tính nghiệp vụ (ngày lễ, kỳ kế toán, "tuần bán hàng") không tính được bằng hàm, và BI cần cột để kéo thả.

**Role-playing dimension**: một dimension vật lý, nhiều vai trong cùng fact.

```
fct_order_fulfillment.order_date_key     ─┐
fct_order_fulfillment.shipped_date_key   ─┼──▶ dim_date (1 bảng)
fct_order_fulfillment.delivered_date_key ─┘
```

Trong BI (Power BI, Looker...) thường tạo **view theo vai** (`dim_order_date`, `dim_delivery_date`) với tên cột có tiền tố, để kéo 2 vai vào cùng 1 báo cáo không bị nhầm.

## Degenerate dimension

Mã giao dịch (số đơn, số hoá đơn, số vận đơn) nằm **trong fact**, không có bảng dimension riêng vì không còn thuộc tính nào khác (thuộc tính của đơn đã là các dimension khác).

Công dụng: gom các dòng của cùng một đơn (`count(distinct order_number)`), truy ngược về hệ thống nguồn, làm group key cho bridge (4.4).

## Junk dimension

Fact thường có nhiều **cờ, mã trạng thái ít giá trị**: kênh bán, phương thức thanh toán, có phải quà tặng, có xuất hoá đơn đỏ...

| Cách | Vấn đề |
|---|---|
| Để rời trong fact | Fact phình cột, ý nghĩa mã khó hiểu |
| Mỗi cờ một dimension | Nhiều dimension tí hon, fact nhiều khoá |
| **Junk dimension** | 1 dimension chứa các **tổ hợp** cờ; fact mang 1 khoá |

```sql
-- dim_order_profile: chỉ các tổ hợp thực sự xuất hiện
select {{ dbt_utils.generate_surrogate_key(['channel', 'payment_method', 'is_gift']) }} as order_profile_key,
       channel, payment_method, is_gift
from (select distinct channel, payment_method, is_gift from {{ ref('int_sales__lines') }})
```

Có thể sinh **mọi tổ hợp** (cross join) nếu số tổ hợp nhỏ, hoặc chỉ tổ hợp xuất hiện nếu lớn.

## Mini-dimension (SCD Type 4)

Khi một vài thuộc tính đổi **rất thường xuyên** (hạng thành viên, nhóm tuổi, nhóm thu nhập, điểm tín dụng), SCD2 làm dimension phình to (gọi là *rapidly changing monster dimension*).

Giải pháp: tách các thuộc tính đó ra **mini-dimension** gồm các **dải giá trị** (band), fact mang **cả 2 khoá**:

```
dim_customer (thuộc tính ổn định)         dim_customer_profile (mini-dimension: tier × nhóm tuổi × nhóm chi tiêu)
         ▲                                          ▲
         └──────────── fct_sales ───────────────────┘   (customer_key, customer_profile_key)
```

Mini-dimension chỉ vài chục, vài trăm dòng (số tổ hợp dải). Lịch sử "khách thuộc nhóm nào lúc mua" nằm ở **fact**.

## Outrigger và snowflaking

- **Snowflaking**: tách thuộc tính phân cấp của dimension ra bảng riêng (sản phẩm → danh mục → ngành hàng). Kimball khuyên **không** làm với dimension thông thường: BI phải join nhiều, chậm, khó hiểu. Nên **làm phẳng** vào `dim_product` (`category_name`, `category_l1_name`).
- **Outrigger**: ngoại lệ được chấp nhận. Một dimension trỏ tới dimension khác, thường là ngày (`dim_customer.first_purchase_date_key → dim_date`). Dùng tiết chế.

## Các loại SCD (0–7)

| Loại | Cách làm | Lịch sử | Khi dùng |
|---|---|---|---|
| **0** | Giữ giá trị ban đầu, không bao giờ đổi | Giá trị gốc | Ngày sinh, ngày tạo tài khoản, phân khúc lúc đăng ký |
| **1** | Ghi đè | ❌ | Sửa lỗi chính tả, thuộc tính không cần lịch sử |
| **2** | Thêm dòng mới, đóng dòng cũ (`valid_from`, `valid_to`) | ✅ đầy đủ | Thuộc tính ảnh hưởng phân tích theo thời gian (thành phố, hạng) |
| **3** | Thêm cột "giá trị trước đó" | 1 bước | Đổi tổ chức lớn, muốn báo cáo song song cũ/mới |
| **4** | Mini-dimension cho thuộc tính đổi nhanh | ✅ (qua fact) | Hạng, nhóm tuổi đổi liên tục |
| **5** | 4 + outrigger Type 1 trỏ tới mini-dimension **hiện tại** | ✅ | Cần cả "lúc đó" và "hiện tại" của mini-dimension |
| **6** | 1 + 2 + 3: dimension Type 2 có thêm cột **giá trị hiện tại** (Type 1) ở mọi phiên bản | ✅ | Báo cáo theo "thành phố lúc mua" **và** "thành phố hiện tại" trong 1 query |
| **7** | Fact mang **cả** surrogate key (Type 2) **và** durable key (để join view Type 1 hiện tại) | ✅ | Linh hoạt nhất, BI tự chọn góc nhìn |

Thực tế một dimension thường là **lai**: một số cột Type 1, một số Type 2. `dim_customer` của lab: `full_name`, `email` Type 1 (mọi phiên bản mang giá trị mới nhất); `city`, `loyalty_tier` Type 2.

### Dựng SCD2 trong dbt: 3 nguồn lịch sử

| Nguồn có gì | Cách dựng | Dựng lại từ đầu được không |
|---|---|---|
| Chỉ trạng thái hiện tại (ghi đè) | `dbt snapshot` (GĐ1) | ❌ lịch sử bỏ lỡ là mất |
| File full hằng ngày được giữ lại | So 2 file liên tiếp bằng `lag()` (lab K4) | ✅ |
| CDC log (insert/update/delete) | Dựng từ log (GĐ1, bài S8) | ✅, chính xác tới từng giây |

## Lỗi hay gặp

- Fact trỏ vào natural key của dimension SCD2 → nhân dòng hoặc mất lịch sử.
- Khoá ngoại null thay vì `-1` / `-2`.
- Mỗi cờ một dimension riêng, fact 15 khoá.
- SCD2 cho cả cột sửa lỗi (email) → phiên bản rác.
- Snowflake hoá mọi phân cấp → BI phải join 5 bảng để lọc theo ngành hàng.
- Surrogate key hash từ cột có thể đổi giá trị → khoá đổi, fact cũ trỏ vào khoảng không.

## Áp dụng vào adventure_works

- [ ] `dim_date` thêm cột năm tài chính (AdventureWorks dùng FY bắt đầu tháng 7), ngày lễ VN tự thêm bằng seed
- [ ] Role-playing: `fct_sales` có `order_date_key`, `due_date_key`, `ship_date_key`; tạo view theo vai cho BI
- [ ] Junk dimension từ `OnlineOrderFlag`, `Status`, `ShipMethodID` của `SalesOrderHeader`
- [ ] `SalesOrderNumber`, `PurchaseOrderNumber` làm degenerate dimension
- [ ] Thành viên `-1` / `-2` cho mọi dimension, test `not_null` trên mọi khoá ngoại của fact
- [ ] Phân loại từng cột `dim_customer` / `dim_product`: Type 0, 1 hay 2? Ghi lý do vào description

## Câu hỏi tự kiểm tra

1. Surrogate key, natural key, durable key khác nhau thế nào? Vì sao fact dùng surrogate key?
2. `-1` và `-2` khác nhau thế nào? Cho ví dụ.
3. Role-playing dimension là gì? Trong BI xử lý thế nào?
4. Khi nào dùng junk dimension? Nên sinh mọi tổ hợp hay chỉ tổ hợp xuất hiện?
5. Mini-dimension giải quyết vấn đề gì?
6. SCD Type 6 là gì? Viết câu SQL doanh thu theo thành phố lúc mua và theo thành phố hiện tại.
7. Vì sao hash surrogate key phải dựa trên cột ổn định?

## Tài liệu

- *The Data Warehouse Toolkit* — chương 2 (tóm tắt mọi kỹ thuật), chương 5 (Procurement: SCD 0–7, mini-dimension), chương 6 (Order management: role-playing, junk, degenerate)
- Kimball Group — danh mục kỹ thuật (mục "Dimension Table Techniques" và "Dealing with Slowly Changing Dimension Attributes"): https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- Lab: [K2, K3, K4](../../bai-tap-kimball-data-vault/bai-tap/01-kimball-thiet-ke-va-dimension.md), [K5](../../bai-tap-kimball-data-vault/bai-tap/02-kimball-fact.md)
