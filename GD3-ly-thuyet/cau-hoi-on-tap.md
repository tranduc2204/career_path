# GĐ3 — Câu hỏi ôn tập và phỏng vấn (Mid → Senior)

> Cách dùng: buổi tối, chọn 5 câu, **nói thành tiếng** trong 2 phút/câu, ghi âm, nghe lại. Câu có ⭐ là câu hay gặp ở vòng phỏng vấn Mid; ⭐⭐ là câu kiểu Senior (cần nêu đánh đổi và kinh nghiệm).
> Khung trả lời gợi ý: **Bối cảnh → Lựa chọn → Đánh đổi → Ví dụ của bạn (lab / adventure_works / thelook) → Bài học**.

## Semantic layer

1. ⭐ Semantic layer là gì? Vì sao công ty đã có mart sạch vẫn cần nó?
2. ⭐ Ratio metric khác `average` thế nào? Lấy AOV làm ví dụ, giải thích vì sao trung bình của AOV ngày là sai.
3. ⭐ Entity primary và foreign khác nhau ra sao, và vì sao MetricFlow từ chối một số join?
4. Cumulative metric `period_agg` dùng để làm gì? Cho ví dụ chọn `first`, `last`, `average`.
5. Ngày không có hoàn tiền làm `net_revenue` ra NULL. Giải thích và nêu 2 cách sửa.
6. ⭐⭐ Finance và Marketing cãi nhau về "doanh thu". Bạn xử lý cả kỹ thuật lẫn con người thế nào?
7. ⭐⭐ MetricFlow, Cube, LookML: chọn cái nào cho (a) startup dùng dbt Core + Metabase, (b) công ty SaaS cần dashboard nhúng cho khách, (c) tập đoàn đã dùng Looker 5 năm?
8. ⭐⭐ Trợ lý AI trả lời câu hỏi về số liệu. Vì sao nên cho nó hỏi qua semantic layer thay vì tự viết SQL?
9. Bạn kiểm thử một metric thế nào trước khi merge?

## Data quality

10. ⭐ Kể các chiều chất lượng dữ liệu, mỗi chiều một test điển hình.
11. ⭐ Khi nào test nên `error`, khi nào `warn`? Test trên source thì có gì đặc biệt?
12. ⭐ SLA, SLO, SLI khác nhau thế nào? Viết SLA cho một dashboard bạn từng làm.
13. Bảng sản phẩm gần như không đổi, freshness theo `_loaded_at` báo đỏ mỗi ngày. Bạn làm gì?
14. ⭐ Anomaly detection hoạt động thế nào? Khi nào nó báo nhầm?
15. Cột được phép NULL 40%, hôm nay 90%. Test nào bắt được? Vì sao không dùng `not_null`?
16. ⭐⭐ Có 400 model, mỗi sáng 30 cảnh báo, không ai đọc. Kế hoạch 2 tuần của bạn?
17. ⭐ Model contract khác data contract thế nào? Bạn đề xuất data contract với đội nguồn ra sao?
18. ⭐⭐ Kể một sự cố dữ liệu bạn từng xử lý (BRAVO / Estuary / lab) theo khung: phát hiện → khoanh vùng → khắc phục → phòng ngừa. Đo TTD, TTR.
19. Connector nạp thiếu 70% nhưng mọi test luật đều xanh. Làm sao phát hiện?
20. Vì sao "thà số hôm qua còn hơn số sai" đôi khi lại sai?

## Governance

21. ⭐ `private`, `protected`, `public` khác nhau thế nào? Staging nên để mức nào?
22. ⭐ Khi nào cần model version mới? Kể 3 thay đổi phá vỡ.
23. Contract trên Snowflake có chặn trùng khoá chính không? Vậy bạn làm gì?
24. ⭐ Che PII ở dbt, ở warehouse, hay ở BI? Ưu nhược từng tầng.
25. ⭐⭐ Thiết kế governance cho công ty 5 đội dữ liệu chung một dbt project. Khi nào tách thành Mesh?
26. Exposure dùng để làm gì ngoài việc vẽ lineage?
27. OpenMetadata lấy thông tin gì từ dbt và cần artifact nào?

## Orchestration

28. ⭐ Task-centric và asset-centric khác nhau thế nào? Ví dụ câu hỏi vận hành mà asset-centric trả lời dễ hơn.
29. ⭐ Chạy dbt trong Airflow: một task `dbt build` hay mỗi model một task? Đánh đổi?
30. Cosmos `LoadMode.DBT_MANIFEST` giải quyết vấn đề gì?
31. ⭐ Retry ở orchestrator và `dbt retry` khác nhau ra sao? Khi nào **không** nên retry?
32. ⭐⭐ Airflow hay Dagster cho (a) startup mới có 1 dbt project, (b) ngân hàng có 300 DAG Airflow 2? Lập luận như một ADR.
33. Backfill 7 ngày cho một incremental model: bạn làm thế nào trong Airflow, Dagster, và với microbatch của dbt?
34. Pipeline lịch 06:30 nhưng connector có hôm 07:15 mới xong. Thiết kế lại.

## dbt (ôn thi chứng chỉ)

35. ⭐ `is_incremental()` đúng khi nào? `on_schema_change` mặc định là gì và hậu quả?
36. ⭐ Microbatch khác incremental truyền thống ở điểm nào? `lookback` để làm gì?
37. ⭐ Slim CI: viết lệnh và giải thích `--defer`, `--state`, `state:modified+`.
38. `dbt retry` và `dbt clone` dùng khi nào?
39. Unit test khác data test thế nào? Viết một unit test cho logic `is_cancelled`.
40. ⭐ Đọc lỗi: compilation error vs database error. Xem SQL thật ở đâu?

## Pipeline Python

41. ⭐ Bạn test một pipeline incremental thế nào? Kể 5 hành vi phải test.
42. Mock thư viện HTTP hay dựng server giả? Mỗi cách bắt được loại lỗi nào?
43. Mutation testing đo cái gì mà coverage không đo?

## Câu tổng hợp (Senior)

44. ⭐⭐ Vẽ kiến trúc nền tảng dữ liệu của Mây Shop sau GĐ3: nguồn → ingest → dbt (staging/marts, groups) → semantic layer → BI/AI, kèm DQ, governance, orchestration. Chỉ ra 3 điểm yếu nhất và kế hoạch 3 tháng.
45. ⭐⭐ Bạn vào một công ty có dbt project 600 model, không test, không owner, chạy cron. Liệt kê 10 việc theo thứ tự ưu tiên trong 90 ngày đầu.
