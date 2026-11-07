# 10.2 Airflow 3 + Cosmos

> Đã chạy 07/11/2026: apache-airflow **3.4.0** + astronomer-cosmos **1.16.0**, DAG lab 34 task, `airflow dags test` thành công.

## Airflow 3 cho người dùng dbt: những gì cần biết

- **DAG** = đồ thị task, định nghĩa bằng Python. Mỗi lần chạy (*DAG run*) có **logical date**.
- **Scheduler** đọc DAG, **dag processor** parse file DAG, **API server** phục vụ UI (Airflow 3 tách khỏi webserver cũ). **Task SDK**: task chạy cách ly, giao tiếp qua API thay vì truy cập thẳng metadata DB.
- **Assets** (`airflow.sdk.Asset`, trước là Dataset): lên lịch DAG khi asset được cập nhật (data-aware scheduling).
- Import mới: `from airflow.sdk import DAG, task, Asset`. Nhiều import cũ (`airflow.models.dagbag`...) vẫn chạy nhưng in cảnh báo deprecated (gặp trong lab: `DagBag` nay ở `airflow.dag_processing.dagbag`).
- Chạy thử không cần scheduler: `airflow dags test <dag_id> <ngày>`. UI cho máy cá nhân: `airflow standalone`.

## Cosmos: dbt project → DAG Airflow

Cosmos (Astronomer, mã nguồn mở) đọc dbt project rồi sinh **mỗi model thành một task group** (`<model>.run` + `<model>.test`), giữ đúng thứ tự phụ thuộc.

```python
from cosmos import DbtDag, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode, TestBehavior

mayshop_dbt = DbtDag(
    dag_id="mayshop_dbt",
    project_config=ProjectConfig(dbt_project_path=LAB_DIR,
                                 manifest_path=LAB_DIR / "target/manifest.json"),
    profile_config=ProfileConfig(profile_name="lab", target_name="dev",
                                 profiles_yml_filepath=LAB_DIR / "profiles.yml"),
    execution_config=ExecutionConfig(dbt_executable_path=DBT_BIN),
    render_config=RenderConfig(load_method=LoadMode.DBT_MANIFEST,
                               select=["path:models"],
                               test_behavior=TestBehavior.AFTER_EACH),
    operator_args={"install_deps": False},
    schedule="30 6 * * *", start_date=datetime(2026, 12, 1), catchup=False,
    max_active_tasks=1,
)
```

| Cấu hình | Lựa chọn | Ghi chú |
|---|---|---|
| `LoadMode` | `AUTOMATIC` (mặc định), `DBT_MANIFEST`, `DBT_LS`, `DBT_LS_FILE`, `DBT_LS_CACHE`, `CUSTOM` | `DBT_MANIFEST` nhanh nhất, không gọi dbt khi parse DAG; cần manifest mới trong image / CI |
| `ExecutionMode` | `LOCAL` (mặc định), `VIRTUALENV`, `DOCKER`, `KUBERNETES`, `AIRFLOW_ASYNC`, `WATCHER`, các biến thể cloud (EKS, ECS, Cloud Run...) | `LOCAL` + `dbt_executable_path` trỏ venv riêng là cách gọn cho máy cá nhân |
| `TestBehavior` | `AFTER_EACH` (mặc định), `BUILD`, `AFTER_ALL`, `NONE` | `BUILD` dùng `dbt build` cho mỗi node (gọn hơn: 1 task/model) |
| `ProfileConfig` | `profiles_yml_filepath` **hoặc** `profile_mapping` | Production: `profile_mapping` (vd `SnowflakeUserPasswordProfileMapping(conn_id=...)`) đọc từ Airflow connection, không cần file chứa mật khẩu |
| `RenderConfig.select/exclude` | cú pháp selector của dbt | Tách nhiều DAG theo domain: `select=["tag:commerce"]` |

`DbtTaskGroup` đặt dbt **vào trong** một DAG lớn hơn: `ingest >> DbtTaskGroup(...) >> reverse_etl`.

## Chạy trong lab

```bash
cd lab/orchestration/airflow && uv sync
export AIRFLOW_HOME=$PWD/.airflow AIRFLOW__CORE__DAGS_FOLDER=$PWD/dags AIRFLOW__CORE__LOAD_EXAMPLES=False
.venv/bin/airflow db migrate
.venv/bin/airflow tasks list mayshop_dbt
.venv/bin/airflow dags test mayshop_dbt 2026-12-04
```

Quan sát: 34 task, ~4,5 phút trên laptop. Mỗi task khởi động một tiến trình `dbt` (parse project, mở kết nối). `dbt build` cả project chỉ ~15 giây. Đây là cái giá của "thấy từng model trong UI".

## Production: những điều cần nghĩ

- **Đóng gói:** image Airflow có sẵn dbt project + `manifest.json` (sinh trong CI), dbt trong venv riêng hoặc container riêng.
- **Bí mật:** Airflow connections / secrets backend (Vault, AWS Secrets Manager), Cosmos `profile_mapping`.
- **Artifact:** lưu `run_results.json`, `manifest.json` lên object storage sau mỗi lần chạy (cho `dbt retry`, `--state`, Elementary, OpenMetadata).
- **Cảnh báo:** `on_failure_callback` gửi Slack, kèm link log và tên model.
- **Managed:** Astronomer, Cloud Composer (GCP), MWAA (AWS). Đỡ phải tự vận hành scheduler + metadata DB.

## Câu hỏi tự kiểm tra

1. Vì sao nên `LoadMode.DBT_MANIFEST` cho production? Manifest đến từ đâu?
2. `TestBehavior.AFTER_EACH` và `BUILD` khác nhau thế nào về số task và hành vi khi test fail?
3. Viết một DAG: `ingest_shop` (giả) → `DbtTaskGroup` chỉ các model `tag:commerce` → `notify_finance`. Lịch theo Asset của bảng nguồn thay vì cron.

## Tài liệu

- Airflow 3 docs: *Upgrading to Airflow 3*, *Assets*, *Task SDK*
- astronomer-cosmos docs: *Getting started*, *Parsing methods (LoadMode)*, *Execution modes*, *Testing behavior*, *Profiles*
