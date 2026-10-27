# 01 · Nền tảng window function

> Mục tiêu: hiểu window function chạy ở đâu trong query, gồm những phần nào, và **hàm nào có quan tâm tới frame**. Chính điều cuối quyết định khi nào bạn phải "kiểm soát UNBOUNDED".

## 1. Window function khác GROUP BY ở đâu

| | `GROUP BY` | Window function |
|---|---|---|
| Số dòng output | gộp lại, mỗi nhóm 1 dòng | **giữ nguyên** số dòng |
| Dùng được cột chi tiết cùng lúc với số tổng? | không (trừ khi join lại) | có |
| Ví dụ | tổng doanh thu mỗi cửa hàng | mỗi ngày kèm lũy kế, kèm % so với tổng tháng |

```sql
select
    cua_hang, ngay, doanh_thu,
    sum(doanh_thu) over (partition by cua_hang) as tong_cua_hang   -- mỗi dòng vẫn còn
from doanh_thu_ngay
```

## 2. Giải phẫu một lời gọi

```
SUM(doanh_thu)                                  ← hàm + đối số
    [IGNORE NULLS]                              ← chỉ với FIRST/LAST/NTH_VALUE, LAG/LEAD (tuỳ engine)
    [FILTER (WHERE ...)]                        ← DuckDB/Postgres
OVER (
    PARTITION BY cua_hang                       ← chia thành các "cửa sổ độc lập"
    ORDER BY ngay                               ← sắp thứ tự TRONG từng partition
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW    ← FRAME: tập con của partition, tính riêng cho từng dòng
)
```

Ba tầng lồng nhau, tính **cho từng dòng hiện tại**:

```
bảng ──► partition (cùng cua_hang) ──► sắp theo ORDER BY ──► frame của dòng hiện tại ──► hàm tính trên frame
```

- **PARTITION BY** bỏ trống thì cả bảng là một partition.
- **ORDER BY** bỏ trống thì không có khái niệm "trước/sau", và frame mặc định là cả partition (xem [02 §2](02-khung-cua-so-frame.md#2-cú-pháp-frame-và-5-loại-đầu-mút)).
- **Frame** bỏ trống thì engine dùng frame mặc định. Đây là nguồn gốc của phần lớn bug.

## 3. Window chạy ở bước nào của query

Thứ tự xử lý logic (không phải thứ tự bạn viết):

```
FROM / JOIN → WHERE → GROUP BY → HAVING → WINDOW → QUALIFY → SELECT (DISTINCT) → ORDER BY → LIMIT
```

Hệ quả thực tế:

1. **Không dùng được window trong `WHERE`.** Phải lọc bằng `QUALIFY` (DuckDB, BigQuery, Snowflake) hoặc bọc subquery/CTE (Postgres).
   ```sql
   select * from su_kien_don
   qualify row_number() over (partition by don_id order by thoi_diem desc) = 1
   ```
2. **`WHERE` lọc trước khi window tính.** Nếu bạn `WHERE ngay >= '2026-10-01'` thì lũy kế bắt đầu lại từ 01/10, chứ không phải lũy kế từ đầu rồi mới cắt. Muốn lũy kế toàn thời gian mà chỉ hiển thị tháng 10 thì tính window trong CTE, rồi lọc ở query ngoài.
3. **Window chạy sau `GROUP BY`**, nên viết được `sum(sum(x)) over (...)`: hàm trong là aggregate của GROUP BY, hàm ngoài là window.
   ```sql
   select cua_hang, sum(doanh_thu) as dt,
          sum(sum(doanh_thu)) over () as tong_toan_chuoi
   from doanh_thu_ngay group by cua_hang
   ```
4. `ORDER BY` bên trong `OVER` **không** sắp output. Muốn output có thứ tự thì phải có `ORDER BY` cuối query.

## 4. Bốn họ hàm và họ nào quan tâm tới frame

Phần này quan trọng nhất của file.

| Họ | Hàm | Dùng frame? | Ghi chú |
|---|---|---|---|
| Xếp hạng | `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `PERCENT_RANK`, `CUME_DIST` | **Không**, luôn xét cả partition | DuckDB im lặng bỏ qua frame nếu bạn ghi; BigQuery báo lỗi |
| Dịch chuyển | `LAG`, `LEAD` | **Không**, nhảy theo vị trí dòng | `LAG(x, 1, giá_trị_mặc_định)` |
| Giá trị | `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE` | **Có**: lấy dòng đầu/cuối/thứ n **của frame** | `LAST_VALUE` + frame mặc định là bẫy số 1 |
| Tổng hợp | `SUM`, `AVG`, `COUNT`, `MIN`, `MAX`, `STRING_AGG`, `ARRAY_AGG`... | **Có**: tính trên frame | khung rỗng → `NULL` (riêng `COUNT` → 0) |

Hai hệ quả:

- Với `ROW_NUMBER`/`RANK`/`LAG`/`LEAD` bạn **không cần** nghĩ tới `UNBOUNDED`. Thứ cần nghĩ là **ORDER BY có unique không** (xem [03 §1](03-kiem-soat-va-phuong-ngu.md)).
- Với họ giá trị và họ tổng hợp, mỗi lần có `ORDER BY` trong `OVER` bạn **phải tự quyết frame**. Ba file tiếp theo đều xoay quanh việc này.

## 5. Đặt tên cửa sổ bằng `WINDOW`

Khi nhiều cột dùng cùng một cửa sổ, đặt tên để tránh copy và tránh lệch frame giữa các cột:

```sql
select
    cua_hang, ngay,
    avg(doanh_thu) over w as tb_7_dong,
    count(*)       over w as so_dong
from doanh_thu_ngay
window w as (partition by cua_hang order by ngay rows between 6 preceding and current row)
```

DuckDB, Postgres, BigQuery và Snowflake đều có mệnh đề `WINDOW`. Có thể kế thừa rồi thêm vào, ví dụ `over (w rows between ...)` khi `w` chưa có frame (cú pháp kế thừa khác nhau giữa các engine, kiểm tra trước khi dùng).

## 6. Tự kiểm tra

1. Vì sao `select ... where row_number() over (...) = 1` lỗi? Viết lại bằng 2 cách.
2. `LAG(doanh_thu) over (partition by cua_hang order by ngay rows between 6 preceding and current row)` ra kết quả gì khác so với không ghi frame?
3. Bạn cần "% doanh thu mỗi cửa hàng so với toàn chuỗi" ở bảng đã `GROUP BY cua_hang`. Viết một query, không join.

→ Tiếp: [02 · Frame và UNBOUNDED](02-khung-cua-so-frame.md)
