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
cột order ở ngày 7 bị xóa đi và cần sử dụng kĩ thuậtt để enable hay visble cột để fix lỗi này 
 {% if 'order_status' in source_columns %}
            order_status
        {% elif 'status' in source_columns %}
            status
        {% else %}
            cast(null as varchar) as order_status
        {% endif %}




