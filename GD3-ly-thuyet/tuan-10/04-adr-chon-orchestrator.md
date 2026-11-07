# 10.4 ADR: chọn orchestrator

> Ôn lại cấu trúc ADR ở [GD2 6.6](../../GD2-ly-thuyet/tuan-6/06-adr-data-vault-vs-kimball.md). Bài này áp dụng cho một quyết định **hạ tầng**.

## Các tiêu chí thường bị bỏ sót

Người mới so tính năng. Người có kinh nghiệm so **chi phí vận hành** và **con người**:

| Nhóm | Tiêu chí | Câu hỏi |
|---|---|---|
| Phù hợp với dbt | Mô hình asset, lineage, test thành check | Người vận hành có thấy được "bảng nào hỏng" ngay không? |
| Hiệu năng | Thời gian chạy cả pipeline, thời gian parse DAG | Đo trên project thật (lab: Cosmos per-model ~4,5 phút, Dagster chọn tập asset ≈ thời gian `dbt build`) |
| Vận hành | Ai cài, nâng cấp, giám sát scheduler + DB metadata? Có bản managed không? | Astronomer / Composer / MWAA, Dagster+ |
| Hệ sinh thái | Đã có bao nhiêu DAG / job khác? Tích hợp ingest, reverse ETL, ML? | Ngân hàng 300 DAG Airflow ≠ startup 0 DAG |
| Con người | Đội đã biết công cụ nào? Tuyển dễ không? | Airflow phổ biến hơn trên thị trường tuyển dụng |
| Lên lịch theo dữ liệu | Sensor, Assets (Airflow 3), declarative automation (Dagster) | Có SLA theo nguồn không? |
| Bảo mật | Secrets, RBAC, audit | Ngân hàng: yêu cầu kiểm toán |
| Chi phí | Hạ tầng + bản quyền + công vận hành | Tính theo năm |

## Mẫu ADR

```markdown
# ADR 0003: Orchestrator cho nền tảng dữ liệu Mây Shop

- Trạng thái: Đề xuất | Đã chấp nhận | Thay thế bởi ADR-xxxx
- Ngày: 2026-12-23
- Người quyết định: ...  · Người được hỏi ý kiến: ...

## Bối cảnh
1 dbt project (~16 model, sẽ tách Mesh 3 project ở Q1/2027), 5 connector, 3 đội, SLA 07:00.
Hiện chạy bằng cron + shell script (`run_day.sh`). Sự cố tháng 12: connector mkt chết 3 ngày,
pipeline vẫn build như thường, không ai biết cho tới khi Marketing hỏi.

## Các lựa chọn
1. Giữ cron + `dbt build` + cảnh báo tự viết
2. Airflow 3 + Cosmos (managed: Astronomer / Composer)
3. Dagster (OSS tự host / Dagster+)

## Số đo (thí nghiệm trên lab, ngày ...)
| | Cron | Airflow + Cosmos | Dagster |
|---|---|---|---|
| Thời gian chạy hết pipeline | 15 s | 4 ph 30 s (34 task) | ... |
| Dòng code cấu hình | 30 | ~45 | ~60 |
| Chạy lại 1 model + downstream | sửa lệnh tay | "Clear" task + downstream | chọn asset → materialize |
| Lịch theo dữ liệu | không | Assets | AutomationCondition |
| ...

## Quyết định
Chọn ... vì (3 lý do chính, gắn với bối cảnh và số đo).

## Hệ quả
- Tích cực: ...
- Tiêu cực / rủi ro: ... (vd: thêm 1 dịch vụ phải vận hành; đội phải học ...)
- Việc cần làm: ...

## Khi nào xem lại
Khi > N model, khi có đội ML cần orchestration riêng, khi chi phí managed > X.
```

## Gợi ý kết luận (để bạn phản biện, không phải đáp án)

- **Startup, dbt-first, chưa có orchestrator:** Dagster thường thắng nhờ asset model, dbt tích hợp sâu, chạy một phần đồ thị nhanh.
- **Doanh nghiệp đã có Airflow (ngân hàng, viễn thông):** Airflow + Cosmos, vì chi phí chuyển đổi và đào tạo lớn hơn lợi ích. Dùng Assets của Airflow 3 cho lịch theo dữ liệu.
- **Chỉ có dbt, 1 lần/ngày, đội nhỏ:** dbt platform job scheduler, hoặc GitHub Actions theo lịch, có khi là đủ. Đừng thêm hạ tầng chưa cần.

## Câu hỏi tự kiểm tra

1. Một ADR tốt phải có phần nào để 1 năm sau người khác hiểu **vì sao** đội đã chọn như vậy?
2. Bạn phỏng vấn ở một ngân hàng dùng Airflow 2.x. Họ hỏi "có nên chuyển sang Dagster không?". Trả lời trong 2 phút.
