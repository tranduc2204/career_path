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
  Không cần backfill nếu code đúng ngay từ đầu: xem câu postmortem 3.

**Lỗi tự gây ra khi sửa: `int_orders` lọc thay vì gắn cờ**
- Lúc sửa P3 mình thêm `where is_revenue_order` vào `int_orders`. Nhìn qua thì vô hại (mart cũng lọc đơn không tính doanh thu), `check.py P3` trên DB đang có vẫn PASS. Nhưng chạy `./scripts/replay.sh 8` từ đầu thì **I5 và P3 FAIL**:
  ```
  2025-12-29: có (6 đơn, 658.85), cần (3 đơn, 449.93)
  ```
- **Vì sao:** ngày 29/12 chỉ có 3 đơn 1013–1015 mang `_loaded_at` mới (2026-01-09), và chính 3 đơn đó chuyển sang `returned`. `int_orders` lọc mất chúng → `list_new_orders` của `fct_daily_revenue` không thấy dòng mới nào của 29/12 → không delete+insert ngày đó → dòng cũ (vẫn tính 3 đơn trả hàng) ở lại mãi.
- **Sửa:** bỏ `where is_revenue_order` khỏi `int_orders`, chỉ giữ cột cờ. Lọc ở **bước tổng hợp cuối** của mart: `case when is_revenue_order` trong `select ... group by` của `fct_daily_revenue`, `where is_revenue_order` trong `customer_lifetime` (table, không có watermark nên lọc ở `where` được).
  - ⚠️ Chuyển `where is_revenue_order` vào CTE `orders` của `fct_daily_revenue` cũng **sai y hệt**: `list_new_orders` đọc từ CTE đó nên vẫn không thấy 3 đơn `returned` (đã thử `replay.sh 8`: I5/P3 vẫn FAIL, 29/12 = 6 đơn, 658.85). Mọi bước dùng để **phát hiện ngày cần tính lại** phải đọc dữ liệu chưa lọc; chỉ bước **tính số** mới lọc.
- **Phải full-refresh sau khi sửa code:**
  ```bash
  dbt build -s int_orders+ --full-refresh
  ```
  Sửa code xong mà chỉ `dbt build` thường thì **không đủ**: watermark `max(max_loaded_at)` của `fct_daily_revenue` đã tiến tới dữ liệu ngày 8, 3 dòng `returned` (`_loaded_at` 2026-01-09) không còn "mới" nữa → 29/12 vẫn sai. Bảng incremental không tự sửa lỗi do code cũ gây ra (giống ý ở câu 3: incremental xử lý dữ liệu mới, không xử lý code mới). `fct_daily_revenue` không đặt `full_refresh=false` nên full-refresh được; nếu là bảng có khoá bảo vệ (như `fct_events`) thì phải backfill có chủ đích theo khoảng ngày.
  - Replay từ ngày 0 với code đã sửa thì không cần hook: mọi ngày được build bằng code đúng. Full-refresh chỉ cần cho DB đang chạy dở đã bị code lỗi nạp vào.
- **Bài học:** tầng intermediate **gắn cờ, không lọc**. Model incremental phía sau phải thấy được cả dòng vừa *rời khỏi* tập doanh thu thì mới biết cần tính lại ngày đó. Lọc ở intermediate là giấu mất chính thay đổi mà incremental cần để kích hoạt.
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
   - Điều kiện ngầm: tầng phía trên **không được lọc mất** dòng thay đổi. Nếu `int_orders` có `where is_revenue_order` thì 3 đơn `returned` biến mất trước khi tới `fct_daily_revenue` → 29/12 không được tính lại (xem mục "Lỗi tự gây ra khi sửa" ở trên).
   - `customer_lifetime` là table, mỗi lần build tính lại toàn bộ.

   Khi nào **không** tự tính lại:
   - **Đổi quy tắc mà dữ liệu không đổi.** Ví dụ tài chính bảo "từ nay đơn `placed` cũng chưa tính doanh thu": không dòng nào có `_loaded_at` mới → incremental không động vào ngày cũ → phải backfill có chủ đích.
   - **Nguồn sửa dữ liệu mà không cập nhật `_loaded_at`**: incremental không thấy (chính là P4).

   → Incremental chỉ xử lý **dữ liệu mới**, không xử lý **code mới**. Đổi logic thì phải tự hỏi: các dòng cũ có cần tính lại không?







# tình huống P4 là 
ngày 9 backend phát hiện thiếu phí ship $5 cho các đơn ngày 27/12, chạy `UPDATE` thẳng vào database mà không đổi `updated_at` / `_loaded_at`. Mọi watermark đều không thấy → dùng backfill có chủ đích theo `order_date`.

### P4 — Ngày 9: nguồn sửa ngầm số liệu cũ
- **Phát hiện lúc / bởi:** `dbt build` sáng ngày 9, test đối soát `audit_fct_orders_vs_full` (bài I9) đỏ, 12 dòng (6 dòng "thiếu/sai" + 6 dòng "thừa" của cùng 6 đơn). Kế toán trưởng: "doanh thu 27/12 lệch sổ sách đúng $30, backend bảo sửa rồi mà?".
- **Ảnh hưởng:**
  - `fct_orders`: 6 đơn 1001–1006 (ngày 2025-12-27) giữ `amount` cũ, mỗi đơn thiếu $5.
  - `fct_daily_revenue`: 27/12 = 781.78, đúng phải là 811.78 (thiếu $30).
  - `fct_orders_pit`: test đối soát đỏ → bị SKIP → đứng yên ở số ngày 8 (83 đơn, nguồn có 89).
  - Không có test đối soát thì tất cả **xanh mà vẫn sai**, sai vĩnh viễn (xem câu 1).
- **Nguyên nhân gốc:** backend sửa dữ liệu bằng `UPDATE` tay, không cập nhật `updated_at` / `_loaded_at`. Hai model incremental đọc orders đều lọc `_loaded_at > watermark` → 6 dòng bị sửa có `_loaded_at` cũ (2026-01-01) → không bao giờ được nạp lại. View/table phía trên (`stg_orders`, `int_orders`) thì đã đúng ngay.
- **Cách sửa:**
  1. **Code:** thêm "cửa backfill" vào cả `fct_orders` và `fct_daily_revenue`:
     ```sql
     where _loaded_at > (select max(...) from {{ this }})
     {% if var('backfill_start', none) %}
         or order_date between '{{ var("backfill_start") }}' and '{{ var("backfill_end") }}'
     {% endif %}
     ```
     Dùng `or` chứ không thay watermark: vừa backfill vừa nạp dữ liệu mới, watermark không nhảy qua dòng chưa xử lý.
  2. **Vận hành:** runbook `scripts/hooks/after_day_9.sh`:
     ```bash
     dbt build -s fct_orders+ fct_daily_revenue+ --vars '{backfill_start: 2025-12-27, backfill_end: 2025-12-27}'
     ```
  3. **Kiểm tra:** query lệch `stg_orders` vs `fct_orders` ra 0 dòng; `audit_fct_orders_vs_full` xanh lại (chạy luôn trong `dbt build` của hook); `replay.sh 9` (bản sao) 31 pass, 0 fail.
- **Phòng ngừa:** test đối soát định kỳ cho **mọi** bảng incremental (hiện chỉ có cho `fct_orders`), full refresh định kỳ cho bảng nhỏ, yêu cầu nguồn cập nhật `updated_at` bằng trigger hoặc dùng CDC (câu 2).

**Vì sao phải backfill cả 2 fct (`fct_orders` và `fct_daily_revenue`)?**

Lineage của dữ liệu `raw.orders`:
```
raw.orders → stg_orders (view) ─┬→ int_orders (view) ─┬→ fct_daily_revenue (incremental)  ← cần backfill
                                │                     └→ customer_lifetime (table)        đúng sẵn
                                ├→ fct_orders (incremental) → fct_orders_pit (table)      ← cần backfill + build lại con
                                └→ customer_order_summary (table)                         đúng sẵn
```
1. **Chỉ bảng incremental mới "nhớ" số cũ.** View chạy lại mỗi lần query, table tính lại toàn bộ mỗi lần build → tự đúng ngay khi nguồn đổi. Incremental giữ kết quả cũ và chỉ xử lý dòng mà watermark cho là mới → chỉ chúng cần backfill. Trong lab có đúng 2 bảng incremental đọc orders: `fct_orders` và `fct_daily_revenue` (các bảng `fct_events*` đọc events, `dim_customers_scd2_manual` đọc customers).
2. **Hai bảng là anh em, không phải cha con.** `fct_daily_revenue` đọc `int_orders` ← `stg_orders`, **không đọc `fct_orders`**. Backfill `fct_orders` xong thì doanh thu 27/12 vẫn sai, và `fct_orders+` không bao gồm `fct_daily_revenue`. Mỗi bảng incremental có watermark riêng, trí nhớ riêng → phải bảo từng bảng tính lại.
3. **Vì sao có dấu `+`.** Bảng con của `fct_orders` (`fct_orders_pit`) đọc nội dung của `fct_orders`. Sáng ngày 9 nó bị SKIP vì test đối soát đỏ, nên đứng ở số ngày 8. Lúc đầu mình chạy tay `dbt run -s fct_orders` (không `+`) → `fct_orders` đúng nhưng `fct_orders_pit` vẫn cũ → S6 FAIL (83/89 đơn). `fct_orders+` build lại cả con. `fct_daily_revenue+` hiện chưa có con, để sẵn cho model viết sau.
4. **Vì sao `dbt build` chứ không `dbt run`.** `build` chạy cả test → `audit_fct_orders_vs_full` chạy lại ngay sau backfill. Backfill sai khoảng ngày thì test đỏ, `dbt build` trả lỗi, `set -e` dừng hook, `replay.sh` in ⚠️. Hook tự kiểm tra kết quả, không "nói dối".

→ Quy tắc: nguồn sửa ngầm thì đi theo lineage từ bảng nguồn xuống, **liệt kê mọi bảng incremental** trên đường đi, backfill từng bảng kèm `+`.

**Postmortem**
1. *Không làm bài I9 thì ai phát hiện, sau bao lâu?*
   Không test nào đỏ: mọi test đều kiểm tra dữ liệu **trong** bảng (unique, not_null...), không so bảng với nguồn. Người phát hiện là **kế toán** khi đối chiếu sổ sách, thường lúc khoá sổ cuối tháng, tức vài tuần sau. Lệch chỉ $30 thì có thể không ai phát hiện. Và vì `_loaded_at` không đổi, incremental **không bao giờ tự lành**: số sai nằm đó mãi.
   Ngay cả có I9, test đối soát chỉ phủ `fct_orders`. Nếu backend chỉ sửa cột mà `fct_orders` không lấy, hoặc chỉ `fct_daily_revenue` lệch, thì vẫn không ai biết → thiếu test đối soát cho `fct_daily_revenue`.
2. *3 cách phòng ngừa:*
   | Cách | Làm gì | Được / mất |
   |---|---|---|
   | Test đối soát định kỳ | so bảng incremental với kết quả tính lại từ nguồn (I9), thêm cho `fct_daily_revenue`; bảng lớn thì chỉ so N ngày gần nhất hoặc so tổng theo ngày | phát hiện sáng hôm sau; không tự sửa |
   | Full refresh định kỳ cho bảng nhỏ | lịch hằng tuần `dbt build --full-refresh -s fct_orders fct_daily_revenue` | tự lành tối đa sau 1 tuần; chỉ hợp bảng nhỏ, bảng có `full_refresh=false` thì không làm được |
   | Sửa ở nguồn | trigger DB tự cập nhật `updated_at` mỗi lần `UPDATE`, hoặc dùng CDC (đọc log thay đổi của DB) | xử lý gốc rễ: mọi thay đổi đều có dấu thời gian mới → watermark thấy; cần backend hợp tác |
   Thêm: thoả thuận với backend là sửa dữ liệu thì báo team data (lần này họ "đã sửa từ hôm qua" mà không ai biết).
3. *Backfill theo `order_date` sai khoảng ngày thì rủi ro gì?*
   - **Hẹp quá (sót ngày):** ngày bị sót sai mãi, không tự lành (`_loaded_at` không đổi). Hook vẫn chạy "thành công" → tưởng đã sửa xong. Chỉ test đối soát mới bắt được.
   - **Rộng quá:** tốn chi phí, nhưng **không sai**: merge theo `order_id` ghi đè bằng giá trị hiện tại của `stg_orders`, delete+insert tính lại cả ngày từ nguồn → chạy rộng hay chạy nhiều lần đều ra cùng kết quả (idempotent). Điều kiện là dùng `or` với watermark; nếu **thay** watermark bằng khoảng ngày thì backfill có thể làm watermark nhảy qua dòng mới chưa xử lý → mất dữ liệu ở ngày khác.
   - **Sai chiều:** khoảng ngày lấy theo lời backend ("đơn ngày 27/12"). Nếu họ sửa theo tiêu chí khác (theo khách, theo sản phẩm, theo giờ địa phương khác múi giờ của `order_date`) thì đơn bị sửa rải rác nhiều ngày, khoảng `order_date` không phủ hết → phải lấy danh sách ngày từ **kết quả đối soát**, không tin lời mô tả.
   - **Ngày biến mất khỏi nguồn:** delete+insert chỉ xoá ngày có trong batch mới; ngày bị xoá hẳn ở nguồn thì backfill không dọn được.
