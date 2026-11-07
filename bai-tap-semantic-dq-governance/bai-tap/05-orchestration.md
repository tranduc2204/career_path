# 05 — Orchestration: Dagster và Airflow + Cosmos (O1–O5)

> Lý thuyết: [GD3-ly-thuyet/tuan-10](../../GD3-ly-thuyet/README.md#tuần-10-1712--2312--orchestration-và-governance) (10.1–10.4). Chấm: `python scripts/check.py O`.
> Đã kiểm chứng 07/11/2026: dagster 1.13.29 + dagster-dbt 0.29.29 (cùng venv với lab); Airflow 3.4.0 + astronomer-cosmos 1.16.0 (venv riêng), `airflow dags test` chạy hết 34 task thành công trong ~4,5 phút.

Đến giờ "pipeline sáng nay" là `scripts/run_day.sh`: một shell script chạy tay. Production cần nhiều hơn thế: lịch chạy, retry, chạy lại một phần, xem được lineage và lịch sử, cảnh báo khi hỏng. Bạn sẽ dựng cùng một pipeline bằng hai công cụ phổ biến nhất, rồi viết ADR chọn một.

Trước khi làm: `dbt parse` (cả hai công cụ đọc `target/manifest.json`).

---

## Phần A — Dagster (O1–O4)

Viết `orchestration/dagster_maystore/definitions.py` (có khung sẵn với TODO). Chạy UI:

```bash
cd lab
dagster dev -m orchestration.dagster_maystore.definitions     # http://localhost:3000
```

### O1 ⭐⭐ — dbt model thành asset

- `DbtProject(project_dir=LAB_DIR, profiles_dir=LAB_DIR)` + `prepare_if_dev()`
- Một hàm `@dbt_assets(manifest=dbt_project.manifest_path, ...)` gọi `dbt.cli(["build"], context=context).stream()`
- Resource `dbt = DbtCliResource(project_dir=dbt_project)`
- **Loại các model của package Elementary** (bảng hệ thống, không phải asset nghiệp vụ): tham số `exclude` của `@dbt_assets` nhận cú pháp selector của dbt

Mở UI → *Assets* → *View lineage*: bạn thấy đúng DAG của dbt, có thêm các source ở đầu.

### O2 ⭐⭐ — Translator: tên asset và nhóm

Viết một lớp kế thừa `DagsterDbtTranslator`:

- `get_asset_key`: source `shop.orders` → asset key `["raw", "shop", "orders"]`. Model giữ mặc định.
- `get_group_name`: group asset = **group của dbt** (`commerce`, `customer`, `growth`) từ G1. Model không có group thì cho vào `platform`.

Asset nguồn hiện trong UI nhưng **không materialize được**: Dagster chỉ quan sát, connector mới là bên tạo ra chúng. `check.py` kiểm tra điều này.

### O3 ⭐ — Lịch 06:30 giờ Việt Nam

`define_asset_job("daily_build", selection="*")` + `ScheduleDefinition(cron_schedule="30 6 * * *", execution_timezone="Asia/Ho_Chi_Minh")`.

Câu hỏi: lịch theo giờ cố định có vấn đề gì khi connector mkt chết 3 ngày (Q1)? Đọc về **sensor** và **declarative automation** (`AutomationCondition`) trong lý thuyết 10.3.

### O4 ⭐⭐ — Asset check + chạy thật

- Mỗi test dbt tự thành **asset check** gắn vào asset tương ứng (dagster-dbt bật mặc định). Kiểm tra trong UI: asset `fct_orders` có check `unique_fct_orders_order_id`.
- `check.py O4` chạy thật `materialize(...)` cho `fct_ad_spend` **và upstream** của nó, trong một Dagster instance tạm. Bạn tự thử trong UI: chọn `fct_ad_spend` → *Materialize selected with upstream*.

Thử thêm (không chấm): chạy `simulate.py next` tới ngày 6, materialize toàn bộ trong UI. Asset nào đỏ, asset nào bị skip, asset check nào fail? So với output của `run_day.sh`.

---

## Phần B — Airflow 3 + Cosmos (O5 ⭐⭐⭐)

Airflow có rất nhiều dependency, nên chạy trong **venv riêng**. dbt vẫn dùng venv của lab.

```bash
cd lab/orchestration/airflow
uv sync                                   # Airflow 3 + astronomer-cosmos (~230 MB)
export AIRFLOW_HOME=$PWD/.airflow
export AIRFLOW__CORE__DAGS_FOLDER=$PWD/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
.venv/bin/airflow db migrate
```

Viết `dags/mayshop_dbt.py` tạo `DbtDag` với `dag_id="mayshop_dbt"`:

| Cấu hình | Giá trị | Vì sao |
|---|---|---|
| `ProjectConfig` | `dbt_project_path=<lab>`, `manifest_path=<lab>/target/manifest.json` | Đọc manifest: parse DAG nhanh, scheduler không phải gọi dbt |
| `ProfileConfig` | `profile_name="lab"`, `target_name="dev"`, `profiles_yml_filepath=<lab>/profiles.yml` | Dùng lại profile có sẵn |
| `ExecutionConfig` | `dbt_executable_path=<venv của lab>/bin/dbt` | dbt không cài trong venv Airflow |
| `RenderConfig` | `load_method=LoadMode.DBT_MANIFEST`, `select=["path:models"]`, `test_behavior=TestBehavior.AFTER_EACH` | Bỏ model của Elementary; test chạy ngay sau model |
| `operator_args` | `{"install_deps": False}` | `dbt_packages` đã có |
| DAG | `schedule="30 6 * * *"`, `catchup=False`, **`max_active_tasks=1`** | DuckDB chỉ cho 1 tiến trình ghi |

Đường dẫn: đọc `MAYSHOP_LAB_DIR` / `MAYSHOP_DBT_BIN` từ biến môi trường nếu có, mặc định tính theo vị trí file DAG. `check.py` đặt 2 biến này khi chấm.

```bash
.venv/bin/airflow tasks list mayshop_dbt          # mỗi model → <model>.run + <model>.test
.venv/bin/airflow dags test mayshop_dbt 2026-12-04    # chạy thật toàn bộ, vài phút
.venv/bin/airflow standalone                       # UI http://localhost:8080 (mật khẩu in ra terminal)
```

Đo thời gian `dags test` và so với `dbt build` (~15 giây). Vì sao chậm hơn nhiều? (Mỗi task là một tiến trình `dbt` riêng: parse project, mở kết nối...) Khi nào đánh đổi này đáng giá, khi nào nên chỉ có **một task `dbt build`**? Đọc về `ExecutionMode` và `TestBehavior.BUILD` của Cosmos.

---

## ADR chọn orchestrator (sản phẩm của tuần 10)

Viết `docs/adr/0003-orchestrator.md` theo mẫu ở lý thuyết 10.4. Bắt buộc có **số đo của chính bạn**:

| Tiêu chí | Dagster | Airflow + Cosmos |
|---|---|---|
| Thời gian chạy hết pipeline | | |
| Số dòng code / cấu hình | | |
| Chạy lại 1 model + downstream | thao tác gì? | thao tác gì? |
| Test dbt hiển thị ở đâu | asset check | task `.test` |
| Lineage tới source / dashboard | | |
| Lịch theo dữ liệu (data-aware) | | Assets / Datasets của Airflow |
| Đội đã quen | | |

Kết luận cho **Mây Shop** (3 đội, 1 dbt project, sắp tách Mesh ở tuần 12) và cho **một ngân hàng đang có 300 DAG Airflow**. Hai kết luận có thể khác nhau.

## Câu hỏi tự kiểm tra

1. "Task-centric" và "asset-centric" khác nhau thế nào? Lấy ví dụ một câu hỏi vận hành mà cách asset-centric trả lời dễ hơn.
2. Vì sao không nên để Airflow gọi `dbt build` cho cả project bằng `BashOperator` khi project có 300 model? Và vì sao đôi khi đó lại là lựa chọn đúng?
3. Retry ở tầng orchestrator và `dbt retry` khác nhau thế nào?
4. Backfill 7 ngày cho một incremental model: Dagster (partition) và Airflow (logical date) truyền ngày vào dbt bằng cách nào?
