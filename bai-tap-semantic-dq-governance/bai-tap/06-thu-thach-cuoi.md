# 06 — Tổng hợp, thử thách mở, câu hỏi phỏng vấn

## Mốc hoàn thành lab

```bash
./scripts/replay.sh              # 26/26 PASS (O5 cần venv Airflow; không có thì SKIP)
```

Cả 4 phần phải xanh **cùng lúc**, trên cùng một project. Đó là điểm khó của nền tảng thật: governance (contract, version) không được làm hỏng semantic layer, test DQ không được chặn nhầm model mà dashboard cần.

## Thử thách mở (không chấm)

1. **Conversion metric thật.** Viết metric `type: conversion`: tỉ lệ phiên **đã đăng nhập** dẫn tới đơn trong vòng 1 ngày (`entity: customer`, `base_metric: sessions`, `conversion_metric: orders`). Đọc `--explain`: MetricFlow so `metric_time` ở grain nào? Với `window: 1 day` và grain ngày, "trong 1 ngày" thực chất là "cùng ngày" (đã đo trên lab). Ngày 03/12 (lỗi tracking) metric này ra sao? Đây là ví dụ một sự cố DQ làm sai một metric dù không bảng mart nào sai.
2. **Metric bị ảnh hưởng bởi sự cố nào?** Với mỗi sự cố Q2–Q6, liệt kê metric nào trong 15 metric bị sai và sai theo hướng nào. Ghi vào runbook, mục "Báo cho người dùng".
3. **Freshness của model.** dbt ≥ 1.10 cho khai báo `config: freshness: build_after:` trên model. Cấu hình này phục vụ state-aware orchestration của dbt platform (chỉ build lại model khi nguồn có dữ liệu mới). Đọc tài liệu và giải thích: trên dbt Core nó làm được gì, không làm được gì, và nó khác source freshness ở Q1 ra sao.
4. **Elementary report.** `pip install 'elementary-data'` (CLI nặng, nên dùng venv riêng) rồi `edr report`. Nếu CLI chưa hỗ trợ DuckDB, làm phần này trên `thelook`.
5. **CI cho semantic layer.** Thêm vào workflow CI của `thelook`: `dbt parse` → `mf validate-configs` → một `mf query` cho metric quan trọng nhất, so với giá trị kỳ vọng của một ngày đã khoá sổ.
6. **Unit test cho macro `mask_pii`.** Viết `unit_tests:` cho `dim_customers_v2` với 3 dòng input (email viết hoa, số điện thoại 11 số, tên một chữ) và output đã che.

## Câu hỏi phỏng vấn (Mid → Senior)

**Semantic layer**
1. "Doanh thu" của Finance và của Marketing lệch 3%. Bạn điều tra thế nào, và semantic layer giúp gì để chuyện này không lặp lại?
2. Khi nào **không** nên làm semantic layer?
3. Thiết kế metric `active_customers_30d` cho dashboard ngày, tuần, tháng. Gom lên tháng thì lấy giá trị nào?

**Data quality**
4. Bạn có 400 model, mỗi sáng 30 cảnh báo, không ai đọc. Bạn làm gì trong 2 tuần đầu?
5. Phân biệt SLA, SLO, SLI bằng một ví dụ của Mây Shop.
6. Khi nào test nên `error` (chặn), khi nào `warn`? Có ngoại lệ nào cho source không?
7. Một connector nạp thiếu 70% dữ liệu nhưng mọi test luật đều xanh. Làm sao phát hiện?

**Governance**
8. Đội khác cần một cột trong model `private` của bạn. Quy trình nên thế nào?
9. Model contract khác data contract với đội nguồn ở điểm nào? Ai ký, ai chịu trách nhiệm khi vi phạm?
10. Che PII ở dbt, ở warehouse, hay ở BI? Ưu, nhược từng chỗ.

**Orchestration**
11. Airflow hay Dagster cho một công ty mới có 1 dbt project và 5 nguồn dữ liệu? Cho một ngân hàng có 300 DAG?
12. Pipeline chạy 06:30 nhưng connector có hôm 07:15 mới xong. Thiết kế lại lịch chạy.

## Nối sang GĐ4

- Groups + access + contract + versions ở đây là nền của **dbt Mesh** (tuần 12): mỗi group sẽ thành một project, model public thành giao diện giữa các project.
- Semantic layer + saved query là đầu vào của **AI context layer** (tuần 14): trợ lý AI hỏi metric qua MCP thay vì tự viết SQL.
