"""Đáp án tham khảo: giết cả 8 mutant. Mỗi test kiểm MỘT hành vi và đặt tên theo hành vi đó."""
from datetime import datetime, timezone

import duckdb
import pytest

from pipeline.mayshop_api import parse_vnd, run


def q(workdir, sql):
    with duckdb.connect(str(workdir / "mayshop.duckdb"), read_only=True) as con:
        return con.execute(sql).fetchall()


# ------------------------------------------------------------------ unit test: hàm thuần, không cần API
@pytest.mark.parametrize("raw, expected", [("1.290.000", 1_290_000), ("99.000", 99_000), ("0", 0), (597000, 597_000)])
def test_parse_vnd_reads_dot_as_thousands_separator(raw, expected):          # P6
    assert parse_vnd(raw) == expected


# ------------------------------------------------------------------ integration test: API giả → DuckDB thật
def test_first_run_loads_every_page(api, workdir):                           # P1
    run(api.base_url, workdir, page_size=50)                                 # 120 đơn = 3 trang
    assert q(workdir, "select count(*) from raw_api.orders") == [(120,)]
    assert q(workdir, "select count(*) from raw_api.customers") == [(40,)]


def test_amount_is_integer_vnd(api, workdir):                                # P6 (đi qua cả pipeline)
    run(api.base_url, workdir)
    assert q(workdir, "select sum(amount) from raw_api.orders") == \
        [(sum(o["amount"] for o in api.days[0]),)]


def test_updated_at_keeps_timezone(api, workdir):                            # P5
    run(api.base_url, workdir)
    (ts,) = q(workdir, "select updated_at from raw_api.orders where order_id = 5001")[0]
    # API: 2026-12-01T08:07:00+07:00  ==  01:07 UTC
    assert ts.astimezone(timezone.utc) == datetime(2026, 12, 1, 1, 7, tzinfo=timezone.utc)


def test_nested_items_go_to_child_table(api, workdir):                       # P8
    run(api.base_url, workdir)
    n_items = sum(len(o["items"]) for o in api.days[0])
    assert q(workdir, "select count(*) from raw_api.orders__items") == [(n_items,)]
    # mỗi dòng con trỏ về đúng đơn cha
    assert q(workdir, """select count(*) from raw_api.orders__items i
                         left join raw_api.orders o on i._dlt_parent_id = o._dlt_id
                         where o._dlt_id is null""") == [(0,)]


def test_second_run_merges_updates_without_duplicates(api, workdir):         # P3, P4
    run(api.base_url, workdir)
    api.set_day(1)                                                           # 6 đơn đổi trạng thái + 8 đơn mới
    run(api.base_url, workdir)
    assert q(workdir, "select count(*), count(distinct order_id) from raw_api.orders") == [(128, 128)]
    assert q(workdir, "select status from raw_api.orders where order_id = 5004") == [("shipped",)]


def test_second_run_only_asks_api_for_new_changes(api, workdir):             # P2
    run(api.base_url, workdir)
    api.set_day(1)
    api.requests.clear()
    pipeline, _ = run(api.base_url, workdir)
    since = [query.get("updated_since") for path, query in api.requests if path == "/v1/orders"]
    assert since and all(s and s.startswith("2026-12-01T22:") for s in since)   # mốc = updated_at lớn nhất của lần 1
    assert pipeline.last_trace.last_normalize_info.row_counts["orders"] == 14


def test_retries_when_api_rate_limits(api, workdir):                         # P7
    api.flaky = True                                                         # lần gọi đầu mỗi endpoint → 429
    run(api.base_url, workdir)
    assert q(workdir, "select count(*) from raw_api.orders") == [(120,)]
    assert sum(1 for path, _ in api.requests if path == "/v1/orders") >= 4   # 1 lần 429 + 3 trang
