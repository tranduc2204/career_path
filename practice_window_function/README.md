# Window function: kiểm soát frame (ROWS / RANGE / GROUPS / UNBOUNDED)

Lý thuyết tiếng Việt cùng 27 bài tự chấm trên DuckDB. Trọng tâm là **frame**: `UNBOUNDED PRECEDING/FOLLOWING`, `CURRENT ROW`, `n PRECEDING`, peer, khung rỗng, `EXCLUDE`, và việc mỗi warehouse hiểu frame mặc định khác nhau.

## Mục lục

| Lý thuyết | Nội dung | Bài liên quan |
|---|---|---|
| [01 · Nền tảng](ly-thuyet/01-nen-tang.md) | window vs GROUP BY, thứ tự xử lý logic, `QUALIFY`, **họ hàm nào dùng frame**, `WINDOW` | — |
| [02 · Frame và UNBOUNDED](ly-thuyet/02-khung-cua-so-frame.md) | 5 loại đầu mút, frame mặc định, ROWS/RANGE/GROUPS và peer, 7 dòng ≠ 7 ngày, bẫy `LAST_VALUE`, `IGNORE NULLS`, khung rỗng, `EXCLUDE` | A1–A12, B01–B12, B14 |
| [03 · Kiểm soát và phương ngữ](ly-thuyet/03-kiem-soat-va-phuong-ngu.md) | 6 quy tắc + test dbt, bảng tính năng DuckDB/Postgres/BigQuery/Snowflake, cách viết portable, pattern AE | B13, B14, B15 |

## Bài tập

**Phần A: đoán kết quả** ([bai-tap/A-du-doan.txt](bai-tap/A-du-doan.txt)). Có 12 biểu thức window trên một bảng 8 dòng. Bạn đoán kết quả bằng giấy bút rồi điền vào file. Phần này luyện trực giác về frame, nên làm **trước** phần B.

**Phần B: viết query** ([bai-tap/](bai-tap/)). Mỗi bài là một file `.sql`, phần đầu file ghi đề và cột cần trả.

| Bài | Chủ đề | Bẫy chính |
|---|---|---|
| B01 | Lũy kế doanh thu | khởi động, ghi frame tường minh |
| B02 | **Sửa bug** lũy kế giao dịch | RANGE mặc định gộp peer, thiếu tie-breaker |
| B03 | Số dư theo mốc thời điểm | lần này RANGE mới đúng |
| B04 | Tỉ trọng trong tháng | tổng cả nhóm thì **không** ORDER BY |
| B05 | **Sửa bug** trạng thái cuối của đơn | `LAST_VALUE` + frame mặc định |
| B06 | Trung bình trượt 7 dòng | `ROWS n PRECEDING`, đếm số dòng trong khung |
| B07 | Tổng 7 ngày lịch | ngày nghỉ → phải dùng RANGE INTERVAL / date spine |
| B08 | Doanh thu 7 ngày tới | `FOLLOWING`, khung rỗng → 0 |
| B09 | Ngày lập kỷ lục | loại dòng hiện tại bằng `1 PRECEDING`, `>` khác `>=` |
| B10 | Điền giá bị thiếu | `IGNORE NULLS`, forward fill + back fill |
| B11 | Còn lại trong tháng | `1 FOLLOWING AND UNBOUNDED FOLLOWING` |
| B12 | Tổng 3 mốc gần nhất | `GROUPS` |
| B13 | B12 không dùng GROUPS | viết portable cho BigQuery/Snowflake |
| B14 | So với các ngày khác | `EXCLUDE CURRENT ROW`, partition 1 dòng |
| B15 | Chia phiên | `LAG` + lũy kế cờ, biên 30 phút |

Dữ liệu là "Mây Shop" (`scripts/du_lieu.py`): 4 cửa hàng có ngày nghỉ, ví điện tử với giao dịch trùng thời điểm và `giao_dich_id` không theo thời gian, sự kiện đơn hàng, bảng giá thưa có NULL.

## Chạy

Cần [uv](https://docs.astral.sh/uv/).

```bash
cd practice_window_function
uv sync && source .venv/bin/activate

python scripts/du_lieu.py        # tạo lab.duckdb để bạn xem dữ liệu, thử query
python scripts/check.py          # chấm tất cả (lúc đầu: B02, B05 FAIL vì có sẵn bug, còn lại SKIP)
python scripts/check.py B07      # chấm 1 bài;  A = cả phần A,  B = cả phần B
```

Thử query nhanh: dùng `duckdb lab.duckdb` (CLI), DuckDB UI (`duckdb -ui lab.duckdb`), hoặc
`python -c "import duckdb; duckdb.connect('lab.duckdb').sql('from giao_dich limit 10').show()"`.

### Cách chấm

- `check.py` tính đáp án bằng **Python thuần** từ dữ liệu nguồn, không dùng SQL, rồi so từng dòng với kết quả query của bạn. Số thực được so với sai số 1e-4, thứ tự cột và dòng không quan trọng, nhưng **tên cột phải đúng** và **không được lọc bớt dòng**.
- Mỗi bài được chạy trên **2 bộ dữ liệu**: bộ lab (giống `lab.duckdb`) và một **bộ ẩn** sinh bằng seed khác, có cùng kiểu bẫy nhưng khác giá trị. Nếu bài chỉ đúng trên bộ lab, checker sẽ báo rằng query đang dựa vào đặc điểm riêng của dữ liệu.
- Khi FAIL, checker in một dòng sai làm ví dụ (`bạn=... đúng=...`). Hãy chạy query trên `lab.duckdb` và lọc đúng dòng đó để tìm lỗi.

### Đáp án

[dap-an/](dap-an/) có lời giải cho cả 27 bài, kèm comment giải thích, cùng 2 bài bonus (date spine cho B07, forward fill không dùng `IGNORE NULLS` cho B10). Tất cả đã được kiểm chứng:

```bash
python scripts/check.py --thu-muc dap-an     # 27 PASS
```

Làm xong bài rồi mới mở.

## Lộ trình gợi ý (khoảng 2 buổi)

1. Đọc [01](ly-thuyet/01-nen-tang.md), sau đó đọc [02](ly-thuyet/02-khung-cua-so-frame.md) §1–§3, rồi làm **A1–A4, A12**.
2. Đọc 02 §4–§6, làm **A5–A11**. Câu nào sai thì chạy lại trên `lab.duckdb` và đọc giải thích trong `dap-an/A-du-doan.txt`.
3. Làm B01–B05 (peer và LAST_VALUE), rồi B06–B11 (offset, UNBOUNDED FOLLOWING, khung rỗng).
4. Đọc [03](ly-thuyet/03-kiem-soat-va-phuong-ngu.md), làm B12–B15, rồi tự trả lời 6 câu phỏng vấn ở cuối file 03.
