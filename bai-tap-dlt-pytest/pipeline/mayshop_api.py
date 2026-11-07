"""Pipeline dlt: API Mây Shop → DuckDB (đây là code "production" bạn cần VIẾT TEST cho nó).

  orders     : incremental theo updated_at (hỏi API `updated_since`), merge theo order_id,
               mảng lồng items → bảng con orders__items, amount "1.290.000" → 1290000
  customers  : nạp lại toàn bộ (replace)
"""
from pathlib import Path

import dlt
import pendulum
from dlt.sources.helpers import requests   # requests của dlt: tự retry 429 / 5xx / lỗi mạng

INITIAL_CURSOR = "2026-01-01T00:00:00+07:00"


def parse_vnd(value) -> int:
    """'1.290.000' → 1290000. Dấu chấm là phân cách hàng nghìn, KHÔNG phải dấu thập phân."""
    return int(str(value).replace(".", "").replace(",", "").strip())


def _paginate(url: str, params: dict, page_size: int):
    page = 1
    while True:
        resp = requests.get(url, params={**params, "page": page, "page_size": page_size})
        resp.raise_for_status()
        body = resp.json()
        yield body["data"]
        if not body.get("next_page"):
            break
        page = body["next_page"]


@dlt.source(name="mayshop", max_table_nesting=1)
def mayshop_source(base_url: str, page_size: int = 50):

    @dlt.resource(primary_key="order_id", write_disposition="merge")
    def orders(updated_at=dlt.sources.incremental("updated_at", initial_value=pendulum.parse(INITIAL_CURSOR))):
        since = updated_at.last_value
        for rows in _paginate(f"{base_url}/v1/orders", {"updated_since": since.isoformat()}, page_size):
            for o in rows:
                o["amount"] = parse_vnd(o["amount"])
                o["updated_at"] = pendulum.parse(o["updated_at"])   # giữ múi giờ → dlt lưu UTC đúng
                yield o

    @dlt.resource(primary_key="customer_id", write_disposition="replace")
    def customers():
        for rows in _paginate(f"{base_url}/v1/customers", {}, page_size):
            yield rows

    return orders, customers


def make_pipeline(workdir: Path, name: str = "mayshop_api") -> dlt.Pipeline:
    """Pipeline ghi vào <workdir>/mayshop.duckdb, state của dlt nằm trong <workdir>/.dlt_pipelines."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    return dlt.pipeline(
        pipeline_name=name,
        destination=dlt.destinations.duckdb(str(workdir / "mayshop.duckdb")),
        dataset_name="raw_api",
        pipelines_dir=str(workdir / ".dlt_pipelines"),
    )


def run(base_url: str, workdir: Path, page_size: int = 50):
    pipeline = make_pipeline(workdir)
    info = pipeline.run(mayshop_source(base_url, page_size=page_size))
    return pipeline, info


if __name__ == "__main__":
    import sys
    from fake_api.server import FakeApi

    api = FakeApi().start()
    p, info = run(api.base_url, Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    print(info)
    api.stop()
