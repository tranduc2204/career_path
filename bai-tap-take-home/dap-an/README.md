# Ngân hàng số Sen — lời giải take-home (bản mẫu)

## Cách chạy
`dbt deps && dbt build` → 4 bảng trong schema `analytics`. Test `assert_gl_reconciles` cảnh báo 1 dòng lệch (xem dưới).

## Mô hình
staging (làm sạch, loại sự kiện CDC phát lại) → intermediate (`int_transactions__current`: trạng thái hiện tại theo lsn lớn nhất; `int_fx_daily`: tỷ giá forward-fill) → marts (4 bảng theo đề).

## Giả định
- Ngày nghiệp vụ là `value_date` (giờ VN). `booking_ts`/`commit_ts` là UTC và có ghi sổ lùi ngày → không dùng để xác định ngày.
- Giao dịch REVERSED coi như không xảy ra; sự kiện `d` là xoá hẳn.
- Ngày không có tỷ giá (cuối tuần, 01/01) dùng tỷ giá niêm yết gần nhất trước đó.
- Lãi và lương (channel SYSTEM) không tính là "khách hoạt động".

## Quyết định
- Materialize `table` toàn bộ: dữ liệu nhỏ, ghi sổ lùi ngày làm thay đổi số dư quá khứ → dựng lại toàn bộ là đúng và đơn giản nhất. Ở production: incremental theo `value_date` với lookback ≥ 3 ngày, hoặc microbatch, và full refresh định kỳ.
- Số dư dày đặc (mọi ngày) để AVG và đối soát không phụ thuộc ngày có giao dịch.
- Đối soát với GL là test `warn`: lệch là thông tin cho Finance, không chặn pipeline.

## Phát hiện
- 15/01/2027, SAVING VND: số dư tính từ giao dịch thấp hơn sổ cái 2.000.000đ, mọi ngày khác khớp → nghi GL hạch toán nhầm ngày đó. Cần xác nhận với Kế toán.

## Việc tiếp theo
- Incremental/microbatch + full refresh hằng tuần; snapshot `core.accounts` (hiện là trạng thái hiện tại, mất lịch sử đổi sản phẩm).
- Contract cho 4 mart, freshness cho source CDC, unit test cho logic chọn lsn lớn nhất.
- Che PII (`full_name`) ở môi trường dev.
