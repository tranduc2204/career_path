#!/usr/bin/env python3
"""Tự chấm bài lab. Chạy từ thư mục lab/ SAU KHI đã `dbt build` / `dbt snapshot`.

  python scripts/check.py            # chấm tất cả
  python scripts/check.py I3 S1      # chỉ chấm vài bài

Kết quả:  ✅ PASS   ❌ FAIL   ⏭️  SKIP (chưa làm / chưa tới ngày cần thiết)
Ground truth luôn tính trực tiếp từ schema raw, không phụ thuộc code của bạn.
"""
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import duckdb

LAB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LAB_DIR / "lab.duckdb"
CODE_DIRS = ["models", "macros", "tests", "snapshots"]

PASS, FAIL, SKIP = "✅ PASS", "❌ FAIL", "⏭️  SKIP"


class Skip(Exception):
    pass


class Fail(Exception):
    pass


# --------------------------------------------------------------------------- helpers

con: duckdb.DuckDBPyConnection
DAY: int


def q(sql, params=None):
    return con.execute(sql, params or []).fetchall()


def q1(sql, params=None):
    return con.execute(sql, params or []).fetchone()[0]


def find(name):
    rows = q(
        """select table_schema from information_schema.tables
           where table_name = ? and table_schema <> 'raw'
           order by table_schema like 'dev%' desc, table_schema""",
        [name],
    )
    if not rows:
        raise Skip(f"chưa thấy bảng/view `{name}` (chưa build?)")
    return f'"{rows[0][0]}"."{name}"'


def columns(rel):
    schema, table = [p.strip('"') for p in rel.split(".")]
    return [r[0].lower() for r in q(
        "select column_name from information_schema.columns where table_schema = ? and table_name = ?",
        [schema, table],
    )]


def need_cols(rel, cols):
    have = columns(rel)
    missing = [c for c in cols if c not in have]
    if missing:
        raise Fail(f"{rel} thiếu cột {missing} (đang có: {have})")


def need_day(n, why):
    if DAY < n:
        raise Skip(f"cần tới ngày {n} ({why}); hiện ở ngày {DAY}")


def code_files():
    for d in CODE_DIRS:
        base = LAB_DIR / d
        if base.exists():
            yield from (p for p in base.rglob("*") if p.suffix in {".sql", ".yml", ".yaml"})


def code_matching(pattern, subdir=None):
    rx = re.compile(pattern, re.S)
    hits = []
    for p in code_files():
        if subdir and not str(p.relative_to(LAB_DIR)).startswith(subdir):
            continue
        if rx.search(p.read_text(encoding="utf-8")):
            hits.append(p.relative_to(LAB_DIR))
    return hits


def need_macro(name):
    if not code_matching(rf"{{%-?\s*macro\s+{name}\s*\(", "macros"):
        raise Skip(f"chưa thấy macro `{name}` trong macros/")


def per_key_counts(rel, key, where="true"):
    return dict(q(f"select {key}, count(*) from {rel} where {where} group by 1"))


def expect_counts(actual, expected, label, hint=""):
    bad = {k: (actual.get(k, 0), v) for k, v in expected.items() if actual.get(k, 0) != v}
    if bad:
        detail = ", ".join(f"{label} {k}: có {a}, cần {e}" for k, (a, e) in bad.items())
        raise Fail(detail + (f". {hint}" if hint else ""))


# --------------------------------------------------------------------------- ground truth

def truth_customer_versions(tracked=("city", "tier")):
    """Phiên bản SCD2 'đúng' theo CDC log: chỉ tạo phiên bản khi cột theo dõi đổi."""
    rows = q(f"""select customer_id, op, {', '.join(tracked)}, changed_at
                 from raw.customer_changelog order by customer_id, changed_at""")
    versions = defaultdict(list)          # cid -> [dict(values, valid_from, valid_to)]
    for cid, op, *vals, changed_at in rows:
        vals = tuple(v.strip() if isinstance(v, str) else v for v in vals)
        vs = versions[cid]
        is_open = bool(vs) and vs[-1]["valid_to"] is None
        if op == "D":
            if is_open:
                vs[-1]["valid_to"] = changed_at
            continue
        if is_open and vs[-1]["vals"] == vals:
            continue
        if is_open:
            vs[-1]["valid_to"] = changed_at
        vs.append({"vals": vals, "valid_from": changed_at, "valid_to": None})
    return versions


def active_customers():
    return {r[0] for r in q("select customer_id from raw.customers")}


# --------------------------------------------------------------------------- Jinja

def check_J1():
    need_macro("cents_to_dollars")
    used = code_matching(r"cents_to_dollars\s*\(", "models/staging")
    if len(used) < 3:
        raise Fail(f"mới dùng cents_to_dollars ở {len(used)} model staging (cần stg_products, stg_orders, stg_order_items)")
    rel = find("stg_products")
    bad = q1(f"""select count(*) from {rel} s join raw.products r using (product_id)
                 where s.list_price <> round(r.list_price_cents / 100.0, 2)""")
    if bad:
        raise Fail(f"{bad} sản phẩm có list_price sai")
    return f"dùng ở {len(used)} model staging, giá trị đúng"


def check_J2():
    need_macro("clean_string")
    if not code_matching(r"clean_string\s*\(", "models/staging"):
        raise Fail("chưa dùng clean_string trong models/staging")
    rel = find("stg_products")
    if q1(f"select count(*) from {rel} where product_name <> trim(product_name)"):
        raise Fail("product_name còn khoảng trắng thừa")
    if q1(f"select category from {rel} where product_id = 8") is not None:
        raise Fail("category rỗng ('') của sản phẩm 8 phải thành null")
    email = q1(f"select email from {find('stg_customers')} where customer_id = 2")
    if email != email.strip().lower():
        raise Fail(f"email khách 2 chưa trim + lower: {email!r}")
    return "trim / lower / chuỗi rỗng → null đều đúng"


def _status_matrix():
    truth = defaultdict(dict)
    for cid, st, n in q("select customer_id, status, count(*) from raw.orders group by 1, 2"):
        truth[cid][st] = n
    return truth


def check_J3():
    rel = find("customer_order_summary")
    statuses = ["placed", "shipped", "delivered", "cancelled"]
    need_cols(rel, ["customer_id", "total_orders"] + [f"orders_{s}" for s in statuses])
    truth = _status_matrix()
    for cid, *vals in q(f"select customer_id, {', '.join('orders_' + s for s in statuses)} from {rel}"):
        for s, v in zip(statuses, vals):
            if v != truth[cid].get(s, 0):
                raise Fail(f"khách {cid}: orders_{s} = {v}, cần {truth[cid].get(s, 0)}")
    return "đủ cột theo var order_statuses, số liệu khớp"


def check_J4():
    rel = find("customer_order_summary_dynamic")
    want = sorted(r[0] for r in q("select distinct status from raw.orders"))
    have = sorted(c[len("orders_"):] for c in columns(rel) if c.startswith("orders_"))
    if have != want:
        raise Fail(f"cột trạng thái {have} ≠ trạng thái thật trong dữ liệu {want} (đã build lại sau khi sang ngày mới?)")
    return f"cột sinh động theo dữ liệu: {have}"


def check_J5():
    missing = [t for t in ("is_positive", "one_current_row_per_key")
               if not code_matching(rf"{{%-?\s*test\s+{t}\s*\(", "tests")
               and not code_matching(rf"{{%-?\s*test\s+{t}\s*\(", "macros")]
    if len(missing) == 2:
        raise Skip("chưa thấy generic test nào")
    if missing:
        raise Fail(f"còn thiếu generic test: {missing}")
    if not code_matching(r"is_positive", "models") or not code_matching(r"one_current_row_per_key", ""):
        raise Fail("đã định nghĩa nhưng chưa gắn test vào YAML của model/snapshot")
    return "2 generic test đã định nghĩa và được dùng"


def check_J6():
    need_macro("generate_schema_name")
    return "đã override (tự kiểm tra: dbt build --target prod rồi xem schema)"


def check_J7():
    need_macro("get_incremental_filter")
    used = code_matching(r"get_incremental_filter\s*\(", "models")
    if not used:
        raise Fail("đã viết macro nhưng chưa model nào dùng")
    return f"dùng ở {', '.join(str(u) for u in used)}"


def check_J8():
    need_macro("audit_incremental_models")
    return "đã có (tự chạy: dbt run-operation audit_incremental_models)"


def check_J9():
    need_macro("days_between")
    if not code_matching(r"macro\s+duckdb__days_between", "macros"):
        raise Fail("thiếu bản cài đặt duckdb__days_between")
    if not code_matching(r"macro\s+default__days_between", "macros"):
        raise Fail("thiếu bản cài đặt default__days_between")
    if not code_matching(r"days_between\s*\(", "models"):
        raise Fail("chưa model nào dùng days_between")
    return "dispatch có default__ và duckdb__, đã dùng trong model"


def check_J10():
    need_macro("scd2_from_changelog")
    if not code_matching(r"scd2_from_changelog\s*\(", "models"):
        raise Fail("chưa model nào dùng scd2_from_changelog")
    return "macro được dùng (số liệu chấm ở S8)"


# --------------------------------------------------------------------------- Incremental

def check_I1():
    rel = find("fct_events_append")
    have, raw_total, raw_distinct = q1(f"select count(*) from {rel}"), q1("select count(*) from raw.events"), \
        q1("select count(distinct event_id) from raw.events")
    if have != raw_total:
        raise Fail(f"có {have} dòng, nguồn có {raw_total} dòng (append phải giữ nguyên mọi dòng đã nạp)")
    dups = have - q1(f"select count(distinct event_id) from {rel}")
    return f"{have} dòng = số dòng nguồn; trong đó {dups} dòng TRÙNG event_id ({raw_distinct} sự kiện thật) → xem I2"


def check_I2():
    rel = find("fct_events")
    dups = q1(f"select count(*) - count(distinct event_id) from {rel}")
    if dups:
        raise Fail(f"còn {dups} dòng trùng event_id")
    have, want = q1(f"select count(*) from {rel}"), q1("select count(distinct event_id) from raw.events")
    if have != want:
        raise Fail(f"có {have} sự kiện, cần {want}")
    return f"{have} sự kiện, không trùng"


def check_I3():
    rel = find("fct_orders")
    dups = q1(f"select count(*) - count(distinct order_id) from {rel}")
    if dups:
        raise Fail(f"{dups} dòng trùng order_id (thiếu unique_key?)")
    missing = [r[0] for r in q(f"select order_id from raw.orders except select order_id from {rel} order by 1")]
    if missing:
        late = q("select order_id, order_date, updated_at, _loaded_at from raw.orders where order_id in "
                 f"({', '.join(map(str, missing))}) order by 1")
        detail = "; ".join(f"{o} (order_date {d}, updated_at {u:%m-%d %H:%M}, _loaded_at {l:%m-%d %H:%M})"
                           for o, d, u, l in late)
        raise Fail(f"thiếu {len(missing)} đơn: {detail}. Watermark của bạn có bắt được đơn đến muộn?")
    wrong = q(f"""select r.order_id, f.order_status, r.status from raw.orders r join {rel} f using (order_id)
                  where f.order_status <> r.status order by 1 limit 5""")
    if wrong:
        raise Fail(f"trạng thái sai (order_id, đang có, đúng): {wrong}")
    bad_amt = q1(f"""select count(*) from raw.orders r join {rel} f using (order_id)
                     where abs(f.amount - r.amount_cents / 100.0) > 0.005""")
    if bad_amt:
        raise Fail(f"{bad_amt} đơn sai amount")
    return f"{q1(f'select count(*) from {rel}')} đơn, trạng thái & số tiền khớp nguồn"


def check_I5():
    rel = find("fct_daily_revenue")
    need_cols(rel, ["order_date", "order_count", "revenue"])
    truth = {d: (n, rev) for d, n, rev in q(
        """select order_date,
                  sum(case when status <> 'cancelled' then 1 else 0 end),
                  coalesce(sum(case when status <> 'cancelled' then amount_cents end), 0) / 100.0
           from raw.orders group by 1""")}
    have = {d: (n, float(rev)) for d, n, rev in q(f"select order_date, order_count, revenue from {rel}")}
    errs = []
    for d, (n, rev) in sorted(truth.items()):
        if d not in have:
            errs.append(f"{d}: thiếu ngày")
        elif have[d][0] != n or abs(have[d][1] - float(rev)) > 0.01:
            errs.append(f"{d}: có ({have[d][0]} đơn, {have[d][1]:.2f}), cần ({n} đơn, {float(rev):.2f})")
    if errs:
        raise Fail("; ".join(errs[:4]) + (" ..." if len(errs) > 4 else ""))
    return f"{len(truth)} ngày, số đơn và doanh thu (đã trừ đơn huỷ) khớp"


def check_I6():
    rel = find("fct_events_by_ts")
    dups = q1(f"select count(*) - count(distinct event_id) from {rel}")
    if dups:
        raise Fail(f"{dups} dòng trùng event_id")
    missing = [r[0] for r in q(f"select distinct event_id from raw.events except select event_id from {rel} order by 1")]
    if missing:
        raise Fail(f"thiếu {len(missing)} sự kiện, ví dụ {missing[:6]}. Lookback đủ dài chưa?")
    return f"{q1(f'select count(*) from {rel}')} sự kiện, bắt đủ sự kiện đến muộn"


def check_I7():
    need_day(4, "nguồn thêm cột channel")
    rel = find("fct_orders")
    if "channel" not in columns(rel):
        raise Fail("fct_orders chưa có cột channel (stg_orders đã có chưa? on_schema_change là gì?)")
    bad = q1(f"""select count(*) from raw.orders r join {rel} f using (order_id)
                 where r.channel is not null and f.channel is distinct from r.channel""")
    if bad:
        raise Fail(f"{bad} đơn có channel sai/null dù nguồn có giá trị")
    nulls = q1(f"select count(*) from {rel} where channel is null")
    return f"có cột channel; {nulls} đơn cũ để null (nguồn cũng null)"


def check_I8():
    rel = find("fct_events_microbatch")
    dups = q1(f"select count(*) - count(distinct event_id) from {rel}")
    if dups:
        raise Fail(f"{dups} dòng trùng event_id (dedupe trong model? stg_events có event_time chưa?)")
    have, want = q1(f"select count(*) from {rel}"), q1("select count(distinct event_id) from raw.events")
    if have != want:
        raise Fail(f"có {have}/{want} sự kiện. Đã chạy với --event-time-start/--event-time-end phủ hết dữ liệu chưa?")
    return f"{have} sự kiện, không trùng"


def check_I9():
    fe = LAB_DIR / "models" / "marts" / "fct_events.sql"
    if not fe.exists():
        raise Skip("chưa có models/marts/fct_events.sql")
    if not re.search(r"full_refresh\s*=\s*false", fe.read_text(encoding="utf-8"), re.I):
        raise Fail("fct_events chưa đặt full_refresh=false")
    audits = [p for p in code_matching(r"fct_orders", "tests") if "generic" not in str(p)]
    if not audits:
        raise Fail("chưa có singular test trong tests/ đối soát fct_orders với kết quả tính lại toàn bộ")
    return f"full_refresh=false + test đối soát {audits[0]}"


# --------------------------------------------------------------------------- Snapshot / SCD2

SNAP_HINT = "Snapshot phải chạy từ ngày 0 và sau MỖI lần `simulate.py next`. Nếu lỡ bỏ ngày: reset và làm lại."


def check_S1():
    rel = find("snap_customers")
    need_cols(rel, ["customer_id", "dbt_valid_from", "dbt_valid_to"])
    d = DAY
    expected = {1: 1, 2: 1 + (d >= 2), 3: 1 + (d >= 1) + (d >= 4), 5: 1, 8: 1 + (d >= 5)}
    if d >= 3:
        expected[11] = 1
    expect_counts(per_key_counts(rel, "customer_id"), expected, "khách", SNAP_HINT)
    hist = q(f"select city from {rel} where customer_id = 3 order by dbt_valid_from")
    return f"khách 3 có lịch sử {[h[0] for h in hist]}; khách 5 chỉ 1 phiên bản (xem S3 để hiểu vì sao)"


def check_S2():
    rel = find("snap_products")
    d = DAY
    expected = {1: 1, 2: 1 + (d >= 1) + (d >= 5), 5: 1 + (d >= 3)}
    if d >= 5:
        expected[9] = 1
    expect_counts(per_key_counts(rel, "product_id"), expected, "sản phẩm", SNAP_HINT)
    prices = [float(r[0]) for r in q(f"select list_price from {rel} where product_id = 2 order by dbt_valid_from")]
    return f"sản phẩm 2 có lịch sử giá {prices}"


def check_S3():
    rel = find("snap_customers_check")
    d = DAY
    deleted_flag = "dbt_is_deleted" in columns(rel)
    where = "coalesce(cast(dbt_is_deleted as varchar), 'False') <> 'True'" if deleted_flag else "true"
    expected = {2: 1, 3: 1 + (d >= 1) + (d >= 4), 5: 1 + (d >= 3), 8: 1 + (d >= 5)}
    expect_counts(per_key_counts(rel, "customer_id", where), expected, "khách",
                  "check_cols nên là [city, tier]. " + SNAP_HINT)
    return "check strategy bắt được khách 5 đổi hạng dù updated_at không đổi, và bỏ qua khách 2 đổi email"


def check_S4():
    need_day(3, "khách 7 bị xoá cứng ở ngày 3")
    rel = find("snap_customers")
    open_rows = q1(f"select count(*) from {rel} where customer_id = 7 and dbt_valid_to is null")
    if open_rows:
        raise Fail("khách 7 đã bị xoá ở nguồn nhưng vẫn còn dòng hiện hành trong snap_customers "
                   "(hard_deletes? lưu ý: phải bật TRƯỚC khi chạy snapshot ngày 3)")
    msg = "snap_customers đã đóng dòng của khách 7"
    try:
        rel2 = find("snap_customers_check")
        if "dbt_is_deleted" in columns(rel2):
            msg += "; snap_customers_check có cột dbt_is_deleted (new_record)"
    except Skip:
        pass
    return msg


def check_S5():
    rel = find("dim_customers")
    need_cols(rel, ["customer_sk", "customer_id", "city", "tier", "valid_from", "valid_to", "is_current"])
    if not q1(f"select count(*) from {rel} where customer_id = -1 or customer_sk = '-1'"):
        raise Fail("thiếu dòng unknown member (customer_sk = '-1')")
    cur = per_key_counts(rel, "customer_id", "is_current and customer_id <> -1")
    should = active_customers()
    bad = {c: n for c, n in cur.items() if n != 1}
    if bad:
        raise Fail(f"khách có nhiều hơn 1 dòng hiện hành: {bad}")
    if set(cur) != should:
        raise Fail(f"tập khách hiện hành {sorted(cur)} ≠ khách đang tồn tại ở nguồn {sorted(should)}")
    overlaps = q1(f"""select count(*) from {rel} a join {rel} b
                      on a.customer_id = b.customer_id and a.customer_sk < b.customer_sk
                      and a.valid_from < b.valid_to and b.valid_from < a.valid_to""")
    if overlaps:
        raise Fail(f"{overlaps} cặp khoảng hiệu lực chồng nhau")
    return f"{len(cur)} khách hiện hành, không chồng khoảng, có unknown member"


def check_S6():
    rel = find("fct_orders_pit")
    need_cols(rel, ["order_id", "customer_sk", "customer_city_at_order"])
    n_raw, n = q1("select count(*) from raw.orders"), q1(f"select count(*) from {rel}")
    if n != n_raw:
        raise Fail(f"có {n} đơn, nguồn có {n_raw} (join làm mất/nhân dòng?)")
    if q1(f"select count(*) from {rel} where customer_sk is null"):
        raise Fail("có đơn customer_sk null → phải gán unknown member '-1'")
    versions = truth_customer_versions()
    have = dict(q(f"select order_id, customer_city_at_order from {rel}"))
    errs = []
    for oid, cid, odate in q("select order_id, customer_id, order_date from raw.orders order by 1"):
        ts = datetime.combine(odate, datetime.min.time())
        city = next((v["vals"][0] for v in versions.get(cid, [])
                     if v["valid_from"] <= ts and (v["valid_to"] is None or ts < v["valid_to"])), "Unknown")
        if have.get(oid) != city:
            errs.append(f"đơn {oid} (khách {cid}, {odate}): có {have.get(oid)!r}, cần {city!r}")
    if errs:
        raise Fail("; ".join(errs[:4]) + (" ..." if len(errs) > 4 else "")
                   + ". Nhắc lại quy ước: phiên bản hợp lệ khi valid_from <= order_date (00:00) < valid_to")
    c3 = q(f"select distinct customer_city_at_order from {rel} where customer_id = 3")
    return f"thành phố tại thời điểm đặt đơn đúng cho mọi đơn; khách 3 xuất hiện ở {sorted(r[0] for r in c3)}"


def _check_scd_against_truth(rel, check_valid_from=False):
    need_cols(rel, ["customer_id", "city", "tier", "valid_from", "valid_to", "is_current"])
    truth = truth_customer_versions()
    have = per_key_counts(rel, "customer_id")
    expected = {cid: len(vs) for cid, vs in truth.items()}
    expect_counts(have, expected, "khách")
    cur = per_key_counts(rel, "customer_id", "is_current")
    should = active_customers()
    if set(cur) != should or any(n != 1 for n in cur.values()):
        raise Fail(f"dòng hiện hành sai: {cur} (khách đang tồn tại: {sorted(should)})")
    if check_valid_from:
        want = [v["valid_from"] for v in truth[3]]
        got = [r[0] for r in q(f"select valid_from from {rel} where customer_id = 3 order by valid_from")]
        if got != want:
            raise Fail(f"valid_from của khách 3 = {got}, cần đúng thời điểm thay đổi {want}")


def check_S7():
    rel = find("dim_customers_scd2_manual")
    _check_scd_against_truth(rel)
    return "số phiên bản theo (city, tier) khớp CDC, kể cả khách 5 (updated_at không đổi) và khách 7 (bị xoá)"


def check_S8():
    rel = find("dim_customers_from_cdc")
    _check_scd_against_truth(rel, check_valid_from=True)
    return "dựng lại đúng toàn bộ lịch sử, valid_from = thời điểm thay đổi thật"


CHECKS = {
    "J1": ("cents_to_dollars", check_J1),
    "J2": ("clean_string", check_J2),
    "J3": ("pivot bằng for-loop + var", check_J3),
    "J4": ("pivot động bằng run_query", check_J4),
    "J5": ("custom generic tests", check_J5),
    "J6": ("generate_schema_name", check_J6),
    "J7": ("get_incremental_filter", check_J7),
    "J8": ("audit bằng graph", check_J8),
    "J9": ("adapter.dispatch", check_J9),
    "J10": ("macro scd2_from_changelog", check_J10),
    "I1": ("append", check_I1),
    "I2": ("chống trùng sự kiện", check_I2),
    "I3": ("merge fct_orders + đơn đến muộn (I4)", check_I3),
    "I5": ("delete+insert doanh thu ngày", check_I5),
    "I6": ("lookback theo event_ts", check_I6),
    "I7": ("on_schema_change", check_I7),
    "I8": ("microbatch", check_I8),
    "I9": ("bảo vệ & đối soát", check_I9),
    "S1": ("snapshot timestamp", check_S1),
    "S2": ("snapshot check", check_S2),
    "S3": ("bẫy updated_at", check_S3),
    "S4": ("hard deletes", check_S4),
    "S5": ("dim_customers SCD2", check_S5),
    "S6": ("point-in-time join", check_S6),
    "S7": ("SCD2 tự viết bằng incremental", check_S7),
    "S8": ("SCD2 từ CDC log", check_S8),
}


def main():
    global con, DAY
    if not DB_PATH.exists():
        sys.exit("Chưa có lab.duckdb. Chạy: python scripts/simulate.py reset")
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    except duckdb.IOException as e:
        sys.exit(f"Không mở được lab.duckdb (đang bị tiến trình khác giữ?): {e}")
    DAY = q1("select current_day from raw._lab_state")
    wanted = [a.upper() for a in sys.argv[1:]] or list(CHECKS)
    print(f"Chấm bài ở NGÀY {DAY}/5\n")
    counts = defaultdict(int)
    for cid in wanted:
        if cid not in CHECKS:
            print(f"?? Không có bài {cid}")
            continue
        title, fn = CHECKS[cid]
        try:
            status, msg = PASS, fn()
        except Skip as e:
            status, msg = SKIP, str(e)
        except Fail as e:
            status, msg = FAIL, str(e)
        except duckdb.Error as e:
            status, msg = FAIL, f"lỗi SQL khi chấm: {e}"
        counts[status] += 1
        print(f"{status}  {cid:<4} {title}\n         {msg}")
    print(f"\nTổng: {counts[PASS]} pass · {counts[FAIL]} fail · {counts[SKIP]} skip")
    con.close()


if __name__ == "__main__":
    main()
