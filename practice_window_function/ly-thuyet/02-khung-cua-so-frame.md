# 02 · Frame và cách kiểm soát UNBOUNDED

> Mọi ví dụ dùng bảng `t` (có trong `lab.duckdb`, cũng là bảng của phần A). Mở DuckDB và chạy thử từng câu:
> `duckdb lab.duckdb` hoặc `python -c "import duckdb; duckdb.connect('lab.duckdb').sql('from t').show()"`

```
 id | nhom | x | v
----+------+---+-----
  1 |  a   | 1 | 10
  2 |  a   | 2 | 20    ┐ peer (cùng x = 2)
  3 |  a   | 2 | 30    ┘
  4 |  a   | 4 | NULL
  5 |  a   | 5 | 50
  6 |  b   | 1 | 5     ┐ peer (cùng x = 1)
  7 |  b   | 1 | 15    ┘
  8 |  b   | 3 | 25
```

## 1. Frame là gì

Sau khi chia partition và sắp xếp, **mỗi dòng có frame riêng**: một đoạn liên tục của partition, được xác định tương đối so với dòng đó. Hàm tổng hợp và hàm giá trị chỉ "nhìn thấy" các dòng trong frame.

```
partition 'a' (đã sắp theo x):   id1   id2   id3   id4   id5
                                  ▲─────▲─────●                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW (đang ở id3)
                                              ●─────▲─────▲       ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING (đang ở id3)
                                        ▲─────●─────▲             ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING (đang ở id3)
```

## 2. Cú pháp frame và 5 loại đầu mút

```
{ ROWS | RANGE | GROUPS } BETWEEN <đầu dưới> AND <đầu trên> [ EXCLUDE ... ]
```

| Đầu mút | Nghĩa |
|---|---|
| `UNBOUNDED PRECEDING` | dòng **đầu tiên** của partition |
| `n PRECEDING` | lùi n (dòng / giá trị / nhóm, tuỳ ROWS/RANGE/GROUPS) |
| `CURRENT ROW` | dòng hiện tại (ROWS), hoặc **dòng hiện tại cùng các peer** (RANGE/GROUPS) |
| `n FOLLOWING` | tiến n |
| `UNBOUNDED FOLLOWING` | dòng **cuối cùng** của partition |

Quy tắc hợp lệ (DuckDB báo lỗi nếu vi phạm):
- Đầu dưới không được đứng sau đầu trên: `BETWEEN CURRENT ROW AND 1 PRECEDING` lỗi.
- `UNBOUNDED FOLLOWING` không làm đầu dưới, `UNBOUNDED PRECEDING` không làm đầu trên.
- Viết tắt `ROWS UNBOUNDED PRECEDING` = `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` (chỉ ghi đầu dưới thì đầu trên là CURRENT ROW).

### Frame mặc định khi bạn không ghi

| Trong `OVER` có... | Frame mặc định (chuẩn SQL) | Ý nghĩa |
|---|---|---|
| không có `ORDER BY` | cả partition: `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` | tổng / trung bình cả nhóm |
| có `ORDER BY` | **`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`** | lũy kế **gồm cả peer** |

Hai bẫy nằm ngay trong dòng thứ hai:
1. Mặc định là **RANGE** chứ không phải ROWS, nên các dòng cùng giá trị ORDER BY được gộp lại (§3).
2. Đầu trên là **CURRENT ROW**, nên `LAST_VALUE` chỉ thấy tới dòng hiện tại (§5).

> Snowflake là ngoại lệ đáng nhớ: với `FIRST_VALUE`/`LAST_VALUE`/`NTH_VALUE`, docs của Snowflake ghi frame mặc định là **cả partition** (lệch chuẩn ANSI). Cùng một câu `LAST_VALUE(...) OVER (ORDER BY ...)` chạy trên Snowflake và trên BigQuery/Postgres/DuckDB sẽ ra kết quả khác nhau. Xem [03 §2](03-kiem-soat-va-phuong-ngu.md#2-phương-ngữ-cái-gì-chạy-ở-đâu).

### Các frame hay dùng

| Nghiệp vụ | Frame |
|---|---|
| Lũy kế từng dòng (running total) | `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` |
| Tổng / tỉ trọng trên cả nhóm | không `ORDER BY`, hoặc `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` |
| Phần còn lại tính từ hôm nay | `ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING` |
| Phần còn lại, **không** tính hôm nay | `ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING` |
| Mọi dòng **trước** hôm nay | `ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING` |
| Trung bình trượt N dòng | `ROWS BETWEEN N-1 PRECEDING AND CURRENT ROW` |
| Cửa sổ N ngày lịch | `RANGE BETWEEN INTERVAL (N-1) DAY PRECEDING AND CURRENT ROW` |
| Giá trị cuối thật sự của nhóm | `LAST_VALUE(...)` + `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` |

## 3. ROWS, RANGE, GROUPS và khái niệm peer

**Peer** là các dòng có **cùng giá trị ORDER BY** trong một partition. Ba chế độ khác nhau ở cách đối xử với peer:

| Chế độ | Đơn vị đo khoảng cách | `CURRENT ROW` nghĩa là |
|---|---|---|
| `ROWS` | số **dòng vật lý** | đúng dòng này |
| `RANGE` | **giá trị** của cột ORDER BY | dòng này **cùng tất cả peer** |
| `GROUPS` | số **nhóm peer** | nhóm peer chứa dòng này |

So sánh trên nhóm `a` (A1, A2 trong phần A):

```sql
select id, x, v,
  sum(v) over (partition by nhom order by x)                         as mac_dinh_range,
  sum(v) over (partition by nhom order by x, id
               rows between unbounded preceding and current row)     as rows_unique
from t where nhom = 'a' order by id;
```

| id | x | v | mac_dinh_range | rows_unique |
|---|---|---|---|---|
| 1 | 1 | 10 | 10 | 10 |
| 2 | 2 | 20 | **60** | 30 |
| 3 | 2 | 30 | **60** | 60 |
| 4 | 4 | NULL | 60 | 60 |
| 5 | 5 | 50 | 110 | 110 |

id2 ra 60 vì với RANGE, `CURRENT ROW` kéo theo cả peer id3.

### Chọn chế độ nào?

- **Muốn từng dòng một** (số dư sau từng giao dịch, số thứ tự sự kiện): dùng **ROWS**, và **ORDER BY phải unique** (thêm cột tie-breaker như `giao_dich_id`). Nếu dùng ROWS mà ORDER BY có trùng, thứ tự giữa các peer là **ngẫu nhiên**, kết quả có thể đổi giữa 2 lần chạy. Đây là loại bug khó tìm nhất vì đôi khi "chạy lại thì hết". → bài B02
- **Muốn theo mốc giá trị** (số dư tại thời điểm T gồm mọi giao dịch cùng T, doanh thu 7 ngày lịch): dùng **RANGE**. → bài B03, B07
- **Muốn theo N mốc khác nhau** (3 thời điểm gần nhất, dù mỗi thời điểm có bao nhiêu dòng): dùng **GROUPS**. → bài B12

## 4. Offset `n PRECEDING / n FOLLOWING`: 7 dòng không phải 7 ngày

| | `6 PRECEDING` nghĩa là |
|---|---|
| `ROWS` | 6 dòng phía trên |
| `RANGE` | mọi dòng có `x >= x_hiện_tại - 6` (ORDER BY phải là **1 biểu thức** số / ngày / timestamp) |
| `GROUPS` | 6 nhóm peer phía trên |

Với dữ liệu ngày **có lỗ** (cửa hàng nghỉ), ví dụ CH02 nghỉ chủ nhật:

```
ngay:     01  02  03  04  05  07  08        (06 là chủ nhật, không có dòng)
                                     ▲ đang ở 08
ROWS 6 PRECEDING          → 02 03 04 05 07 08 + 01   = 7 dòng, trải 8 ngày lịch
RANGE INTERVAL 6 DAY PREC → 02 03 04 05 07 08        = 6 dòng, đúng 7 ngày lịch (02..08)
```

Hai cách cho cửa sổ thời gian:
1. `RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW` (DuckDB, Postgres; BigQuery thì đổi ngày sang số bằng `UNIX_DATE`).
2. **Date spine**: lấp đầy mọi ngày bằng 0 (`dbt_utils.date_spine`), khi đó 1 dòng = 1 ngày và `ROWS` đúng nghĩa. Cách này chạy ở mọi nơi. → bài B07 bonus

Với RANGE trên **giá trị** (A7): `range between 1 preceding and 1 following` tại id4 (x=4) lấy các dòng có x ∈ [3, 5], tức là id4, id5. Đó là khoảng **giá trị**, không phải dòng kề.

## 5. Hàm giá trị: bẫy LAST_VALUE

```sql
last_value(v) over (partition by nhom order by x, id)
-- frame mặc định: RANGE UNBOUNDED PRECEDING .. CURRENT ROW
-- → dòng cuối của frame chính là dòng hiện tại → trả về chính v
```

Kết quả: `10 20 30 NULL 50 ...` (A4), không phải "giá trị cuối của nhóm".

Sửa bằng cách **mở đầu trên tới UNBOUNDED FOLLOWING**:

```sql
last_value(v) over (partition by nhom order by x, id
                    rows between unbounded preceding and unbounded following)
```

`FIRST_VALUE` với frame mặc định thì đúng (đầu dưới vốn là UNBOUNDED PRECEDING), nhưng nếu dùng chung `WINDOW w` với `LAST_VALUE` thì vẫn nên ghi frame đầy đủ. Các cách khác cho "giá trị cuối":
- `FIRST_VALUE(v) OVER (... ORDER BY x DESC)`: đảo thứ tự, frame mặc định đã đủ.
- `QUALIFY ROW_NUMBER() ... = 1` nếu chỉ cần 1 dòng mỗi nhóm.
- `ARG_MAX(v, x)` / `MAX_BY` (DuckDB, Snowflake `MAX_BY`, BigQuery `ARRAY_AGG(... ORDER BY ... LIMIT 1)`) nếu đang GROUP BY.

### IGNORE NULLS: forward fill

```sql
last_value(v ignore nulls) over (partition by nhom order by x, id
                                 rows between unbounded preceding and current row)
```

Lấy giá trị **khác NULL gần nhất** tính tới dòng hiện tại (A6: id4 → 30). Back fill thì làm ngược lại: `first_value(v ignore nulls) over (... rows between current row and unbounded following)`. → bài B10

## 6. Ca biên: khung rỗng, loại dòng hiện tại, NULL

### Khung rỗng
`ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING` ở dòng cuối không có dòng nào: `SUM/AVG/MIN/MAX` ra **NULL**, `COUNT` ra **0** (A9). Nghiệp vụ muốn 0 thì phải `COALESCE(..., 0)`. → B08, B11

### Loại dòng hiện tại ra khỏi frame

| Cách | Khi nào |
|---|---|
| `... AND 1 PRECEDING` / `1 FOLLOWING AND ...` | loại dòng hiện tại ở đầu/cuối khung (kỷ lục trước đó) → B09 |
| `EXCLUDE CURRENT ROW` | loại dòng hiện tại ở **giữa** khung (so với các ngày khác) → B14 |
| `EXCLUDE GROUP` | loại dòng hiện tại cùng mọi peer |
| `EXCLUDE TIES` | loại các peer nhưng **giữ** dòng hiện tại |
| `(SUM() OVER p - x) / NULLIF(COUNT() OVER p - 1, 0)` | engine không có EXCLUDE (BigQuery, Snowflake) |

### NULL
- Hàm tổng hợp **bỏ qua NULL** trong frame: `COUNT(v)` ≠ `COUNT(*)` (A10), `AVG` chia cho số dòng khác NULL.
- NULL **trong cột ORDER BY** với RANGE: các dòng NULL là peer của nhau, frame offset của một dòng NULL chỉ gồm các dòng NULL. Vị trí của chúng phụ thuộc `NULLS FIRST/LAST`, và mặc định mỗi engine một khác. Hãy lọc hoặc `COALESCE` trước.

## 7. Quy trình 3 câu hỏi trước mỗi window

1. **Đơn vị là gì?** Từng dòng → ROWS (ORDER BY unique). Theo giá trị/thời gian → RANGE. Theo số mốc → GROUPS.
2. **Hai đầu mút ở đâu?** Có gồm dòng hiện tại không, có nhìn về tương lai không. Viết ra **cả hai** đầu, đừng dựa vào mặc định.
3. **Ca biên ra gì?** Dòng đầu, dòng cuối, khung rỗng, peer, NULL, ngày bị thiếu. Ghi kết quả mong muốn trước rồi mới viết query.

→ Tiếp: [03 · Kiểm soát trong production và phương ngữ](03-kiem-soat-va-phuong-ngu.md)
