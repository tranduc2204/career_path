# 4.4 Bridge table: dimension nhiều giá trị và phân cấp không đều

Bridge table giải quyết 2 bài toán mà mô hình sao (star) "thuần" không làm được:

1. **Dimension nhiều giá trị** (multivalued): ở grain của fact, một dimension có **nhiều** giá trị cùng lúc.
2. **Phân cấp không đều** (ragged / variable-depth hierarchy): cây có độ sâu khác nhau ở mỗi nhánh.

## Phần 1. Dimension nhiều giá trị

### Bài toán

| Fact | Dimension "nhiều giá trị" |
|---|---|
| Dòng đơn hàng | Voucher (1 đơn dùng 0–3 voucher) |
| Lần khám bệnh | Chẩn đoán (1 lần khám nhiều chẩn đoán) |
| Giao dịch tài khoản ngân hàng | Chủ tài khoản (tài khoản đồng sở hữu) |
| Đơn hàng AdventureWorks | Lý do mua (`SalesOrderHeaderSalesReason`) |

Không thể đặt `voucher_key` vào fact: một dòng sẽ cần 3 khoá. Nhân fact lên 3 dòng thì vỡ grain, doanh thu nhân 3.

### Cấu trúc

```
fct_sales ──(order_number = group key)──▶ bridge_order_voucher ──(voucher_key)──▶ dim_voucher
                                          (order_number, voucher_key, weighting_factor)
```

| Cột bridge | Ý nghĩa |
|---|---|
| Group key | Nhận diện **nhóm** giá trị. Kimball gốc: `voucher_group_key` riêng, nhiều đơn dùng chung 1 nhóm. Trong lab: dùng luôn `order_number` |
| Khoá dimension | `voucher_key` |
| `weighting_factor` | Phần của giá trị này trong nhóm. **Tổng mỗi nhóm = 1** |

### Hai kiểu báo cáo

| | Weighted (có trọng số) | Impact (ảnh hưởng, không trọng số) |
|---|---|---|
| Công thức | `sum(net_amount * weighting_factor)` | `sum(net_amount)` |
| Trả lời | "Doanh thu **phân bổ** cho voucher X là bao nhiêu?" | "Các đơn **có dùng** voucher X mang lại bao nhiêu doanh thu?" |
| Cộng mọi voucher | = **đúng tổng doanh thu** | **Lớn hơn** tổng (đơn nhiều voucher bị đếm nhiều lần) |

Cả hai đều đúng, trả lời 2 câu hỏi khác nhau. Nguy hiểm là cho người dùng cộng cột impact rồi so với tổng doanh thu. Trên dashboard: đặt tên rõ ("Doanh thu các đơn có dùng voucher (không cộng dồn được)"), hoặc chỉ đưa weighted.

### Chọn trọng số

| Cách | Khi nào |
|---|---|
| Theo giá trị (số tiền giảm, thời lượng, tỷ lệ sở hữu) | Có con số nghiệp vụ hợp lý, như lab: `discount_amount / tổng giảm của đơn` |
| Chia đều (1/n) | Không có cơ sở phân bổ (lý do mua hàng, chẩn đoán) |
| Do nghiệp vụ quy định | Hợp đồng đồng sở hữu ghi rõ 60/40 |

### Thành viên "không có"

Đơn không dùng voucher vẫn phải có **1 dòng bridge** trỏ tới thành viên `-2` ("Không dùng voucher"), trọng số 1. Không có dòng này, `inner join` qua bridge làm **mất** doanh thu các đơn không voucher.

### Test bắt buộc

```sql
-- tests/assert_bridge_weights_sum_to_one.sql
select order_number, sum(weighting_factor) as total_weight
from {{ ref('bridge_order_voucher') }}
group by order_number
having abs(sum(weighting_factor) - 1) > 0.000001
```

Thêm: mọi `order_number` của fact đều có trong bridge (relationships), unique `(order_number, voucher_key)`.

### Khi nào KHÔNG cần bridge

- Chỉ quan tâm **giá trị chính** (voucher lớn nhất, chẩn đoán chính) → thêm 1 khoá vào fact là đủ.
- Số giá trị tối đa nhỏ và cố định → có thể làm cột `voucher_1_key`, `voucher_2_key` (nhưng khó query "doanh thu theo voucher").
- Nhu cầu chỉ là **lọc** ("đơn có dùng FREESHIP") → một cột cờ hoặc mảng (ARRAY trên BigQuery/Snowflake) trong fact có thể đủ.

## Phần 2. Phân cấp không đều

### Bài toán

| Phân cấp đều (fixed depth) | Phân cấp không đều (ragged) |
|---|---|
| Ngày → tháng → quý → năm | Cây danh mục: nhánh sâu 1, 2 hay 3 cấp |
| Sản phẩm → nhóm → ngành (AdventureWorks: Subcategory → Category) | Sơ đồ tổ chức: quản lý → nhân viên, độ sâu tuỳ người |
| → **làm phẳng** thành cột trong dimension là đủ | Kế toán: hệ thống tài khoản nhiều cấp |

Với cây không đều, làm phẳng thành `level_1`, `level_2`, `level_3` gặp vấn đề: nhánh 1 cấp thì `level_2` điền gì? Sản phẩm gắn vào nút **không phải lá** (SKU07 gắn vào `DT_PK` trong lab) thì sao? Cây sâu thêm 1 cấp thì phải sửa cấu trúc bảng.

### Closure table (bridge phân cấp)

Lưu **mọi cặp (tổ tiên, con cháu)**, kể cả chính nó:

| ancestor | descendant | distance |
|---|---|---|
| TT | TT | 0 |
| TT | TT_AO | 1 |
| TT | TT_AO_THUN | 2 |
| TT_AO | TT_AO_THUN | 1 |
| TT_AO_THUN | TT_AO_THUN | 0 |
| ... | ... | ... |

Kimball còn gợi ý thêm cột `is_top_most` (tổ tiên là gốc), `is_bottom_most` (con cháu là lá).

Dựng bằng CTE đệ quy:

```sql
with recursive closure as (
    select category_code as ancestor_category_code, category_code as descendant_category_code, 0 as distance
    from {{ ref('stg_erp__categories') }}
    union all
    select c.ancestor_category_code, k.category_code, c.distance + 1
    from closure c
    join {{ ref('stg_erp__categories') }} k on k.parent_code = c.descendant_category_code
)
select * from closure
```

### Dùng bridge phân cấp

"Doanh thu của nhánh X (gồm mọi cấp con)":

```sql
select b.ancestor_category_code, sum(f.net_amount)
from fct_sales f
join dim_product p using (product_key)
join bridge_category_hierarchy b on b.descendant_category_code = p.category_code
where b.ancestor_category_code = 'TT'          -- chọn nút cần xem
group by 1
```

- Muốn **chỉ** nút đó (không gồm con): `distance = 0`.
- Muốn con trực tiếp: `distance = 1`.

**Bẫy kinh điển:** `group by ancestor` cho **mọi** nút rồi cộng tất cả lại → doanh thu bị đếm ở mọi cấp (1 đơn áo thun được cộng ở TT_AO_THUN, TT_AO và TT). Báo cáo nhiều cấp chỉ được đọc **từng nút một**, không cộng dọc.

### Kích thước

Số dòng closure table = tổng độ sâu của mọi nút (+1). Cây 11 nút trong lab: 22 dòng. Cây 10.000 nút sâu trung bình 6 cấp: khoảng 70.000 dòng, vẫn nhỏ. Sơ đồ tổ chức đổi theo thời gian → closure table cũng cần lịch sử (SCD2 trên bridge, có `valid_from`, `valid_to`).

## Lỗi hay gặp

- Nhân fact theo dimension nhiều giá trị (vỡ grain).
- Quên thành viên "không có" trong bridge → mất doanh thu khi inner join.
- Trọng số không tổng bằng 1 do làm tròn → lệch vài đồng; dùng kiểu số thực hoặc dồn phần dư vào 1 dòng.
- Cộng báo cáo impact như thể nó cộng được.
- Làm phẳng cây không đều thành cột cố định, điền "N/A" lung tung.
- Cộng doanh thu ở mọi nút của bridge phân cấp.

## Áp dụng vào adventure_works

- [ ] `bridge_sales_reason` từ `Sales.SalesOrderHeaderSalesReason` + `dim_sales_reason` (`SalesReason`), trọng số chia đều 1/n. Đơn không có lý do → thành viên `-2`
- [ ] Báo cáo "doanh thu theo lý do mua": weighted và impact, ghi chú rõ trên README
- [ ] Bridge phân cấp cho sơ đồ tổ chức `HumanResources.Employee` (`OrganizationNode` là kiểu `hierarchyid` của SQL Server; khi chuyển sang Snowflake thường thành chuỗi đường dẫn như `/1/1/5/` hoặc cột cấp — tự tìm hiểu dữ liệu bạn đang có) hoặc dùng `ManagerID` nếu nguồn của bạn có
- [ ] Test: tổng trọng số = 1; mọi đơn có trong bridge

## Câu hỏi tự kiểm tra

1. Vì sao không nhét được `voucher_key` vào fact dòng đơn?
2. Weighting factor là gì? Tổng mỗi nhóm phải bằng bao nhiêu?
3. Báo cáo weighted và impact khác nhau thế nào? Cái nào cộng được?
4. Vì sao bridge cần thành viên "không có"?
5. Closure table lưu gì? Vì sao gồm cả cặp (X, X)?
6. Vì sao không được cộng doanh thu ở mọi nút của bridge phân cấp?

## Tài liệu

- *The Data Warehouse Toolkit* — chương 7 (Accounting: hierarchy bridge), chương 14 (Healthcare: multivalued diagnosis), chương 10 (Financial services: multiple account holders)
- Kimball Group — danh mục kỹ thuật, mục "Multivalued Dimension and Bridge Tables" và "Ragged/Variable Depth Hierarchies": https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- Lab: [K11, K12](../../bai-tap-kimball-data-vault/bai-tap/03-kimball-nang-cao.md)
