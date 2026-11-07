"""Dagster cho lab Mây Shop (bài O1–O4).

Chạy UI:   cd lab && dagster dev -m orchestration.dagster_maystore.definitions
Chạy thử:  cd lab && python -m orchestration.dagster_maystore.definitions   (materialize fct_ad_spend + upstream)
"""
from pathlib import Path
from typing import Any, Mapping

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

LAB_DIR = Path(__file__).resolve().parents[2]

# O1: trỏ tới dbt project của lab. prepare_if_dev() tự `dbt parse` khi chạy `dagster dev`
dbt_project = DbtProject(project_dir=LAB_DIR, profiles_dir=LAB_DIR)
dbt_project.prepare_if_dev()


class MayShopTranslator(DagsterDbtTranslator):
    """O2: đặt tên asset cho dễ đọc trong UI."""

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        if dbt_resource_props["resource_type"] == "source":
            # source shop.orders → asset ["raw", "shop", "orders"] (do connector tạo, Dagster chỉ quan sát)
            return AssetKey(["raw", dbt_resource_props["source_name"], dbt_resource_props["name"]])
        return super().get_asset_key(dbt_resource_props)

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        # dùng group của dbt (commerce / customer / growth); model không có group → "platform"
        return dbt_resource_props.get("group") or "platform"


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=MayShopTranslator(),
    exclude="package:elementary",          # bảng hệ thống của Elementary không phải asset nghiệp vụ
)
def mayshop_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # `dbt build` = run + test; mỗi test thành một asset check (O4)
    yield from dbt.cli(["build"], context=context).stream()


# O3: job + lịch chạy mỗi sáng 06:30 giờ Việt Nam (sau khi connector nạp xong lúc 06:00)
daily_job = define_asset_job("daily_build", selection="*")
daily_schedule = ScheduleDefinition(
    name="daily_0630",
    job=daily_job,
    cron_schedule="30 6 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)

defs = Definitions(
    assets=[mayshop_dbt_assets],
    jobs=[daily_job],
    schedules=[daily_schedule],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)


if __name__ == "__main__":
    from dagster import AssetSelection, materialize

    sel = AssetSelection.keys(AssetKey(["fct_ad_spend"])).upstream()
    result = materialize([mayshop_dbt_assets], selection=sel, resources={"dbt": DbtCliResource(project_dir=dbt_project)})
    print("success:", result.success)
