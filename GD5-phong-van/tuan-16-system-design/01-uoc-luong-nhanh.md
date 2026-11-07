# 16.1 Ước lượng nhanh (back-of-the-envelope) cho bài toán dữ liệu

> Mục tiêu: đúng **bậc độ lớn** trong 3 phút và dùng con số để **ra quyết định** (full refresh hay incremental, cần partition không, chi phí có đáng lo không). Giá cả là tham khảo đầu 2026 theo bảng giá công khai. Luôn nói "cần kiểm tra bảng giá hiện hành / hợp đồng của công ty".

## Con số nên thuộc

| Đại lượng | Giá trị dùng để ước lượng |
|---|---|
| 1 ngày | 86.400 giây ≈ **10⁵ giây** |
| 1 năm | ≈ 3,15 × 10⁷ giây; 365 ngày; ~250 ngày làm việc |
| 1 triệu dòng / ngày | ≈ 12 dòng / giây trung bình (đỉnh ×5–10) |
| Kích thước 1 dòng giao dịch (10–20 cột) | 100–300 byte thô; **nén cột ~5–10×** → 20–50 byte trên warehouse |
| 1 tỷ dòng × 200 byte | 200 GB thô → **~20–40 GB** nén cột |
| Bảng snapshot dày đặc | số thực thể × số ngày. 2 triệu tài khoản × 365 = **730 triệu dòng / năm** |

## Warehouse: chi phí và tốc độ (tham khảo)

| | Snowflake | BigQuery (on-demand) |
|---|---|---|
| Đơn vị tính | **credit / giờ** theo cỡ warehouse: XS = 1, S = 2, M = 4, L = 8 (gấp đôi mỗi cỡ), tính theo giây, tối thiểu 60 giây mỗi lần bật | **TB dữ liệu quét**: ~6,25 USD / TiB (1 TiB đầu mỗi tháng miễn phí) |
| Giá 1 đơn vị | ~2–4 USD / credit tuỳ edition & vùng | |
| Lưu trữ | ~23–40 USD / TB / tháng | ~0,02 USD / GB / tháng (active, logical) |
| Đòn bẩy giảm chi phí | auto-suspend, cỡ nhỏ, clustering, chỉ build phần đổi | partition + cluster (giảm byte quét), `maximum_bytes_billed`, editions/slots khi tải đều |

Ví dụ nhanh:

- **Snowflake:** `dbt build` 300 model chạy 20 phút trên warehouse S mỗi ngày = 2 credit/h × 1/3 h ≈ 0,67 credit/ngày ≈ 20 credit/tháng ≈ **40–80 USD/tháng**. Chi phí lớn thường đến từ **dashboard truy vấn liên tục**, không phải dbt.
- **BigQuery:** model quét bảng 500 GB không partition, chạy 24 lần/ngày = 12 TB/ngày ≈ **75 USD/ngày ≈ 2.250 USD/tháng**. Partition theo ngày, mỗi lần chỉ quét 2 ngày (~3 GB) → vài USD/tháng. Đây là kiểu câu chuyện ước lượng làm người phỏng vấn gật đầu.

## Quy tắc ngón tay cái để ra quyết định

| Nếu... | Thì cân nhắc... |
|---|---|
| Bảng < ~50 triệu dòng, build < vài phút | `table` (full refresh), đơn giản, luôn đúng |
| Bảng hàng trăm triệu → tỷ dòng, tăng đều theo thời gian | `incremental` / `microbatch` + partition theo ngày + lookback cho dữ liệu trễ |
| Dữ liệu cũ bị sửa ngược thường xuyên (CDC có `u`/`d`) | merge theo khoá + lookback, hoặc dựng lại cửa sổ N ngày; full refresh định kỳ |
| Snapshot dày đặc quá lớn | chỉ giữ dày đặc 13 tháng gần nhất, cũ hơn lưu dạng "khoảng hiệu lực" (valid_from/valid_to) |
| Dashboard cần < 1 phút trễ | dữ liệu đó không đi qua dbt batch: streaming / materialized view / dynamic table (xem đề 10) |
| Tải truy vấn BI cao, lặp lại | aggregate table / semantic layer cache / pre-aggregation |

## Mẫu nói khi ước lượng (đề ngân hàng)

> "Giả định ngân hàng 3 triệu khách, 5 triệu tài khoản, 8 triệu giao dịch/ngày. Một năm ~3 tỷ giao dịch, khoảng 100–150 GB nén: lưu trữ không đáng lo. Snapshot số dư ngày 5 triệu tài khoản × 365 = 1,8 tỷ dòng/năm, cũng ổn nếu partition theo ngày. Chỗ đáng lo là **dựng lại** số dư: không thể full refresh lịch sử mỗi ngày. Em sẽ làm incremental theo `balance_date`, lookback 7 ngày cho ghi sổ lùi, và rebuild toàn bộ hằng tháng sau khoá sổ."

## Bài tập

Ước lượng (3 phút mỗi bài, nói thành tiếng):

1. Ví điện tử 20 triệu người dùng, mỗi người 3 giao dịch/ngày. Kích thước bảng giao dịch 3 năm? Có cần partition không?
2. Sàn TMĐT ghi 200 sự kiện click/phiên, 2 triệu phiên/ngày. BigQuery: một dashboard quét toàn bộ bảng sự kiện 90 ngày, 50 người xem mỗi giờ trong giờ làm việc. Tiền mỗi tháng? Sửa thế nào?
3. 400 model dbt, CI chạy mỗi PR toàn bộ project trên Snowflake M mất 25 phút, 30 PR/ngày. Chi phí CI/tháng? Slim CI giảm được bao nhiêu nếu mỗi PR chỉ đụng 5% model?

<details><summary>Gợi ý đáp số</summary>

1. 20M × 3 × 365 × 3 ≈ 66 tỷ dòng, ~2–3 TB nén. Bắt buộc partition theo ngày + cluster theo user/merchant.
2. 400M sự kiện/ngày × 90 ≈ 36 tỷ dòng, ~2 TB quét mỗi lần. 50 × 8 giờ × 22 ngày ≈ 8.800 lần → ~17.600 TB → ~110.000 USD/tháng. Sửa: bảng tổng hợp theo ngày (vài GB), partition, BI cache. Còn vài chục USD.
3. M = 4 credit/h × 25/60 h ≈ 1,7 credit/PR × 30 × 22 ≈ 1.100 credit ≈ 2.200–4.400 USD/tháng. Slim CI ~5% model → còn ~100–200 USD (cộng chi phí cố định khởi động).
</details>
