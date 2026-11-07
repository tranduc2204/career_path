# 10.3 Dagster + dbt

> Đã chạy 07/11/2026: dagster **1.13.29** + dagster-dbt **0.29.29**, cùng venv với dbt-core 1.12.6. Lab: 25 asset, 35 asset check, materialize một phần đồ thị thành công.

## Mô hình của Dagster

| Khái niệm | Nghĩa | Với dbt |
|---|---|---|
| **Asset** | Một đối tượng dữ liệu lâu dài (bảng, file, model ML) | Mỗi model / seed / snapshot = 1 asset; mỗi source = 1 asset bên ngoài (quan sát) |
| **Asset key** | Tên duy nhất, dạng đường dẫn | Mặc định theo cấu hình schema/tên model, tuỳ biến bằng translator |
| **Asset check** | Kiểm tra gắn vào asset | Mỗi data test của dbt |
| **Materialization** | Một lần tạo / cập nhật asset | Một lần chạy model |
| **Job / Schedule / Sensor** | Chọn tập asset, chạy theo lịch / theo sự kiện | |
| **Declarative automation** | `AutomationCondition`: "build khi upstream cập nhật", "khi quá hạn"... | Thay cho lịch cứng |
| **Partition** | Chia asset theo thời gian / khoá | Backfill theo ngày, truyền vào dbt bằng `--vars` |
| **Resource** | Kết nối dùng chung | `DbtCliResource` |

## Code tối thiểu

```python
from dagster import AssetExecutionContext, AssetKey, Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

dbt_project = DbtProject(project_dir=LAB_DIR, profiles_dir=LAB_DIR)
dbt_project.prepare_if_dev()                 # `dagster dev` tự dbt parse → manifest mới

class MayShopTranslator(DagsterDbtTranslator):
    def get_asset_key(self, props):
        if props["resource_type"] == "source":
            return AssetKey(["raw", props["source_name"], props["name"]])
        return super().get_asset_key(props)
    def get_group_name(self, props):
        return props.get("group") or "platform"     # group của dbt → group của Dagster

@dbt_assets(manifest=dbt_project.manifest_path,
            dagster_dbt_translator=MayShopTranslator(),
            exclude="package:elementary")
def mayshop_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

daily = ScheduleDefinition(name="daily_0630", job=define_asset_job("daily_build", selection="*"),
                           cron_schedule="30 6 * * *", execution_timezone="Asia/Ho_Chi_Minh")

defs = Definitions(assets=[mayshop_dbt_assets], schedules=[daily],
                   resources={"dbt": DbtCliResource(project_dir=dbt_project)})
```

Điểm hay:

- Chọn `fct_ad_spend` + upstream trong UI → Dagster tự gọi `dbt build --select ...` đúng tập đó. **Một tiến trình dbt** cho cả lựa chọn, nên không chậm như mỗi model một task.
- Test dbt thành **asset check**: UI hiện ngay trên asset, lịch sử pass/fail theo thời gian.
- `.stream()` có thể nối thêm `.fetch_row_counts()`, `.fetch_column_metadata()` để ghi metadata (số dòng, schema) vào mỗi lần materialize.
- Source của dbt hiện như asset gốc (không materialize). Asset của dlt / Airbyte / Fivetran (tích hợp có sẵn) có thể **thay** các source đó, thành một đồ thị từ ingest tới dashboard.

## Components và `dg` (Dagster ≥ 1.10)

Dagster có thêm lớp **Components**: khai báo bằng YAML (`DbtProjectComponent`) và CLI `dg` để tạo project chuẩn (`dg scaffold`, `dg dev`). Code Python ở trên vẫn là cách nền tảng và dễ hiểu nhất. Components hợp khi nhiều đội cùng dùng một khuôn.

## Lịch theo dữ liệu

```python
from dagster import AutomationCondition

class MayShopTranslator(DagsterDbtTranslator):
    def get_automation_condition(self, props):
        if props.get("group") == "growth":
            return AutomationCondition.eager()                       # upstream mới → build ngay
        return AutomationCondition.on_cron("30 6 * * *", "Asia/Ho_Chi_Minh")   # còn lại: 06:30, khi upstream đã cập nhật
```

Muốn automation condition chạy, bật **automation sensor** (mặc định có trong `dagster dev`).

Với dbt: gán `automation_condition` qua translator (`get_automation_condition`), ví dụ `AutomationCondition.eager()` cho model rẻ, cron cho model đắt. Kịch bản Q1 của lab (connector mkt chết) là ví dụ điển hình: lịch cứng 06:30 sẽ build `fct_ad_spend` với dữ liệu cũ, còn điều kiện "khi upstream mới" thì đứng yên, kèm cảnh báo freshness.

## Partition cho incremental

```python
from dagster import DailyPartitionsDefinition
daily_partitions = DailyPartitionsDefinition(start_date="2026-10-01")

@dbt_assets(manifest=..., select="config.materialized:incremental", partitions_def=daily_partitions)
def incremental_assets(context, dbt):
    start, end = context.partition_time_window
    vars_ = {"start_date": start.isoformat(), "end_date": end.isoformat()}
    yield from dbt.cli(["build", "--vars", json.dumps(vars_)], context=context).stream()
```

Model đọc `var('start_date')`/`var('end_date')`. Backfill 7 ngày = chọn 7 partition trong UI.

## Câu hỏi tự kiểm tra

1. Vì sao chọn nhiều model trong Dagster không chậm như Cosmos `AFTER_EACH`?
2. Asset check từ dbt test có chặn downstream không? So với `dbt build`.
3. Thiết kế đồ thị cho Mây Shop: asset dlt (tuần 11) → dbt → saved query export. Asset nào có automation condition gì?

## Tài liệu

- Dagster docs: *dbt integration* (`dagster-dbt`), *Asset checks*, *Declarative automation*, *Partitions*, *Components / dg*
- Dagster University: khoá *Dagster & dbt* (miễn phí)
