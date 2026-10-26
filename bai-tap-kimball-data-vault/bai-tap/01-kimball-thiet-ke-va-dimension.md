# 01 — Kimball: thiết kế và dimension (K1–K4)

> Lý thuyết: [4.1 quy trình 4 bước & grain](../../GD2-ly-thuyet/tuan-4/01-quy-trinh-4-buoc-va-grain.md) · [4.2 bus matrix](../../GD2-ly-thuyet/tuan-4/02-bus-matrix-va-conformed-dimension.md) · [4.3 kỹ thuật dimension](../../GD2-ly-thuyet/tuan-4/03-ky-thuat-dimension.md)

**Tình huống:** bạn vừa được giao dựng kho dữ liệu cho Mây Shop. Staging đã có. Trưởng nhóm dặn: *"Đừng viết SQL vội. Vẽ ra mình có những quy trình nghiệp vụ nào, mỗi quy trình đo ở grain nào, rồi mới làm dimension dùng chung trước."*

Làm ở **ngày 0** là đủ cho K1–K3. K4 làm ở ngày 0, sang các ngày sau chấm lại.

⭐ cơ bản · ⭐⭐ trung bình · ⭐⭐⭐ khá · ⭐⭐⭐⭐ nâng cao

---

## K1 ⭐ Khảo sát nguồn và thiết kế trên giấy (không chấm)

**Bước 1: xem dữ liệu.**

```bash
dbt show --inline "select * from {{ ref('stg_shop__orders') }}" --limit 10
dbt show --inline "select * from {{ ref('stg_crm__customers') }} where customer_code in ('C001','C003') order by customer_code, extract_date"
dbt show --inline "select * from {{ ref('stg_wms__shipment_events') }} order by order_number, event_ts" --limit 20
dbt show --inline "select * from {{ ref('stg_wms__stock_movements') }}" --limit 20
dbt show --inline "select * from {{ ref('stg_erp__sales_targets') }}"
```

**Bước 2: trả lời (ghi vào `lab/NOTES.md`).**
1. Liệt kê các **quy trình nghiệp vụ** (business process) mà dữ liệu này đo được. Gợi ý: có 5.
2. Với mỗi quy trình, **khai báo grain** bằng một câu bắt đầu bằng "1 dòng = ...". Grain phải là mức chi tiết NHẤT mà nguồn cho phép.
3. Với mỗi quy trình, những dimension nào mô tả nó? Measure nào?
4. Vẽ **bus matrix**: hàng = quy trình, cột = dimension, đánh dấu X. Dimension nào xuất hiện ở nhiều hàng?
5. Bảng nào nguồn **ghi đè** (mất lịch sử), bảng nào **giữ lịch sử**? Điều này ảnh hưởng gì tới cách dựng SCD2?
6. Voucher thuộc về đơn hay dòng đơn? Phí ship thì sao? Nếu fact ở grain dòng đơn thì 2 con số này xử lý thế nào?

<details><summary>Đáp án tham khảo</summary>

| Quy trình | Grain | Dimension | Measure | Loại fact |
|---|---|---|---|---|
| Bán hàng (online + cửa hàng) | 1 dòng đơn / dòng hoá đơn đã bán | ngày, khách, sản phẩm, địa điểm (cửa hàng), hồ sơ đơn | số lượng, đơn giá, tiền hàng, giảm giá phân bổ, phí ship phân bổ, thực thu | transaction |
| Thực hiện đơn online | 1 đơn online | ngày (đặt, trả tiền, đóng gói, gửi, giao, trả, huỷ), khách, kho, hồ sơ đơn | tổng tiền, số món, số lần giao hỏng, số ngày giao | accumulating snapshot |
| Tồn kho | 1 sản phẩm × 1 kho × 1 ngày | ngày, sản phẩm, kho | tồn cuối ngày, nhập, xuất | periodic snapshot |
| Khuyến mãi áp dụng | 1 chương trình × 1 sản phẩm × 1 ngày | ngày, sản phẩm, chương trình | (không có) | factless |
| Chỉ tiêu doanh thu | 1 tháng × 1 danh mục cấp 1 | tháng, danh mục cấp 1 | chỉ tiêu | periodic snapshot (kế hoạch) |

Conformed: ngày (dùng ở cả 5, có lúc ở dạng rút gọn là tháng), sản phẩm, khách, địa điểm.

Q5: CRM giữ lịch sử (file full nối thêm) → SCD2 dựng lại từ đầu được. Shop, ERP ghi đè → muốn lịch sử phải tự chụp (snapshot / vault).

Q6: voucher và phí ship ở cấp **đầu đơn**. Fact grain dòng đơn → **phân bổ** xuống từng dòng (K5), hoặc làm thêm 1 fact grain đầu đơn. Tuyệt đối không lặp số tiền đầu đơn ở mọi dòng (cộng lại sẽ nhân lên).
</details>

---

## K2 ⭐⭐ `dim_date` và `dim_month`

**Yêu cầu:** 2 model trong `models/marts/core/` (folder `marts` đã cấu hình `table`).

`dim_date`: mỗi ngày của năm 2026 + **1 dòng đặc biệt** `date_key = -1` ("Chưa xảy ra").

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `date_key` | integer | `yyyymmdd`, ví dụ `20260301`. Dòng đặc biệt: `-1` |
| `full_date` | date | Dòng đặc biệt: null |
| `day_of_week` | integer | Thứ Hai = 1 … Chủ Nhật = 7 (`isodow`) |
| `day_name_vi` | varchar | `Thứ Hai` … `Chủ Nhật`. Dòng đặc biệt: `Chưa xảy ra` |
| `is_weekend` | boolean | |
| `month_key` | integer | `yyyymm`. Dòng đặc biệt: `-1` |
| `month_number`, `quarter_number`, `year_number` | integer | |
| `month_name_vi` | varchar | `Tháng 3` |
| `month_start_date` | date | ngày đầu tháng |

`dim_month`: 12 dòng, các cột `month_key, month_start_date, month_number, month_name_vi, quarter_number, year_number`, **giá trị phải giống hệt** cột cùng tên trong `dim_date`.

**Kiểm tra:** `dbt build -s dim_date dim_month` → `check.py K2`.

**Vì sao cần dòng `-1`?** Fact `fct_order_fulfillment` (K8) có 7 khoá ngày (đặt, trả tiền, đóng gói, gửi, giao, trả, huỷ). Đơn chưa giao thì `delivered_date_key` là gì? Để `null` thì `inner join` dim_date làm rơi đơn, BI phải viết `left join` khắp nơi, đếm đơn sai. Trỏ vào `-1` thì mọi join đều an toàn và báo cáo hiện chữ "Chưa xảy ra".

**Ngoài thực tế:**
- Một `dim_date` duy nhất đóng **nhiều vai** (role-playing): ngày đặt, ngày giao... Trong BI thường tạo view theo vai, vd `dim_order_date`, `dim_delivery_date`, để người dùng không nhầm.
- `dim_month` là **shrunken rollup dimension**: cùng dòng họ với `dim_date` nhưng ở grain thô hơn. Giữ tên + giá trị cột y hệt thì fact grain tháng (K13) và fact grain ngày so được với nhau.

<details><summary>Gợi ý</summary>

```sql
with spine as (
    {{ dbt_utils.date_spine(datepart="day",
                            start_date="cast('2026-01-01' as date)",
                            end_date="cast('2027-01-01' as date)") }}   -- end_date không bao gồm
)
select cast(strftime(cast(date_day as date), '%Y%m%d') as integer) as date_key, ...
```
Dòng đặc biệt: `union all select -1, null, null, 'Chưa xảy ra', ...` (đủ số cột, đúng thứ tự). `dim_month` = `select distinct ... from {{ ref('dim_date') }} where date_key <> -1`.
</details>

---

## K3 ⭐⭐ `dim_product` (Type 1) và các dimension nhỏ

**Yêu cầu:** 5 model trong `models/marts/core/`.

| Model | Cột (đúng tên) | Khoá surrogate | Thành viên đặc biệt |
|---|---|---|---|
| `dim_product` | `product_key, sku, product_name, brand, list_price, category_code, category_name, category_l1_code, category_l1_name` | `generate_surrogate_key(['sku'])` | `product_key = '-1'`, `sku = '-1'`, tên `Không xác định` |
| `dim_category_l1` | `category_l1_key, category_l1_code, category_l1_name` | `generate_surrogate_key(['category_l1_code'])` | — (3 dòng: TT, DT, NC) |
| `dim_location` | `location_key, location_code, location_name, location_type, city` | `generate_surrogate_key(['location_code'])` | `'-1'` (không xác định) và `'-2'` (không áp dụng, dùng cho đơn online) |
| `dim_voucher` | `voucher_key, voucher_code, voucher_type, voucher_name` | `generate_surrogate_key(['voucher_code'])` | `'-1'` và `'-2'` với `voucher_code = 'KHONG_VOUCHER'` |
| `dim_promotion` | `promotion_key, promo_code, promo_name, discount_pct, start_date, end_date` | `generate_surrogate_key(['promo_code'])` | — (1 dòng / chương trình; nguồn ở grain chương trình × sản phẩm) |

`dim_product` là **SCD Type 1**: luôn mang thuộc tính hiện tại. `category_l1_*` là danh mục cấp 1 chứa danh mục của sản phẩm (đi ngược lên gốc cây).

**Kiểm tra:** `check.py K3` ở ngày 0. Sang ngày 3 build lại `dim_product` và chấm lại: SKU07 phải ở `TT_TUI`, cấp 1 `TT`.

**Câu hỏi suy ngẫm**
1. Ngày 3 SKU07 đổi danh mục. Với Type 1, doanh thu SKU07 của các ngày **trước** ngày 3 giờ được tính vào danh mục nào? Có ai trong công ty có thể không đồng ý với điều đó?
2. Khi nào bạn chọn Type 2 cho `category_code`? Đổi sang Type 2 thì fact phải join thế nào?
3. Giá niêm yết đổi ở ngày 5. Báo cáo doanh thu có bị ảnh hưởng không? (gợi ý: fact dùng `unit_price` nào?)
4. `'-1'` và `'-2'` khác nhau thế nào? Cho 1 ví dụ mỗi loại trong lab này.

<details><summary>Gợi ý danh mục cấp 1</summary>

Cây không đều (1–3 cấp) → dùng CTE đệ quy, nên tách ra `models/intermediate/int_category__paths.sql` để K12 dùng lại:

```sql
with recursive paths as (
    select category_code, category_name, parent_code, 1 as category_level,
           category_code as category_l1_code, category_name as category_l1_name
    from {{ ref('stg_erp__categories') }} where parent_code is null
    union all
    select c.category_code, c.category_name, c.parent_code, p.category_level + 1,
           p.category_l1_code, p.category_l1_name
    from {{ ref('stg_erp__categories') }} c join paths p on c.parent_code = p.category_code
)
select * from paths
```
</details>

---

## K4 ⭐⭐⭐ `dim_customer` SCD Type 2 từ file CRM

**Bối cảnh:** CRM không có `updated_at`, chỉ gửi file full mỗi cuối ngày. Kho giữ mọi file. Muốn biết khách đổi gì, phải **so 2 file liên tiếp**.

**Yêu cầu:** `models/marts/core/dim_customer.sql`, grain **1 phiên bản khách hàng**.

| Cột | Quy tắc |
|---|---|
| `customer_key` | `dbt_utils.generate_surrogate_key(['customer_code', 'valid_from'])` |
| `customer_code` | |
| `full_name`, `email` | **Type 1**: mọi phiên bản mang giá trị của file MỚI NHẤT |
| `city`, `loyalty_tier` | **Type 2**: đổi 1 trong 2 cột này mới sinh phiên bản mới |
| `valid_from` | timestamp. Phiên bản ĐẦU TIÊN: `1900-01-01`. Các phiên bản sau: `extract_date` của file có thay đổi (00:00) |
| `valid_to` | `valid_from` của phiên bản kế tiếp; phiên bản hiện hành: `9999-12-31` |
| `is_current` | `valid_to = 9999-12-31` |
| `is_inferred` | `false` (bài K6 sẽ dùng cột này) |

Thêm dòng **unknown member**: `customer_key = '-1'`, `customer_code = '-1'`, `full_name = 'Khách vãng lai / không xác định'`, city/tier `'Không xác định'`, hiệu lực 1900 → 9999, `is_current = true`, `is_inferred = false`.

Test trong YAML:
- `dbt_utils.unique_combination_of_columns` trên `(customer_code, valid_from)`
- `dbt_utils.mutually_exclusive_ranges` (lower `valid_from`, upper `valid_to`, partition `customer_code`, `gaps: not_allowed`)

**Kiểm tra:** `check.py K4` ở ngày 0, rồi `next` từng ngày tới ngày 4 và build lại `dim_customer`. Kỳ vọng:
- C003: 2 phiên bản (Ha Noi → Da Nang từ 02/03)
- C002: **1** phiên bản, email mới (sửa lỗi gõ là Type 1)
- C005: **3** phiên bản (Member → Silver → Member). Không được gộp phiên bản 1 và 3!

⚠️ Từ ngày 2, K4 còn đòi khách C013 xuất hiện dưới dạng *inferred member*. Đó là việc của K6: làm tới đó thì quay lại.

**Câu hỏi suy ngẫm**
1. Vì sao ở đây **không cần** `dbt snapshot` như GĐ1? Nếu CRM chỉ gửi trạng thái hiện tại (ghi đè) thì sao?
2. Vì sao phiên bản đầu bắt đầu từ `1900-01-01` thay vì ngày file đầu tiên? (gợi ý: đơn W0001 đặt ngày 27/02, file CRM đầu tiên là 01/03; và đọc trước K6)
3. Độ chính xác thời gian của phiên bản là bao nhiêu? Khách đổi thành phố lúc 9h sáng 02/03, đơn đặt lúc 8h cùng ngày sẽ mang thành phố nào?
4. Nếu một ngày CRM quên gửi file rồi hôm sau gửi bù, `valid_from` có sai không?
5. Vì sao `customer_key` phải gồm cả `valid_from`?

**Ngoài thực tế:** rất nhiều hệ thống cũ (ERP, core banking, phần mềm kế toán) chỉ xuất file full theo ngày. Kỹ thuật "so 2 file liên tiếp" là cách dựng SCD2 phổ biến nhất ở các công ty Việt Nam.

<details><summary>Gợi ý</summary>

```sql
compared as (
    select customer_code, extract_date, city, loyalty_tier,
           row_number() over w as file_seq,
           lag(city) over w as prev_city,
           lag(loyalty_tier) over w as prev_tier
    from {{ ref('stg_crm__customers') }}
    window w as (partition by customer_code order by extract_date)
),
changes as (
    select ... from compared
    where file_seq = 1 or city is distinct from prev_city or loyalty_tier is distinct from prev_tier
)
```
Rồi `lead(valid_from)` cho `valid_to`, và join với "file mới nhất" để lấy Type 1. Dùng `is distinct from` thay vì `<>` để không bị null đánh lừa.
</details>

---

✅ Xong K1–K4: `check.py K2 K3 K4` PASS ở ngày 0. Sang [02-kimball-fact.md](02-kimball-fact.md).
