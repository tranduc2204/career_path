"""Dagster cho lab Mây Shop — BẠN VIẾT FILE NÀY (bài O1–O4, đề: bai-tap/05-orchestration.md).

Chạy UI:   cd lab && dagster dev -m orchestration.dagster_maystore.definitions
Chấm:      python scripts/check.py O

Yêu cầu:
  O1  mỗi model dbt của project là 1 asset (bỏ package Elementary)          → @dbt_assets(..., exclude=...)
  O2  source shop.orders → asset key ["raw", "shop", "orders"]; group asset = group của dbt
                                                                             → DagsterDbtTranslator
  O3  schedule chạy toàn bộ lúc 06:30 giờ Việt Nam                            → ScheduleDefinition
  O4  test dbt thành asset check; materialize được fct_ad_spend + upstream
Biến bắt buộc ở cuối file: `defs = Definitions(...)`
"""
from pathlib import Path

from dagster import Definitions

LAB_DIR = Path(__file__).resolve().parents[2]

# TODO O1: DbtProject(project_dir=LAB_DIR, profiles_dir=LAB_DIR) + prepare_if_dev()
# TODO O1: @dbt_assets(manifest=..., exclude="package:elementary") chạy `dbt build`
# TODO O2: class MayShopTranslator(DagsterDbtTranslator): get_asset_key, get_group_name
# TODO O3: define_asset_job + ScheduleDefinition(cron_schedule="30 6 * * *", execution_timezone=...)

defs = Definitions()
