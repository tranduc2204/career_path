# 03 · Kiểm soát frame trong production và khác biệt giữa các warehouse

## 1. Sáu quy tắc kiểm soát

1. **Có `ORDER BY` trong `OVER` + hàm tổng hợp/giá trị thì ghi frame tường minh, cả hai đầu.**
   Không viết `sum(x) over (order by d)`; viết `sum(x) over (order by d rows between unbounded preceding and current row)`. Người review đọc là hiểu ngay, và code chuyển sang engine khác không đổi nghĩa (Snowflake có mặc định riêng cho `LAST_VALUE`).

2. **Dùng ROWS thì ORDER BY phải unique trong partition.** Thêm tie-breaker (`id`, `loaded_at`...). Kiểm chứng bằng test:
   ```yaml
   # models/schema.yml
   - name: fct_giao_dich
     data_tests:
       - dbt_utils.unique_combination_of_columns:
           arguments:
             combination_of_columns: [khach_hang_id, thoi_diem, giao_dich_id]
   ```
   Nếu không có cột nào làm tie-breaker được thì nghiệp vụ đang muốn tính **theo mốc**, và bạn nên dùng RANGE/GROUPS, hoặc gộp về mốc trước.

3. **Cửa sổ thời gian thì không dùng `ROWS n PRECEDING` trên dữ liệu có lỗ.** Dùng `RANGE ... INTERVAL`, hoặc densify bằng date spine rồi mới dùng ROWS. Một cách tự kiểm: thêm cột `count(*) over w`; nếu nó luôn bằng N kể cả quanh ngày nghỉ thì bạn đang đếm dòng chứ không đếm ngày.

4. **Khung có thể rỗng thì quyết định NULL hay 0 theo nghiệp vụ.** Dòng đầu với `... AND 1 PRECEDING`, dòng cuối với `1 FOLLOWING AND ...`. "Chưa có dữ liệu" (NULL) khác "bằng 0".

5. **Muốn "giá trị cuối" thì mở tới `UNBOUNDED FOLLOWING`**, hoặc đảo `ORDER BY ... DESC` rồi dùng `FIRST_VALUE`.

6. **Ghi kỳ vọng ca biên thành test.** Ví dụ singular test "lũy kế ngày cuối = tổng cả nhóm":
   ```sql
   -- tests/assert_luy_ke_cuoi_bang_tong.sql
   with x as (
       select cua_hang, luy_ke,
              sum(doanh_thu) over (partition by cua_hang) as tong,
              row_number() over (partition by cua_hang order by ngay desc) as rn
       from {{ ref('fct_doanh_thu_luy_ke') }}
   )
   select * from x where rn = 1 and abs(luy_ke - tong) > 0.01
   ```

## 2. Phương ngữ: cái gì chạy ở đâu

Cột DuckDB đã được kiểm chứng trên DuckDB 1.5.6 (lab này). Các cột khác viết theo docs/kinh nghiệm tới 2026. Warehouse cập nhật liên tục, nên khi gặp lỗi cú pháp hãy tra lại docs của bản bạn đang dùng.

| Tính năng | DuckDB | Postgres (≥ 11) | BigQuery | Snowflake |
|---|---|---|---|---|
| `ROWS BETWEEN ...` | ✅ | ✅ | ✅ | ✅ |
| `RANGE` với offset số | ✅ | ✅ | ✅ (ORDER BY 1 biểu thức **số**) | ✅ (bản mới, kiểm tra docs) |
| `RANGE` với `INTERVAL` (ngày/giờ) | ✅ | ✅ | ❌, dùng `UNIX_DATE(ngay)` / `UNIX_SECONDS(ts)` rồi offset số | ✅ (bản mới, kiểm tra docs) |
| `GROUPS` | ✅ | ✅ | ❌ | ❌ |
| `EXCLUDE CURRENT ROW / GROUP / TIES` | ✅ | ✅ | ❌ | ❌ |
| `IGNORE NULLS` (FIRST/LAST_VALUE, LAG/LEAD) | ✅ | ❌ ở các bản phổ biến | ✅ | ✅ |
| `QUALIFY` | ✅ | ❌ (dùng subquery) | ✅ | ✅ |
| Frame cho `ROW_NUMBER`/`RANK` | bỏ qua | bỏ qua | **lỗi** | lỗi |
| Mặc định `LAST_VALUE(...) OVER (ORDER BY ...)` | chuẩn: tới CURRENT ROW | chuẩn | chuẩn | **cả partition** (lệch chuẩn) |

Bài học từ dòng cuối: adventure_works của bạn chạy trên Snowflake, nên một model `LAST_VALUE` không ghi frame có thể chạy đúng ở đó, rồi sai âm thầm khi port sang BigQuery (GĐ2). Quy tắc 1 giải quyết luôn chuyện này.

## 3. Viết portable khi thiếu tính năng

| Thiếu | Thay bằng | Bài |
|---|---|---|
| `GROUPS` | `GROUP BY` mốc → `ROWS` trên bảng đã gộp → join ngược lại | B13 |
| `RANGE INTERVAL` | (a) BigQuery: `RANGE BETWEEN 6 PRECEDING AND CURRENT ROW` trên `ORDER BY UNIX_DATE(ngay)`; (b) date spine + `ROWS` | B07 bonus |
| `EXCLUDE CURRENT ROW` | `(sum(x) over p - x) / nullif(count(x) over p - 1, 0)` | B14 |
| `IGNORE NULLS` | `count(x)` lũy kế tạo "nhóm", rồi `max(x) over (partition by ..., nhom)` | B10 bonus |
| `QUALIFY` | CTE tính window, query ngoài `WHERE` | — |

Ví dụ BigQuery cho 7 ngày lịch:

```sql
-- BigQuery
sum(doanh_thu) over (
    partition by cua_hang
    order by unix_date(ngay)
    range between 6 preceding and current row
)
```

## 4. Các pattern AE hay gặp và frame tương ứng

| Pattern | Lõi | Lưu ý frame |
|---|---|---|
| **Dedup bản mới nhất** | `qualify row_number() over (partition by id order by updated_at desc, _loaded_at desc) = 1` | không có frame; ORDER BY phải unique, nếu không mỗi lần build chọn một bản khác |
| **SCD2 `valid_to`** | `lead(valid_from) over (partition by id order by valid_from)` | LEAD không dùng frame; 2 bản ghi cùng `valid_from` sẽ ra khoảng hiệu lực 0 giây |
| **Sessionization** | `lag` → cờ phiên mới → `sum(co) over (... rows unbounded preceding)` | xem B15; biên `>` hay `>=` phải theo đặc tả |
| **Gaps & islands** (chuỗi ngày liên tiếp) | `ngay - row_number() over (partition by k order by ngay) * interval 1 day` làm khoá nhóm | không có frame |
| **Running total / số dư** | `sum() over (... rows between unbounded preceding and current row)` | ROWS + tie-breaker, hoặc RANGE nếu muốn theo mốc (B02 và B03) |
| **Rolling N ngày** | `RANGE INTERVAL` hoặc spine + `ROWS` | B06 và B07 |
| **Tỉ trọng / % of total** | `x / sum(x) over (partition by nhom)` | **không** ORDER BY (B04) |
| **Forward fill** dữ liệu thưa | `last_value(x ignore nulls) over (... rows between unbounded preceding and current row)` | B10 |

## 5. Hiệu năng (đủ biết khi nào cần lo)

- `UNBOUNDED PRECEDING AND CURRENT ROW` (lũy kế) và cả partition thì rẻ: engine tính một lượt trên partition đã sắp.
- Cửa sổ trượt `n PRECEDING` với `SUM/AVG/COUNT` cũng rẻ (cộng vào, trừ ra). Với `MIN/MAX`/`MEDIAN` trên khung trượt lớn thì đắt hơn, vì phải duy trì cấu trúc phụ.
- Partition lệch (một khách có 50 triệu dòng) dồn hết vào 1 worker. Trên BigQuery/Snowflake, hãy xem query profile ở [bai-tap-performance](../../bai-tap-performance/README.md).
- Nhiều window **cùng** `PARTITION BY` + `ORDER BY` thì engine sort một lần. Dùng `WINDOW w` để giữ chúng giống hệt nhau.

## 6. Câu hỏi phỏng vấn hay gặp

1. Khác nhau giữa `ROWS` và `RANGE`? Cho ví dụ hai cái ra kết quả khác nhau. (§3 file 02)
2. Vì sao `LAST_VALUE` trả về chính dòng hiện tại? Sửa thế nào?
3. Tính "doanh thu 7 ngày gần nhất" khi có ngày không bán được hàng?
4. Lũy kế của bạn thỉnh thoảng đổi giá trị giữa hai lần chạy, dù dữ liệu không đổi. Nguyên nhân?
5. BigQuery không có `GROUPS`/`EXCLUDE`, vậy làm sao viết lại?
6. `where` đặt trước hay sau window? Tác động lên lũy kế ra sao?
