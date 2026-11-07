# 11.1 dbt Analytics Engineering Certification: thể thức và kế hoạch tuần thi

> Thông tin tra ngày 07/11/2026. **Kiểm tra lại trên trang chính thức** (getdbt.com → Certifications: *exam guide* và *study guide*) trước khi đăng ký: dbt Labs cập nhật đề theo phiên bản dbt.

## Thể thức

| | |
|---|---|
| Phiên bản dbt của đề | **1.11** (trang chính thức ghi "dbt 1.11"; theo các nguồn ôn thi, đề được làm mới tháng 4/2026) |
| Số câu / thời gian | **65 câu / 120 phút** (có thêm một số câu thử nghiệm không tính điểm, không phân biệt được) |
| Điểm đạt | **65%** (theo study guide; các nguồn bên thứ ba ghi giống) |
| Hình thức | Online, có giám thị trực tiếp qua webcam; tiếng Anh (có thêm tiếng Nhật) |
| Lệ phí | **200 USD**, thi lại phải trả lại |
| Hiệu lực | 2 năm |
| Dạng câu | Chọn 1, chọn nhiều (đề ghi số đáp án đúng), điền từ, ghép cặp, "hotspot" (chọn vị trí trong code/DAG), DOMC (từng phương án hiện riêng, trả lời đúng/sai) |
| Khuyến nghị | SQL vững + ≥ 6 tháng dùng dbt |

## Các mảng kiến thức

Theo study guide (bản 1.11) và tổng hợp của người đã thi. Trọng số chính xác xem study guide:

| # | Mảng | Nội dung chính | Bạn đã học ở |
|---|---|---|---|
| 1 | Developing & optimizing models | materialization (gồm **microbatch**), ref/source, Jinja/macro, Python model, snapshot YAML, seeds, grants, `dbt_project.yml`, `persist_docs`, doc block, `--empty`, `--sample` | GĐ1 tuần 1–2 |
| 2 | Model governance | contracts, constraints, versions, `deprecation_date` | GĐ3 tuần 10 |
| 3 | Debugging modeling errors | lỗi compile / database / runtime, đọc `target/compiled`, YAML/Jinja error, behavior flags | GĐ1 |
| 4 | Troubleshooting pipelines | lỗi trong DAG, `dbt retry`, **`dbt clone`**, tích hợp công cụ | GĐ1 tuần 3, GĐ3 |
| 5 | Tests | generic/singular/custom generic, **unit tests**, severity, `store_failures` | GĐ1 tuần 2, GĐ3 tuần 9 |
| 6 | External dependencies | exposures, source freshness, packages | GĐ1, GĐ3 |
| 7 | dbt state | `manifest.json`, `state:modified`, `--defer`, `--state`, `result:`, Slim CI | GĐ1 tuần 3, GĐ2 tuần 5 |

Theo các nguồn ôn thi, bản 2026 **giảm** trọng tâm `access`/`groups` và docs, **thêm** microbatch, `--empty`/`--sample`, behavior flags, constraints, `dbt clone`. Theo outline hiện tại, semantic layer **không** nằm trong đề này.

## Kế hoạch tuần 11 (24–30/12)

| Ngày | Sáng | Chiều | Tối |
|---|---|---|---|
| T5 24/12 | [11.2](02-on-thi-theo-chu-de.md) mảng 1, 3 | Lab GĐ1: làm lại 5 bài khó nhất, có đọc `target/compiled` | Thẻ ghi nhớ: materialization, config |
| T6 25/12 | 11.2 mảng 5, 6, 7 | Viết 3 unit test + 1 microbatch model trên `adventure_works` | `dbt clone`, `dbt retry` thử trên máy |
| T7 26/12 | 11.2 mảng 2, 4 | **Đề thi thử** [11.3](03-de-thi-thu.md) 65 câu / 120 phút, bấm giờ | Chấm bằng [11.4](04-dap-an-de-thi-thu.md), ghi câu sai |
| CN 27/12 | Ôn câu sai theo mảng | (nghỉ) | |
| T2 28/12 | Đọc lại docs các mảng < 70% | [11.5](05-pytest-cho-pipeline-dlt.md) + lab dlt P1–P4 | |
| T3 29/12 | Làm lại đề thi thử, chỉ câu sai + câu đoán | Lab dlt P5–P8 → 8/8 | Kiểm tra máy, webcam, phòng thi |
| T4 30/12 | **Thi** (buổi sáng, đầu óc tỉnh táo) | Áp dụng pytest sang pipeline thật | Cập nhật CV / LinkedIn |

## Mẹo làm bài

- Câu hỏi thường cho **một đoạn YAML / SQL / lệnh** rồi hỏi kết quả. Luyện **đọc** code nhanh hơn viết.
- Để ý chữ nhỏ: *"the first time"* vs *"subsequent runs"* (incremental), *"in production"* vs *"in CI"* (`--defer`), số đáp án đúng ở câu chọn nhiều.
- Không có điểm âm: **không bỏ trống** câu nào.
- Đánh dấu câu lâu, làm hết lượt đầu trong ~80 phút, quay lại sau.
- Thuộc **giá trị mặc định**: materialization (`view`), `on_schema_change` (`ignore`), severity (`error`), `lookback` của microbatch (`1`)... (bảng ở 11.2).

## Tài liệu

- dbt Labs: *dbt Analytics Engineering Certification Exam* (trang đăng ký), *Exam guide*, *Study guide* (danh sách docs cần đọc theo từng mảng)
- dbt Learn: *dbt Fundamentals*, *Advanced Materializations*, *Jinja, Macros & Packages*, *Advanced Testing*, *Analyses & Seeds*, *Refactoring SQL for Modularity*
