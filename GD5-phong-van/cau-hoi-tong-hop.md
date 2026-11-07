# Câu hỏi phỏng vấn tổng hợp (GĐ1 → GĐ5)

> Một chỗ để ôn trước mỗi buổi phỏng vấn. Mỗi tuần 18–20, thêm câu hỏi **thật** bạn gặp vào phần cuối (từ [nhật ký](tuan-18-20-phong-van/07-nhat-ky-va-hoc-bu.md)).

## Bộ câu hỏi theo giai đoạn

| Giai đoạn | File | Chủ đề |
|---|---|---|
| GĐ1 | [GD1-ly-thuyet](../GD1-ly-thuyet/README.md) (câu hỏi tự kiểm tra cuối mỗi file) | dbt cơ bản, incremental, snapshot, Jinja, CI |
| GĐ2 | [GD2-ly-thuyet/cau-hoi-on-tap.md](../GD2-ly-thuyet/cau-hoi-on-tap.md) | Kimball, Data Vault, BigQuery, performance |
| GĐ3 | [GD3-ly-thuyet/cau-hoi-on-tap.md](../GD3-ly-thuyet/cau-hoi-on-tap.md) | Semantic layer, DQ, governance, orchestration |
| GĐ3 | [Đề thi thử dbt 65 câu](../GD3-ly-thuyet/tuan-11/03-de-thi-thu.md) | dbt chi tiết |
| GĐ5 | [16.11 ngân hàng đề system design](tuan-16-system-design/11-ngan-hang-de-luyen-them.md) | System design |
| GĐ5 | [Flashcard 60 câu](tuan-17-tet/on-nhe-va-flashcard.md) | Ôn nhanh |
| GĐ5 | [Câu hỏi hành vi](tuan-18-20-phong-van/03-behavioral-star.md) | STAR |

## 30 câu hay gặp nhất ở vòng AE Mid (ôn trước mọi buổi)

**dbt & SQL**
1. Incremental hoạt động thế nào, bẫy gì? (dữ liệu trễ, `on_schema_change`, `unique_key`)
2. Snapshot timestamp vs check? Hard delete?
3. Slim CI: lệnh, `--defer`, `--state`.
4. Contract, versions, access: dùng khi nào?
5. Test generic / singular / unit khác nhau ra sao? Severity?
6. Macro/Jinja bạn từng viết? `adapter.dispatch`?
7. Window function: top N mỗi nhóm, luỹ kế, gaps & islands.
8. Dedupe bản ghi mới nhất; xử lý NULL trong join và so sánh.

**Mô hình**
9. 4 bước Kimball, grain là gì, ví dụ grain của bạn.
10. SCD2 dựng thế nào, join fact với SCD2 ra sao?
11. Semi-additive, periodic vs accumulating snapshot.
12. Data Vault vs Kimball, khi nào chọn cái nào.
13. Fan-out là gì, phát hiện và tránh thế nào?
14. Late-arriving fact / dimension.

**Nền tảng**
15. Thiết kế 3 môi trường + CI/CD.
16. DQ framework của bạn: test ở đâu, severity, freshness, anomaly.
17. Semantic layer: vì sao cần, ratio vs average.
18. Orchestration: Airflow vs Dagster, một task hay mỗi model một task.
19. Tối ưu chi phí / hiệu năng warehouse: bạn đo gì, đòn bẩy nào.
20. PII và phân quyền.

**System design** (tuần 16)
21. Tầng transformation cho ngân hàng.
22. DQ framework cho 500 model.
23. CI/CD nhiều môi trường.
24. Chuyển stored procedure sang dbt.
25. Dashboard gần real-time.

**Senior**
26. Mono-repo hay multi-repo, khi nào dbt Mesh?
27. Metric tập trung hay theo domain?
28. Context engineering cho AI hỏi số liệu.
29. Khi nào **không** dùng dbt / không làm semantic layer?
30. Kể một quyết định kiến trúc sai và cách sửa.

## Câu hỏi thật đã gặp (tự thêm)

| Ngày | Công ty | Câu hỏi | Ghi chú |
|---|---|---|---|
| | | | |
