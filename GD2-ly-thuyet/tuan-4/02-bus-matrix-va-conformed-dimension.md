# 4.2 Bus matrix, conformed dimension và drill-across

## Vấn đề: mỗi team một "doanh thu", mỗi bảng một "khách hàng"

Không có kế hoạch chung, mỗi mart tự làm dimension riêng:

```
mart Sales:      dim_customer_sales  (city = "HCM")
mart Marketing:  dim_khach_hang      (city = "Ho Chi Minh")
mart Finance:    dim_cust            (city = "TP.HCM")
```

Kết quả: báo cáo của 3 team không so được với nhau, mỗi lần họp là một lần cãi số. Kimball gọi đây là **"data mart cô lập" (stovepipe)**.

Lời giải của Kimball gồm 3 phần: **bus architecture**, **conformed dimension**, **bus matrix**.

## Enterprise bus architecture

Ý tưởng: giống "bus" trong máy tính (một chuẩn cắm chung, thiết bị nào cũng cắm được), kho dữ liệu có một bộ **dimension chuẩn dùng chung**. Mỗi quy trình nghiệp vụ (fact) "cắm" vào bus bằng cách dùng đúng các dimension đó.

```
              dim_date ─── dim_customer ─── dim_product ─── dim_location   ← "bus" (conformed dimensions)
                 │              │               │                │
     ┌───────────┼──────────────┼───────────────┼────────────────┤
     ▼           ▼              ▼               ▼                ▼
 fct_sales   fct_order_fulfillment   fct_inventory_daily   fct_promotion_coverage ...
```

Nhờ vậy kho được xây **từng quy trình một** (incremental), quy trình sau tự khớp với quy trình trước.

## Conformed dimension

Hai dimension là **conformed** khi:
- **Giống hệt**: cùng một bảng (cách tốt nhất trong dbt: cùng một model `dim_customer` được mọi fact `ref()` tới), hoặc
- Là **tập con / bản rút gọn** của nhau với **cùng tên cột và cùng giá trị**:
  - **Shrunken rollup dimension**: `dim_month` là `dim_date` ở grain tháng. Cột `month_key`, `month_name_vi` giống y hệt.
  - **Shrunken subset**: `dim_category_l1` chỉ gồm danh mục cấp 1, cột `category_l1_code` trùng với cột cùng tên trong `dim_product`.

"Giống" nghĩa là giống **từng ký tự**: "Thời trang" và "Thời Trang" là hai giá trị khác nhau, drill-across sẽ không khớp.

| Conformed ở đâu | Cách làm trong dbt |
|---|---|
| Dimension dùng chung | Một model duy nhất trong `marts/core/`, mọi fact `ref()` tới |
| Shrunken dimension | Dựng **từ** dimension gốc (`select distinct ... from {{ ref('dim_date') }}`), không viết lại logic |
| Thuộc tính dùng chung | Tính **một chỗ** (vd `int_category__paths`), các dimension cùng đọc |

**Conformed fact** (ít được nhắc hơn): measure cùng tên ở nhiều fact phải cùng định nghĩa và đơn vị. `net_amount` ở `fct_sales` và ở một bảng tổng hợp phải cùng công thức.

## Bus matrix

Bảng kế hoạch: **hàng = quy trình nghiệp vụ**, **cột = dimension**, đánh dấu X khi quy trình dùng dimension đó.

| Quy trình | date | month | customer | product | category_l1 | location | order_profile | promotion |
|---|---|---|---|---|---|---|---|---|
| Bán hàng | X | | X | X | | X | X | |
| Thực hiện đơn online | X (×7 vai) | | X | | | X | X | |
| Tồn kho cuối ngày | X | | | X | | X | | |
| Khuyến mãi áp dụng | X | | | X | | | | X |
| Chỉ tiêu doanh thu | | X | | | X | | | |

Đọc bus matrix để:
- **Lập kế hoạch**: làm quy trình nào trước (thường là quy trình có giá trị cao + dữ liệu sẵn sàng).
- **Thấy dimension quan trọng**: cột có nhiều X (date, product, customer) phải làm kỹ nhất, thống nhất sớm nhất với các team.
- **Giao tiếp**: một trang giấy cho sếp, cho team khác hiểu kho dữ liệu có gì.

Kimball còn có **opportunity / stakeholder matrix**: hàng = quy trình, cột = phòng ban quan tâm. Dùng để chọn quy trình làm trước.

### Giữ bus matrix "sống" cạnh code

Bus matrix nằm trong file Word sẽ lệch với code sau vài tháng. Cách tốt hơn: YAML trong repo, CI kiểm tra nó khớp với model (bài K14 của lab làm đúng việc này):

```yaml
bus_matrix:
  - process: Bán hàng (online + cửa hàng)
    fact: fct_sales
    type: transaction
    grain: 1 dòng đơn online hoặc 1 dòng hoá đơn POS đã bán
    dimensions: [dim_date, dim_customer, dim_product, dim_location, dim_order_profile]
```

Một cách khác trong dbt: gắn `meta` hoặc `tags` cho fact (`meta: {bus_process: sales}`) rồi sinh bus matrix từ `manifest.json`.

## Drill-across

**Drill-across** = trả lời câu hỏi cần **nhiều fact** (thường khác grain), ví dụ "doanh thu thực tế vs chỉ tiêu theo tháng × ngành hàng".

Cách đúng (2 bước):

```
Bước 1: đưa TỪNG fact về grain chung qua thuộc tính conformed
   fct_sales         → group by month_key, category_l1_code → actual
   fct_sales_target  → (đã ở grain tháng × ngành)           → target

Bước 2: join 2 kết quả trên các thuộc tính chung (thường FULL OUTER JOIN)
```

```sql
with actual as (
    select d.month_key, p.category_l1_code, sum(f.net_amount) as actual_net_amount
    from {{ ref('fct_sales') }} f
    join {{ ref('dim_date') }} d on d.date_key = f.order_date_key
    join {{ ref('dim_product') }} p using (product_key)
    group by 1, 2
),
target as (
    select t.month_key, c.category_l1_code, t.target_amount
    from {{ ref('fct_sales_target') }} t
    join {{ ref('dim_category_l1') }} c using (category_l1_key)
)
select coalesce(t.month_key, a.month_key) as month_key, ...
from target t
full outer join actual a on a.month_key = t.month_key and a.category_l1_code = t.category_l1_code
```

Cách **sai**: join 2 fact với nhau ở grain chi tiết rồi mới `group by`. Mỗi dòng chỉ tiêu bị nhân lên theo số dòng đơn → `sum(target_amount)` sai (fan-out).

Vì sao **full outer join**: tháng có bán nhưng chưa đặt chỉ tiêu (tháng 2 trong lab), hoặc ngành có chỉ tiêu nhưng chưa bán được, đều phải hiện ra.

Semantic layer (GĐ3, MetricFlow) làm drill-across tự động: bạn khai báo metric trên từng fact và dimension dùng chung, nó tự sinh SQL 2 bước như trên. Nó chỉ làm được khi dimension **conformed**.

## Lỗi hay gặp

- Mỗi mart tự viết `dim_customer` riêng → số khách hàng mỗi báo cáo một khác.
- Shrunken dimension viết lại logic thay vì dựng từ dimension gốc → lệch giá trị theo thời gian.
- Join fact với fact ở grain chi tiết.
- `left join` từ một phía khi drill-across → mất dòng của phía kia.
- Bus matrix chỉ vẽ một lần lúc đầu dự án rồi bỏ.

## Áp dụng vào adventure_works

- [ ] Vẽ bus matrix cho các quy trình ở 4.1 (bán hàng internet, bán hàng đại lý, thực hiện đơn, sản xuất, tồn kho, chỉ tiêu, khuyến mãi). Đưa bảng vào README
- [ ] `bus_matrix.yml` + script (hoặc test) kiểm tra khớp model như bài K14
- [ ] Rà `marts/`: có dimension nào bị định nghĩa 2 lần không? Gộp về `marts/core/`
- [ ] Drill-across: `Sales.SalesPersonQuotaHistory` (chỉ tiêu theo **quý** × nhân viên) vs doanh thu thực tế. Cần `dim_quarter` (shrunken từ `dim_date`) và `dim_employee` dùng chung

## Câu hỏi tự kiểm tra

1. "Conformed dimension" nghĩa là gì? Hai cách để 2 dimension được coi là conformed?
2. Shrunken rollup dimension là gì? Cho ví dụ. Vì sao nên dựng từ dimension gốc?
3. Bus matrix có hàng, cột là gì? Dùng nó để làm gì trong dự án?
4. Drill-across là gì? Vì sao không join 2 fact trực tiếp?
5. Khi nào dùng full outer join trong drill-across?
6. Semantic layer liên quan gì tới conformed dimension?

## Tài liệu

- *The Data Warehouse Toolkit* — chương 4 (Inventory: bus matrix, conformed dimensions, drill-across)
- Kimball Group — Enterprise Data Warehouse Bus Matrix: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/enterprise-data-warehouse-bus-matrix/
- Lab: [K13, K14](../../bai-tap-kimball-data-vault/bai-tap/03-kimball-nang-cao.md)
