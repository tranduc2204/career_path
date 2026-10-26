# 03 — Kimball nâng cao: factless, bridge, drill-across, bus matrix (K10–K14)

> Lý thuyết: [4.4 bridge table](../../GD2-ly-thuyet/tuan-4/04-bridge-table.md) · [4.5 factless fact](../../GD2-ly-thuyet/tuan-4/05-factless-fact.md) · [4.2 bus matrix & drill-across](../../GD2-ly-thuyet/tuan-4/02-bus-matrix-va-conformed-dimension.md)

**Tình huống:** các câu hỏi tiếp theo không trả lời được bằng 1 fact + vài dimension:
- 🗨️ Marketing: *"Sản phẩm nào đang khuyến mãi mà không bán được cái nào?"* và *"Mỗi voucher mang về bao nhiêu doanh thu?"*
- 🗨️ Giám đốc ngành hàng: *"Doanh thu của cả nhánh Thời trang, của riêng nhánh Áo?"*
- 🗨️ Giám đốc: *"Tháng này mỗi ngành hàng đạt bao nhiêu % chỉ tiêu?"*

---

## K10 ⭐⭐ Factless fact: coverage khuyến mãi

**Grain:** *1 dòng = 1 chương trình × 1 sản phẩm × 1 ngày được khuyến mãi.* Không có measure.

**Yêu cầu:**

`models/marts/marketing/fct_promotion_coverage.sql`: cột `date_key, product_key, promotion_key`. Mỗi ngày trong `[start_date, end_date]` của từng dòng `stg_erp__promotions`. Test unique trên 3 cột.

`models/marts/marketing/rpt_promo_no_sales.sql`: các (ngày, sản phẩm, chương trình) **được khuyến mãi mà không có dòng nào trong `fct_sales`**, chỉ xét ngày `<= {{ business_date() }}`. Cột: `date_key, full_date, sku, product_name, promo_code`.

**Kiểm tra:** `check.py K10` ở nhiều ngày. Để ý: ở ngày 1, báo cáo nói SKU03 ngày 02/03 "không bán được". Sang ngày 2, dòng đó **biến mất**. Vì sao?

**Câu hỏi suy ngẫm**
1. Vì sao không trả lời được câu "KM mà không bán được" chỉ bằng `fct_sales`?
2. Ngày 3 ERP gia hạn KM_THANG3 thêm 1 ngày. Coverage tự cập nhật nhờ đâu? Nếu coverage là incremental thì sao?
3. Ngoài coverage, factless còn loại **event tracking** (ghi nhận sự kiện không có số đo). Cho 1 ví dụ trong Mây Shop.
4. Báo cáo "không bán được" của 2 ngày gần nhất có đáng tin không, khi POS đồng bộ 2 ngày một lần? Bạn sẽ ghi chú gì cho Marketing?

---

## K11 ⭐⭐⭐ Bridge cho thuộc tính nhiều giá trị: đơn – voucher

**Bối cảnh:** một đơn dùng 0–3 voucher (W0012 dùng 2, W0015 dùng 3). Không thể nhét `voucher_key` vào `fct_sales`: một dòng đơn sẽ phải có 3 khoá voucher.

**Yêu cầu:**

`models/marts/sales/bridge_order_voucher.sql`, grain *1 đơn × 1 voucher*, chỉ gồm các đơn có trong `fct_sales`:

| Cột | Quy tắc |
|---|---|
| `order_number` | đóng vai **group key** (nhóm voucher của đơn) |
| `voucher_key` | khoá `dim_voucher`. Đơn **không** dùng voucher → 1 dòng trỏ `'-2'` |
| `voucher_discount_amount` | số tiền voucher đó giảm (đơn không voucher: 0) |
| `weighting_factor` | `voucher_discount_amount / tổng giảm giá của đơn`. Đơn không voucher: 1.0. Tổng mỗi đơn = 1 |

`models/marts/sales/rpt_revenue_by_voucher.sql`: 1 dòng / voucher.

| Cột | Quy tắc |
|---|---|
| `voucher_code`, `voucher_name` | |
| `order_count` | số đơn dùng voucher đó |
| `weighted_net_amount` | `sum(net_amount * weighting_factor)` → cộng mọi voucher = đúng tổng doanh thu |
| `impact_net_amount` | `sum(net_amount)` của các đơn có dùng voucher đó (không chia) |

Thêm singular test `tests/assert_bridge_weights_sum_to_one.sql`.

**Kiểm tra:** `check.py K11`. Thông báo PASS cho biết cộng `impact` vượt tổng doanh thu bao nhiêu.

**Câu hỏi suy ngẫm**
1. Hai cột `weighted` và `impact` trả lời 2 câu hỏi khác nhau. Câu nào? Khi đưa lên dashboard, bạn đặt tên / chú thích thế nào để không ai cộng sai?
2. Vì sao cần dòng `'-2' KHONG_VOUCHER`? Bỏ đi thì `inner join` bridge làm mất gì?
3. Kimball gốc dùng `voucher_group_key` trên fact và bridge `(group_key, voucher_key, weight)`, nhiều đơn dùng chung 1 nhóm. Ở đây vì sao dùng luôn `order_number` làm group key? Khi nào nên tách nhóm dùng chung?
4. Trọng số theo số tiền giảm có phải lựa chọn duy nhất không? Đề xuất 1 cách khác và nói khi nào nó hợp lý hơn.

---

## K12 ⭐⭐⭐⭐ Bridge cho cây phân cấp không đều

**Bối cảnh:** cây danh mục có nhánh 1 cấp (`NC`), 2 cấp, 3 cấp. Sản phẩm gắn vào **bất kỳ cấp nào** (SKU07 gắn thẳng vào `DT_PK` dù `DT_PK` còn có con). Cách "làm phẳng thành cột cấp 1 / cấp 2 / cấp 3" không xử lý gọn trường hợp này.

**Yêu cầu:**

`models/marts/core/bridge_category_hierarchy.sql` (closure table): mọi cặp (tổ tiên, con cháu), **kể cả chính nó**.

| Cột | |
|---|---|
| `ancestor_category_code` | |
| `descendant_category_code` | |
| `distance` | số cấp giữa 2 nút; chính nó = 0 |

`models/marts/sales/rpt_sales_by_category.sql`: 1 dòng cho **mỗi** danh mục (11 dòng, kể cả danh mục chưa bán được gì), cột `category_code, category_name, category_level, net_amount, quantity` = tổng của mọi dòng bán có sản phẩm thuộc danh mục đó hoặc con cháu của nó (theo danh mục **hiện tại** của sản phẩm).

**Kiểm tra:** `check.py K12`. Tự kiểm: `net_amount` của `TT` = tổng của `TT_AO`, `TT_GIAY`, `TT_TUI`. `DT_PK` lớn hơn `DT_PK_SAC` đúng bằng doanh thu SKU07 (trước ngày 3).

**Câu hỏi suy ngẫm**
1. Cộng `net_amount` của MỌI dòng trong `rpt_sales_by_category` có ra tổng doanh thu không? Vì sao? Câu này là lỗi kinh điển khi dùng bridge phân cấp.
2. Closure table có bao nhiêu dòng với cây 11 nút? Với cây 10.000 nút sâu 8 cấp?
3. Sang ngày 3, SKU07 chuyển sang `TT_TUI`. Doanh thu của nhánh `DT` giảm. Kế toán hỏi "sao doanh thu tháng 2 của ngành Điện tử bị đổi?". Bạn trả lời thế nào?
4. Sơ đồ tổ chức nhân sự (quản lý → nhân viên) cũng là cây không đều. Dùng bridge này trả lời "doanh số của cả nhóm do chị A quản lý" thế nào?

<details><summary>Gợi ý</summary>

```sql
with recursive closure as (
    select category_code as ancestor_category_code, category_code as descendant_category_code, 0 as distance
    from {{ ref('stg_erp__categories') }}
    union all
    select c.ancestor_category_code, k.category_code, c.distance + 1
    from closure c join {{ ref('stg_erp__categories') }} k on k.parent_code = c.descendant_category_code
)
```
Báo cáo: `categories left join bridge on ancestor = category left join (doanh thu theo danh mục lá) on descendant`.
</details>

---

## K13 ⭐⭐⭐ Drill-across: chỉ tiêu vs thực tế

**Bối cảnh:** chỉ tiêu đặt theo **tháng × danh mục cấp 1**. Doanh thu ở grain **dòng đơn**. Hai fact khác grain.

**Yêu cầu:**

`models/marts/sales/fct_sales_target.sql`: cột `month_key, category_l1_key, target_amount` (join `dim_month`, `dim_category_l1`). Test unique `(month_key, category_l1_key)`.

`models/marts/sales/rpt_target_vs_actual.sql`: 1 dòng / (tháng, danh mục cấp 1) có chỉ tiêu **hoặc** có doanh thu.

| Cột | |
|---|---|
| `month_key`, `category_l1_code`, `category_l1_name` | thuộc tính **conformed** |
| `target_amount` | null nếu tháng đó không có chỉ tiêu |
| `actual_net_amount` | tổng `net_amount` (0 nếu không bán) |
| `achievement_ratio` | `actual / target` (null nếu không có chỉ tiêu) |

Cách làm đúng (**drill-across**): đưa **từng** fact về grain chung (tháng × danh mục cấp 1) qua thuộc tính conformed (`dim_date.month_key`, `dim_product.category_l1_code`), **rồi** full outer join 2 kết quả.

**Kiểm tra:** `check.py K13`. Có 3 dòng tháng 2 chỉ có thực tế (bán ngày 27–28/02), không có chỉ tiêu.

**Câu hỏi suy ngẫm**
1. Thử viết sai: join `fct_sales` với `fct_sales_target` trước rồi mới `group by`. Chuyện gì xảy ra với `target_amount`?
2. Vì sao dùng `full outer join` thay vì `left join` từ chỉ tiêu?
3. Nếu `dim_product.category_l1_name` ghi "Thời Trang" còn `dim_category_l1` ghi "Thời trang", báo cáo hỏng ở đâu? Đây chính là lý do của từ "conformed".

---

## K14 ⭐⭐ Bus matrix khớp model thật

**Yêu cầu:** file `lab/bus_matrix.yml` (ngang hàng `dbt_project.yml`):

```yaml
bus_matrix:
  - process: Bán hàng (online + cửa hàng)
    fact: fct_sales
    type: transaction            # transaction | periodic_snapshot | accumulating_snapshot | factless
    grain: 1 dòng đơn online hoặc 1 dòng hoá đơn POS đã bán
    dimensions: [dim_date, dim_customer, ...]
  - process: ...
```

Ít nhất 5 quy trình (5 fact bạn đã làm).

`check.py K14` kiểm tra **file khớp với model thật**:
- Mỗi `fact` tồn tại.
- Mỗi `dim_X` tồn tại, có cột khoá `X_key`.
- Fact có cột `X_key` hoặc `<vai>_X_key` (vd `order_date_key`, `store_location_key`), và mọi giá trị khoá đều có trong dimension.

**Kiểm tra:** `check.py K14`. Thông báo PASS liệt kê các dimension dùng chung (conformed).

**Ngoài thực tế:** bus matrix là tài liệu **lập kế hoạch** quan trọng nhất của Kimball: nó cho thấy làm quy trình nào trước, dimension nào phải thống nhất giữa các team. Giữ nó dạng YAML cạnh code và cho CI kiểm tra (như bài này) giúp tài liệu không bao giờ "nói một đằng, code một nẻo". Đưa bảng bus matrix vào README của `adventure_works`.

---

✅ Xong K2–K14: `./scripts/replay.sh` → 13 bài K đều PASS (K1 không chấm). Tuần 6 tiếp ở [04-data-vault-raw-vault.md](04-data-vault-raw-vault.md).
