# số bảng tổng cộng
'''
| table_name         |
| ------------------ |
| _lab_log           |
| _lab_state         |
| customer_changelog |
| customers          |
| events             |
| order_items        |
| orders             |
| products           |
'''

các staging nên có stg__customers



# tình huống P1 là 
bảng stg order_xuất hiện duplicate.  
và bị báo lỗi uniquekey
cần sử dụng qualify để loại bỏ case deduplicate. 

### P1 — Ngày 6: raw.orders bị nạp trùng
- **Phát hiện lúc / bởi:** `dbt build` sáng ngày 6, test `unique` trên `stg_orders.order_id` đỏ. PM hỏi "sao dashboard vẫn là số hôm qua".
- **Ảnh hưởng:** test đỏ → mọi model sau `stg_orders` bị SKIP (`fct_orders`, `fct_order_lines`, `fct_daily_revenue`, `customer_lifetime`...) → dashboard đứng yên ở số ngày 5. Số không sai, chỉ cũ.
- **Nguyên nhân gốc:** công cụ ingest retry giữa chừng (at-least-once) → 4 đơn 1066–1069 (order_date 2026-01-06) bị ghi 2 lần, 2 dòng giống hệt nhau kể cả `_loaded_at`. `stg_orders` không có bước khử trùng nên trùng lọt thẳng lên.
- **Cách sửa:** thêm vào `stg_orders`:
  ```sql
  qualify row_number() over(partition by order_id order by _loaded_at desc, updated_at desc) = 1
  ```
  Không cần backfill vì test đỏ đã chặn, chưa model incremental nào nạp dòng trùng.
- **Phòng ngừa:** test `unique` trên source `raw.orders` với `warn_if: ">0"`, `error_if: ">10"` để theo dõi ingest; giữ test `unique` mức error trên `stg_orders` để bảo đảm 1 dòng = 1 đơn.

**Vì sao sửa ở staging mà không sửa ở fct_orders?**
- stg là gốc, nhiều fct kế thừa. Sửa ở fct thì mỗi fct phải tự khử trùng, sửa một lần là phải sửa toàn bộ, quên một chỗ là số nhân đôi.
- Bảng incremental không tự sửa dòng cũ: trùng lọt vào fct rồi thì phải backfill, không chỉ sửa code.
- Model mới viết sau này đọc `stg_orders` sẽ mặc định 1 dòng = 1 đơn, đó là cam kết của staging.

**Postmortem**
1. *2 dòng trùng không giống hệt nhau thì giữ dòng nào?* Giữ dòng `_loaded_at` mới nhất (bản nạp sau cùng). Nếu `_loaded_at` bằng nhau thì xét tiếp `updated_at` để `row_number()` luôn chọn cùng một dòng, không ngẫu nhiên. `distinct` không xử lý được trường hợp này vì chỉ gộp dòng giống hệt.
2. *Test `unique` ở staging để `error` hay `warn`?* Cân nhắc giữa dashboard đứng yên (error) và dashboard sai (warn), cần hỏi lead. Cách của mình: dùng ngưỡng. Nhưng sau khi có `qualify` thì `unique` trên `stg_orders` luôn xanh, nên ngưỡng phải đặt ở source:
   | Lớp | Việc | Mức |
   |---|---|---|
   | `raw.orders` | theo dõi chất lượng ingest | warn > 0, error > 10 |
   | `stg_orders` | bảo đảm 1 dòng = 1 đơn | error |



# tình huống P2 là 
ngày 7 backend đổi tên cột `status` → `order_status` trong raw.orders, không báo trước. Dùng `adapter.get_columns_in_relation` + `{% if %}` để staging đọc được cả tên cũ lẫn tên mới.

### P2 — Ngày 7: backend đổi tên cột status → order_status
- **Phát hiện lúc / bởi:** job dbt 06:30 ngày 7 failed (#data-alerts): `stg_orders` ERROR vì không còn cột `status`.
- **Ảnh hưởng:** `stg_orders` lỗi → khoảng 20 model và test phía sau bị SKIP → dashboard đứng yên ở số ngày 6. Không có dữ liệu sai được nạp vào bảng incremental.
- **Nguyên nhân gốc:** team backend đổi tên cột `raw.orders.status` thành `order_status` mà không báo team data. `stg_orders` viết cứng `status as order_status` nên lỗi ngay khi cột cũ biến mất.
- **Cách sửa:** chỉ sửa `stg_orders`: đọc danh sách cột thật của nguồn rồi chọn nhánh theo tên đang có, để staging chạy được cả **trước** (ngày 0–6) và **sau** (ngày 7+) khi đổi tên:
  ```sql
  {%- set source_columns = adapter.get_columns_in_relation(source('raw', 'orders'))
      | map(attribute='name') | map('lower') | list -%}
  ...
  {% if 'order_status' in source_columns %}
      order_status,
  {% elif 'status' in source_columns %}
      status as order_status,   -- TODO: xoá khi hết cần đọc dữ liệu tên cũ (xem câu 3)
  {% endif %}
  ```
  Không cần backfill vì build lỗi đã chặn, chưa model nào nạp dữ liệu ngày 7. Kiểm tra bằng `./scripts/replay.sh 7` (P3–P6 SKIP vì chưa tới ngày).
- **Phòng ngừa:** test `dbt_expectations.expect_column_to_exist` trên source `raw.orders` chạy trước `dbt build`; data contract với backend; CI chạy dbt trên môi trường thử của backend (chi tiết ở câu 2).

**Postmortem**
1. *Có bao nhiêu model phía sau phải sửa?* **0**, chỉ sửa 1 model là `stg_orders`. Có 6 model dùng cột `order_status` (`int_orders`, `fct_orders`, `fct_orders_pit`, `fct_order_lines`, `customer_order_summary`, `customer_order_summary_dynamic`) nhưng tất cả đọc qua `ref('stg_orders')`, không model nào đọc thẳng `source('raw', 'orders')`. Nếu không có tầng staging thì cả 6 model đều phải sửa, sót một cái là lỗi. → Staging là lớp đệm: là nơi duy nhất "biết" tên cột thật của nguồn, nguồn đổi thì chỉ sửa một chỗ.
2. *Làm sao phát hiện trước khi job sáng lỗi?* Ba mức, từ muộn đến sớm:
   | Mức | Cách | Được gì |
   |---|---|---|
   | Test source | `expect_column_to_exist` trên `raw.orders`, chạy `dbt test -s source:raw` trước `dbt build` | báo lỗi rõ nghĩa ("nguồn mất cột X") và sớm hơn, nhưng không ngăn được sự cố |
   | Data contract | thoả thuận với backend: schema bảng `orders` cố định, đổi phải báo trước N ngày | xử lý gốc rễ: lần này lỗi vì không ai báo |
   | CI trên môi trường thử | chạy dbt trên dữ liệu môi trường thử của backend trước khi họ lên production | phát hiện trước khi sự cố xảy ra |
3. *Hỗ trợ tên cũ bao lâu, khi nào xoá nhánh `status`?* Chưa xoá ngay được vì vẫn có thể gặp dữ liệu mang tên cũ:
   - dữ liệu lịch sử phải đọc lại (backfill, full refresh từ file/backup cũ; trong lab là `replay.sh` chạy từ ngày 0);
   - môi trường khác (dev/staging của backend) có thể chưa đổi;
   - backend có thể rollback về bản cũ.

   Xoá khi **cả ba** không còn: backend xác nhận mọi môi trường đã đổi, hết thời gian rollback, không còn dữ liệu cũ cần đọc lại. Trong lab này phải giữ luôn vì replay chạy từ ngày 0. Ngoài thực tế thì gắn TODO có ngày + ticket để không thành code chết.







# tình huống P3 là 
ngày 8 tính năng trả hàng lên production, nguồn xuất hiện trạng thái mới `returned`. Test `accepted_values` chặn pipeline. Tài chính quy định đơn `returned` không tính doanh thu.

### P3 — Ngày 8: trạng thái mới `returned`
- **Phát hiện lúc / bởi:** `dbt build` sáng ngày 8, test `accepted_values` trên `stg_orders.order_status` đỏ. Kế toán trưởng báo doanh thu 29/12 trên dashboard cao hơn sổ sách.
- **Ảnh hưởng:** test đỏ → mọi model sau `stg_orders` bị SKIP → dashboard đứng yên ở số ngày 7. Nếu không bị chặn, 3 đơn returned (1013, 1014, 1015, ngày 2025-12-29) sẽ bị tính vào doanh thu, vì quy tắc là "loại các trạng thái trong danh sách đen", trạng thái lạ thì mặc định được tính.
- **Nguyên nhân gốc:** backend thêm giá trị trạng thái mới. Không phải lỗi dữ liệu mà là **quy tắc nghiệp vụ mới**: pipeline chưa biết `returned` có tính doanh thu hay không.
- **Cách sửa:** chỉ sửa cấu hình, không sửa SQL của model nào:
  | Chỗ sửa | Thay đổi | Để làm gì |
  |---|---|---|
  | `_staging.yml` | thêm `returned` vào `accepted_values` | test chấp nhận trạng thái mới |
  | `dbt_project.yml` → `order_statuses` | thêm `returned` | `customer_order_summary` có cột `orders_returned` (J3) |
  | `dbt_project.yml` → `non_revenue_statuses` | thêm `returned` | `int_orders.is_revenue_order` = false → `fct_daily_revenue`, `customer_lifetime` tự loại |

  `customer_order_summary_dynamic` không phải sửa: macro `get_order_statuses()` đọc trạng thái từ dữ liệu nên tự có `returned`.
  Không cần backfill: xem câu postmortem 3.
- **Phòng ngừa:** giữ `accepted_values` để trạng thái lạ luôn bị phát hiện; thoả thuận với backend báo trước khi thêm trạng thái; định nghĩa doanh thu có chủ sở hữu và tài liệu (câu 2).

**Nếu quy tắc đặt ở `int_orders` (B7) thì sửa mấy chỗ? Nếu không thì mấy chỗ?**
- Có `int_orders`: quy tắc doanh thu sửa **1 chỗ** (var `non_revenue_statuses`, code `int_orders` cũng không đổi). Tổng cả sự cố là 3 dòng cấu hình ở bảng trên.
- Không có `int_orders`: mỗi model tự viết `where order_status <> 'cancelled'` → phải sửa **từng model tính doanh thu** (`fct_daily_revenue`, `customer_lifetime`, và mọi model/dashboard viết sau này). Sót một chỗ là hai báo cáo cho ra hai con số doanh thu khác nhau.

**Postmortem**
1. *`accepted_values` đỏ chặn pipeline, có nên đổi sang `warn`? Đổi thì mất gì?*
   Không nên. Với `warn`, đơn `returned` chạy thẳng vào mart và **được tính là doanh thu** (danh sách đen không có `returned`) → dashboard báo doanh thu cao hơn thực tế, sếp ra quyết định trên số sai mà không ai biết. Warn thì chỉ hiện trong log, dễ bị bỏ qua.
   | | `error` | `warn` |
   |---|---|---|
   | Dashboard | đứng yên (cũ) | chạy tiếp nhưng **sai** |
   | Ai biết có chuyện | team data, ngay sáng đó | người dùng, khi số lệch sổ sách (có thể vài ngày sau) |
   | Cái giá | cả buổi sáng không có số mới, kể cả model không liên quan doanh thu | mất niềm tin vào số liệu |
   Số cũ có thể chờ, số sai thì nguy hiểm hơn. Cách giảm thiệt hại của `error`: có alert để sửa nhanh, và phân tách job để model không liên quan (sự kiện...) không bị kéo theo.
2. *Ai sở hữu định nghĩa doanh thu? Ghi ở đâu?*
   - **Chủ sở hữu là phía nghiệp vụ** (tài chính / kế toán trưởng): họ quyết định đơn nào tính doanh thu. AE không tự quyết, AE **cài đặt** định nghĩa đó vào code. Lần này AE chỉ làm theo quy định tài chính đưa ra.
   - **Ghi ở một chỗ duy nhất** mà mọi bên cùng dùng: trong dbt hiện tại là `int_orders.is_revenue_order` + var `non_revenue_statuses`, kèm mô tả trong yml/dbt docs. Tốt hơn nữa là **semantic layer** (GĐ3): định nghĩa metric `revenue` một lần, BI / finance / AE đều truy vấn metric đó, không dashboard nào tự viết lại `sum(amount) where ...`.
3. *Các ngày cũ bị ảnh hưởng có tự được tính lại không?*
   **Lần này có**, nhưng do may mắn về dữ liệu chứ không phải do incremental tự sửa:
   - 3 đơn đổi sang `returned` có `_loaded_at` mới → `fct_orders` (merge theo `order_id`) nhặt được trạng thái mới.
   - `fct_daily_revenue` thấy ngày 29/12 có dòng `_loaded_at` mới → delete+insert **cả ngày 29/12** → tính lại doanh thu với quy tắc mới.
   - Test đỏ chặn build ngày 8 nên watermark chưa tiến lên, lần build sau khi sửa vẫn thấy các dòng này.
   - `customer_lifetime` là table, mỗi lần build tính lại toàn bộ.

   Khi nào **không** tự tính lại:
   - **Đổi quy tắc mà dữ liệu không đổi.** Ví dụ tài chính bảo "từ nay đơn `placed` cũng chưa tính doanh thu": không dòng nào có `_loaded_at` mới → incremental không động vào ngày cũ → phải backfill có chủ đích.
   - **Nguồn sửa dữ liệu mà không cập nhật `_loaded_at`**: incremental không thấy (chính là P4).

   → Incremental chỉ xử lý **dữ liệu mới**, không xử lý **code mới**. Đổi logic thì phải tự hỏi: các dòng cũ có cần tính lại không?
