"""Airflow 3 + Cosmos cho lab Mây Shop (bài O5).

Cosmos đọc dbt project rồi sinh MỖI MODEL thành một task group (run + test của model đó),
giữ đúng thứ tự phụ thuộc của dbt. Airflow chạy trong venv riêng (orchestration/airflow/.venv),
còn dbt chạy bằng venv của lab, nên phải chỉ đường tới file `dbt` của lab.
"""
import os
from datetime import datetime
from pathlib import Path

from cosmos import DbtDag, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode, TestBehavior

LAB_DIR = Path(os.environ.get("MAYSHOP_LAB_DIR", Path(__file__).resolve().parents[3]))
DBT_BIN = os.environ.get("MAYSHOP_DBT_BIN", str(LAB_DIR.parent / ".venv" / "bin" / "dbt"))

mayshop_dbt = DbtDag(
    dag_id="mayshop_dbt",
    project_config=ProjectConfig(
        dbt_project_path=LAB_DIR,
        manifest_path=LAB_DIR / "target" / "manifest.json",   # đọc manifest có sẵn: parse DAG nhanh, không gọi dbt
    ),
    profile_config=ProfileConfig(
        profile_name="lab",
        target_name="dev",
        profiles_yml_filepath=LAB_DIR / "profiles.yml",
    ),
    execution_config=ExecutionConfig(dbt_executable_path=DBT_BIN),
    render_config=RenderConfig(
        load_method=LoadMode.DBT_MANIFEST,
        select=["path:models"],                 # chỉ model của project, bỏ package Elementary
        test_behavior=TestBehavior.AFTER_EACH,  # test chạy ngay sau model của nó
    ),
    operator_args={"install_deps": False},     # dbt_packages đã có sẵn trong lab
    schedule="30 6 * * *",
    start_date=datetime(2026, 12, 1),
    catchup=False,
    max_active_tasks=1,                         # DuckDB chỉ cho 1 tiến trình ghi tại một thời điểm
    tags=["dbt", "mayshop"],
)
