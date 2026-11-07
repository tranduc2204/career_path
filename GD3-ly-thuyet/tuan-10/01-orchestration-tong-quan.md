# 10.1 Orchestration cho dbt: các khái niệm và mẫu thiết kế

## Orchestrator làm gì mà cron không làm

| Nhu cầu | cron + `dbt build` | Orchestrator |
|---|---|---|
| Chạy theo lịch | ✅ | ✅ |
| Chờ nguồn sẵn sàng rồi mới chạy | ❌ | sensor / data-aware scheduling |
| Retry khi lỗi tạm thời | tự viết | cấu hình |
| Chạy lại **một phần** (model lỗi + phía sau) | tay | UI / CLI |
| Lịch sử, log, thời gian từng bước | file log | UI, metadata DB |
| Cảnh báo | tự viết | tích hợp Slack / email / PagerDuty |
| Backfill nhiều ngày | vòng lặp tay | partition / logical date |
| Phối hợp nhiều công cụ (ingest → dbt → reverse ETL → ML) | khó | DAG xuyên công cụ |

## Task-centric và asset-centric

| | Task-centric (Airflow truyền thống) | Asset-centric (Dagster; Airflow 3 có Assets) |
|---|---|---|
| Đơn vị | **Task**: "chạy lệnh X" | **Asset**: "bảng `fct_orders`" |
| Câu hỏi tự nhiên | "Task lúc 06:30 hôm qua có chạy không?" | "`fct_orders` cập nhật lần cuối khi nào, từ dữ liệu nào, test có xanh không?" |
| Lineage | giữa task | giữa **dữ liệu** (khớp với DAG của dbt) |
| Lịch | theo thời gian | theo thời gian **hoặc** theo trạng thái dữ liệu (upstream mới → build) |

dbt vốn đã là asset-centric (mỗi model là một bảng), nên công cụ asset-centric khớp tự nhiên. Airflow 3 (2025) đưa **Assets** (trước gọi là Datasets) thành khái niệm hạng nhất để lên lịch theo dữ liệu, thu hẹp khoảng cách này.

## Mẫu chạy dbt trong orchestrator

| Mẫu | Mô tả | Ưu | Nhược |
|---|---|---|---|
| **A. Một task `dbt build`** | `BashOperator` / một op gọi `dbt build` cho cả project | Đơn giản, nhanh (dbt tự chạy song song) | Lỗi 1 model là cả task đỏ; chạy lại = chạy lại hết (đỡ hơn với `dbt retry`) |
| **B. Mỗi model một task** | Cosmos `DbtDag` / `DbtTaskGroup`, dagster-dbt | Thấy từng model trong UI, retry từng model, lineage | Mỗi task một tiến trình dbt → **chậm hơn nhiều** (lab: 34 task ~4,5 phút so với `dbt build` ~15 giây) |
| **C. Theo selector / domain** | vài task, mỗi task `dbt build -s tag:commerce` | Cân bằng, khớp với ownership | Phải tự giữ selector cho đúng |
| **D. Hướng sự kiện** | build khi nguồn có dữ liệu mới (`source_status:fresher+`, sensor, declarative automation) | Không chạy thừa, đúng SLA | Phức tạp hơn khi debug |

Không có mẫu "đúng nhất". Project 30 model, 1 đội: A hoặc C là đủ. 500 model, nhiều đội, SLA khác nhau: B hoặc D.

## Những điểm hay hỏng khi đưa dbt vào orchestrator

- **Parse chậm**: mỗi lần scheduler đọc DAG mà gọi `dbt ls` thì rất chậm. Đọc **`manifest.json`** có sẵn (Cosmos `LoadMode.DBT_MANIFEST`, dagster-dbt `manifest=`), và sinh manifest trong CI/CD.
- **Dependency xung đột**: Airflow và dbt cùng muốn những bản thư viện khác nhau → venv riêng cho dbt (`dbt_executable_path`, `ExecutionMode.VIRTUALENV`, container).
- **Đồng thời**: DuckDB một tiến trình ghi (`max_active_tasks=1` trong lab). Warehouse thật thì giới hạn concurrency theo warehouse size / slot.
- **Profile và bí mật**: không đưa `profiles.yml` có mật khẩu vào image. Dùng connection của Airflow (Cosmos `ProfileMapping`) hoặc biến môi trường.
- **Test**: chạy ở đâu (`TestBehavior.AFTER_EACH` / asset check), lỗi test có chặn downstream không? Phải **giống** hành vi `dbt build` mà team đang hiểu.

## Retry: hai tầng

- **Orchestrator retry**: chạy lại task sau N phút. Hợp với lỗi tạm thời (mạng, warehouse bận).
- **`dbt retry`**: đọc `run_results.json` lần trước, chỉ chạy lại node lỗi và phía sau. Hợp với mẫu A.
- **Không retry** lỗi logic (test fail vì dữ liệu sai): retry chỉ tốn tiền và làm chậm cảnh báo.

## Backfill

- Airflow: mỗi lần chạy có **logical date** → truyền vào dbt bằng `--vars '{"run_date": "{{ ds }}"}'`, model incremental dùng `var('run_date')`. Backfill = chạy lại DAG cho khoảng ngày.
- Dagster: **partition** (ngày) trên asset → dagster-dbt truyền khoảng thời gian vào `--vars`. Backfill = chọn khoảng partition trong UI.
- dbt ≥ 1.9: **microbatch** (`incremental_strategy='microbatch'`, `event_time`, `batch_size`) + `dbt run --event-time-start ... --event-time-end ...`. dbt tự chia lô, nên orchestrator chỉ cần truyền khoảng ngày.

## Câu hỏi tự kiểm tra

1. Project 40 model, chạy 1 lần/ngày, 1 đội. Bạn chọn mẫu nào? Còn 600 model, 6 đội, SLA khác nhau?
2. Viết ra 3 câu hỏi vận hành mà UI asset-centric trả lời trong 1 click còn task-centric thì không.
3. `dbt retry` cần artifact gì, và trong Airflow artifact đó nằm ở đâu giữa các lần chạy task?
