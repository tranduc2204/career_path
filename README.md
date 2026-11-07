# target_ae — Tự học Analytics Engineer: Junior → Mid (15/10/2026 → 28/02/2027)

Repo này chứa toàn bộ tài liệu tự học và bài thực hành cho lộ trình **Analytics Engineer** trong 20 tuần: lý thuyết viết bằng tiếng Việt, lab dbt chạy được ngay trên máy (có script tự chấm), và bộ hướng dẫn kèm file mẫu cho các bài phải chạy trên cloud.

Kế hoạch đầy đủ, gồm skill gap, lịch học trong ngày và đầu ra từng tuần: **[ROADMAP-AE-2027.md](ROADMAP-AE-2027.md)**.

## Tiến độ

| Giai đoạn | Thời gian | Nội dung | Tài liệu |
|---|---|---|---|
| **GĐ1** — Junior | 15/10 → 4/11 | Phân tầng dbt, packages, Jinja/macro, incremental, snapshot/SCD2, custom test, sqlfluff, slim CI, contracts, freshness | ✅ [Lý thuyết](GD1-ly-thuyet/README.md) · [Lab](bai-tap-incremental-scd2-jinja/README.md) |
| **GĐ2** — Modeling & Warehouse mức Mid | 5/11 → 2/12 | Kimball chuyên sâu, BigQuery với 3 môi trường + CD, Data Vault 2.0, performance playbook | ✅ [Lý thuyết](GD2-ly-thuyet/README.md) · [Lab](bai-tap-kimball-data-vault/README.md) · [BigQuery](bai-tap-bigquery-thelook/README.md) · [Performance](bai-tap-performance/README.md) |
| **GĐ3** — Platform mức Mid | 3/12 → 30/12 | Semantic layer (MetricFlow, Cube), DQ framework (Elementary, SLA, contracts), governance, orchestration (Dagster, Airflow + Cosmos), chứng chỉ dbt, pytest cho dlt | ✅ [Lý thuyết](GD3-ly-thuyet/README.md) · [Lab](bai-tap-semantic-dq-governance/README.md) · [dlt + pytest](bai-tap-dlt-pytest/README.md) · [Đề thi thử](GD3-ly-thuyet/tuan-11/03-de-thi-thu.md) |
| **GĐ4** — Capstone hướng Senior | 31/12 → 27/1 | dbt Mesh, tự viết dbt package, AI context layer, architecture blueprint | ⏳ |
| **GĐ5** — Phỏng vấn | 28/1 → 28/2 | System design (8 đề giải mẫu + 14 đề luyện, rubric, drill), take-home ngân hàng tự chấm, CV/STAR/live SQL/offer | ✅ [Tài liệu](GD5-phong-van/README.md) · [System design](GD5-phong-van/tuan-16-system-design/00-khung-tra-loi.md) · [Take-home](bai-tap-take-home/README.md) |

## Cấu trúc repo

```
target_ae/
├── ROADMAP-AE-2027.md              ← lộ trình 20 tuần
│
├── GD1-ly-thuyet/                  ← lý thuyết GĐ1 (tuần 1–3) + câu hỏi ôn tập
├── bai-tap-incremental-scd2-jinja/ ← lab GĐ1: dbt + DuckDB, 38 bài tự chấm, 12 "ngày" giả lập
│
├── GD2-ly-thuyet/                  ← lý thuyết GĐ2 (tuần 4–7) + câu hỏi ôn tập
├── bai-tap-kimball-data-vault/     ← lab GĐ2: dbt + DuckDB + automate_dv, 21 bài tự chấm, 7 "ngày"
├── bai-tap-bigquery-thelook/       ← hướng dẫn 6 bước + file mẫu cho project 2 trên BigQuery
├── bai-tap-performance/            ← thí nghiệm Snowflake (TPC-H) & BigQuery (thelook) + mẫu playbook
│
├── GD3-ly-thuyet/                  ← lý thuyết GĐ3 (tuần 8–11) + câu hỏi ôn tập + đề thi thử chứng chỉ dbt
├── bai-tap-semantic-dq-governance/ ← lab GĐ3: MetricFlow + Elementary + governance + Dagster/Airflow, 26 bài tự chấm, 8 "ngày" 6 sự cố, kit Cube
├── bai-tap-dlt-pytest/             ← viết pytest cho pipeline dlt, chấm bằng mutation testing (8 mutant)
│
├── GD5-phong-van/                  ← GĐ5: system design (khung, ước lượng, mẫu, 8 đề giải mẫu, 14 đề luyện, phiếu chấm, drill.py), Tết, ứng tuyển
└── bai-tap-take-home/              ← take-home mẫu "Ngân hàng số Sen": CDC → số dư ngày → đối soát sổ cái, tự chấm + rubric
```

Mỗi folder có README riêng, gồm mục lục, lịch theo ngày và checklist mốc.

## Phần thực hành

| Bài | Chạy ở đâu | Có gì |
|---|---|---|
| [Lab incremental / SCD2 / Jinja](bai-tap-incremental-scd2-jinja/README.md) | Máy cá nhân (DuckDB) | Tự dựng từ staging lên mart. Ngày 0–5 luyện Jinja, incremental và snapshot; ngày 6–11 xử lý 6 sự cố production (dữ liệu trùng, đổi tên cột, nguồn sửa ngầm số liệu cũ, soft delete...) |
| [Lab Kimball + Data Vault](bai-tap-kimball-data-vault/README.md) | Máy cá nhân (DuckDB) | "Mây Shop" với 5 hệ thống nguồn. Dựng star schema kiểu Kimball (bridge, factless, accumulating/periodic snapshot, dữ liệu đến muộn), rồi dựng lại bằng Data Vault 2.0 và phải ra đúng kết quả cũ |
| [Project BigQuery thelook](bai-tap-bigquery-thelook/README.md) | BigQuery + GitHub | 3 môi trường dev/ci/prod, CI theo PR, CD khi merge, tự xoá dataset của PR, xác thực bằng Workload Identity Federation |
| [Performance playbook](bai-tap-performance/README.md) | Snowflake + BigQuery | Pruning, clustering, chọn cỡ warehouse, partition, đo chi phí qua `INFORMATION_SCHEMA.JOBS` |
| [Lab semantic + DQ + governance](bai-tap-semantic-dq-governance/README.md) | Máy cá nhân (DuckDB; Docker cho Cube) | "Mây Shop" quý IV, 60 ngày lịch sử. 15 metric MetricFlow chấm bằng `mf query` thật; 8 ngày có 6 sự cố production (connector chết, thiếu dữ liệu, NULL tăng vọt, đổi schema, giá sai đơn vị) mà bộ test phải bắt đúng ngày và không báo động giả; groups/access/contracts/versions/PII; Dagster và Airflow 3 + Cosmos |
| [dlt + pytest](bai-tap-dlt-pytest/README.md) | Máy cá nhân | API giả lập (phân trang, cursor, 429), pipeline dlt → DuckDB, test của bạn phải giết 8 mutant |
| [Take-home Sen Bank](bai-tap-take-home/README.md) | Máy cá nhân (DuckDB) | Đề viết như email tuyển dụng, 6 giờ: nhật ký CDC (r/c/u/d, phát lại), tỷ giá thiếu ngày, ghi sổ lùi, 1 lỗi sổ cái. 4 bảng chấm từng dòng + rubric chủ quan + câu hỏi vòng đọc lại bài |

Ba lab DuckDB có chung cách vận hành: `simulate.py` cho thời gian trôi qua từng ngày, `check.py` tính đáp án chuẩn từ dữ liệu nguồn rồi chấm model của bạn, `replay.sh N` chạy lại từ ngày 0 tới ngày N để biết model có còn đúng khi dữ liệu thay đổi hay không. Folder `dap-an/` trong mỗi lab đã được kiểm chứng PASS toàn bộ, nên làm xong bài rồi mới mở.

## Bắt đầu nhanh

Cần [uv](https://docs.astral.sh/uv/). uv tự cài đúng bản Python theo `.python-version` của từng lab (3.13).

```bash
cd bai-tap-incremental-scd2-jinja      # hoặc bai-tap-kimball-data-vault / bai-tap-semantic-dq-governance
uv sync && source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.

dbt deps
python scripts/simulate.py reset       # tạo lab.duckdb, nạp dữ liệu ngày 0
python scripts/check.py                # lúc này mọi bài đều SKIP
```

Sau đó mở file `bai-tap/00-setup.md` của lab.

## Cách học mỗi ngày

| Giờ | Việc |
|---|---|
| 07:30–11:30 | Đọc lý thuyết của ngày, kèm tài liệu gốc được dẫn ở cuối mỗi file |
| 13:00–17:00 | Làm lab hoặc bước hướng dẫn tương ứng, rồi áp dụng vào project thật (`adventure_works`, `thelook`) |
| 18:30–20:30 | Luyện SQL, từ tuần 8 chuyển sang luyện phỏng vấn ([câu hỏi GĐ3](GD3-ly-thuyet/cau-hoi-on-tap.md)) |
| 20:30–22:30 | Tự trả lời "Câu hỏi tự kiểm tra" không nhìn tài liệu; viết README / ADR / playbook |

## Công cụ

dbt-core 1.12 · dbt-duckdb 1.11 · DuckDB 1.5 (ghim `<2`) · automate_dv 0.11.5 · dbt-bigquery 1.12 · sqlfluff 4 · dbt-metricflow 0.15 · Elementary 0.26 · Dagster 1.13 · Airflow 3.4 + Cosmos 1.16 · Cube 1.6 · dlt 1.32 · GitHub Actions. Ghi chú phiên bản chi tiết và các hành vi đã kiểm chứng nằm ở cuối [GD2-ly-thuyet/README.md](GD2-ly-thuyet/README.md) và [GD3-ly-thuyet/README.md](GD3-ly-thuyet/README.md).

## Project liên quan

- `adventure_works`: project dbt chính trên Snowflake, nơi áp dụng mọi kỹ thuật học ở đây (Kimball, Data Vault, sau này là Mesh)
- `thelook-analytics`: project 2 trên BigQuery, dựng theo [bai-tap-bigquery-thelook](bai-tap-bigquery-thelook/README.md)
- Portfolio: [tranduc.site](https://tranduc.site/landing/) · GitHub: [tranduc2204](https://github.com/tranduc2204)
