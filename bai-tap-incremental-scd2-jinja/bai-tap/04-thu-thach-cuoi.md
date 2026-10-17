# 04 — Thử thách cuối

## 1. Chạy trọn bộ

```bash
./scripts/replay.sh
dbt run -s fct_events_microbatch --event-time-start 2025-12-29 --event-time-end 2026-01-07
python scripts/check.py
```

Mục tiêu: **26/26 PASS**. Chạy thêm `dbt run-operation audit_incremental_models` (J8) — không có lỗi.

## 2. Viết lại bằng lời (quan trọng nhất)

Tạo `lab/NOTES.md`, trả lời ngắn gọn — đây là thứ bạn sẽ nói trong phỏng vấn:

1. Bảng "model – chiến lược – `unique_key` – watermark – lý do chọn" cho mọi model incremental.
2. 3 lỗi bạn đã gặp trong lab, mỗi lỗi: triệu chứng → nguyên nhân → cách sửa → cách phát hiện sớm trong production.
3. So sánh 3 cách dựng SCD2 (snapshot / incremental tự viết / CDC log): chi phí, độ chính xác thời gian, khả năng dựng lại, khi nào dùng.

## 3. Thử thách mở (không có trong check.py)

| # | Cấp | Thử thách |
|---|---|---|
| C1 | ⭐⭐⭐⭐ | Đổi `fct_orders_pit` sang incremental. Mỗi lần chạy xử lý đơn mới **và** các đơn đang `customer_sk = '-1'` để gán lại khi khách đến sau. Kiểm chứng bằng S6 qua replay. |
| C2 | ⭐⭐⭐ | `analyses/revenue_by_city_at_order_vs_current.sql`: doanh thu theo thành phố lúc đặt đơn so với thành phố hiện tại. Giải thích chênh lệch. |
| C3 | ⭐⭐⭐ | Thêm `incremental_predicates` cho `fct_orders` để merge chỉ quét đơn trong 3 ngày gần nhất. Replay → đơn đến muộn ngày 2 (order_date 12-28) có bị ảnh hưởng không? Viết lại kết luận về đánh đổi. |
| C4 | ⭐⭐⭐ | Dùng `dbt_valid_to_current` trong `snap_customers` để dòng hiện hành có `dbt_valid_to = '9999-12-31'` thay vì null. Sửa `dim_customers` và test cho phù hợp. |
| C5 | ⭐⭐⭐⭐ | `dim_products` SCD2 từ `snap_products` + `fct_order_items_pit` lấy giá niêm yết tại thời điểm đặt đơn. Bạn sẽ đụng phải vấn đề `dbt_valid_from` của strategy check (S2). Đề xuất cách giải quyết. |
| C6 | ⭐⭐⭐⭐ | Viết macro `generate_scd2_tests(model_name, key)` in ra (`print`) khối YAML test chuẩn cho một dim SCD2, chạy bằng `run-operation` — giống codegen. |
| C7 | ⭐⭐ | Chọn 3 kỹ thuật trong lab, áp dụng vào `adventure_works` (vd: `fct_sales` merge theo `_loaded_at`, snapshot `Production.Product` dạng check, `dim_customers` SCD2). |

## 4. Câu hỏi phỏng vấn tự luyện

Trả lời miệng, mỗi câu ≤ 2 phút, có ví dụ từ lab:

1. Bạn chọn watermark cho incremental thế nào? Kể một lần chọn sai.
2. `merge` và `delete+insert` khác nhau ra sao? Khi nào chọn cái nào?
3. Làm sao chứng minh model incremental của bạn cho cùng kết quả với full refresh?
4. Dữ liệu đến muộn 10 ngày, lookback chỉ 3 ngày. Bạn xử lý thế nào?
5. Nguồn thêm cột mới lúc 2h sáng. Pipeline của bạn phản ứng ra sao? Bạn muốn nó phản ứng ra sao?
6. Snapshot `timestamp` và `check` khác nhau thế nào? Kể trường hợp `timestamp` bỏ sót thay đổi.
7. Bảng nguồn không có `updated_at`. Bạn dựng SCD2 thế nào? `valid_from` có chính xác không?
8. Fact đến trước dimension: bạn làm gì để không mất dòng, và để sửa lại khi dimension đến?
9. Snapshot lỡ không chạy 3 ngày. Mất gì? Lấy lại được không?
10. Có CDC log thì còn cần snapshot không?
