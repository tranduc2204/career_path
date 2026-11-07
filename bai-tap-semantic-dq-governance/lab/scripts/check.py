#!/usr/bin/env python3
"""Tự chấm lab GĐ3. Chạy từ thư mục lab/ SAU KHI đã `dbt build` (hoặc ./scripts/replay.sh).

  python scripts/check.py              # chấm tất cả
  python scripts/check.py M Q3 G       # chỉ chấm một phần (tiền tố hoặc mã bài)
  python scripts/check.py --summary-day N   # (run_day.sh dùng) tóm tắt tín hiệu DQ của ngày N

Kết quả:  ✅ PASS   ❌ FAIL   ⏭️  SKIP (chưa làm / chưa có dữ liệu cần thiết)

  M* (semantic layer)  : gọi `mf query` thật, so với đáp án tính bằng SQL thẳng trên các bảng mart dựng sẵn
  Q* (data quality)    : đọc kết quả TỪNG NGÀY trong .replay/day_N/ (do run_day.sh / replay.sh lưu)
  G* (governance)      : đọc target/manifest.json + dữ liệu thật trong lab.duckdb
  O* (orchestration)   : nạp Definitions của Dagster, chạy thử 1 lần materialize; O5 dùng venv Airflow nếu có
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

import duckdb

LAB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LAB_DIR / "lab.duckdb"
TARGET = LAB_DIR / "target"
REPLAY = LAB_DIR / ".replay"
BIN = Path(sys.executable).parent
D0 = date(2026, 11, 30)
START = date(2026, 10, 1)
MAX_DAY = 7

PASS, FAIL, SKIP = "✅ PASS", "❌ FAIL", "⏭️  SKIP"


class Skip(Exception):
    pass


class Fail(Exception):
    pass


# =========================================================================== tiện ích chung

@contextmanager
def db():
    """Mở lab.duckdb CHỈ ĐỌC rồi đóng ngay: mf / dbt cần mở file này ở chế độ ghi."""
    if not DB_PATH.exists():
        raise Skip("chưa có lab.duckdb (chạy simulate.py reset)")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        yield con
    finally:
        con.close()


def lab_day():
    with db() as con:
        try:
            return con.execute("select day from _lab.state").fetchone()[0]
        except duckdb.Error:
            raise Skip("lab.duckdb không có _lab.state (chạy simulate.py reset)")


def bdate(day):
    return D0 + timedelta(days=day)


def find(con, name):
    rows = con.execute("""select table_schema from information_schema.tables
                          where table_name = ? and table_schema not in ('shop','crm','erp','web','mkt','ingest','_lab')
                          order by table_schema like '%marts%' desc, table_schema""", [name]).fetchall()
    if not rows:
        raise Skip(f"chưa thấy bảng `{name}` (chưa build?)")
    return f'"{rows[0][0]}"."{name}"'


def columns(con, rel):
    schema, table = [p.strip('"') for p in rel.split(".")]
    return [r[0].lower() for r in con.execute(
        "select column_name from information_schema.columns where table_schema = ? and table_name = ?",
        [schema, table]).fetchall()]


def load_json(path: Path, why):
    if not path.exists():
        raise Skip(f"chưa có {path.relative_to(LAB_DIR)} ({why})")
    return json.loads(path.read_text(encoding="utf-8"))


def manifest():
    return load_json(TARGET / "manifest.json", "chạy dbt build / dbt parse")


def semantic_manifest():
    return load_json(TARGET / "semantic_manifest.json", "chạy dbt parse")


def close(a, b, tol=1e-6):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, float) and abs(v) < 100:
        return f"{v:.6g}"
    return f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)


def compare(label, expected: dict, actual: dict, allow_none_for=None, limit=3):
    """expected/actual: {khoá: số}. allow_none_for(khoá) → True nếu NULL cũng chấp nhận."""
    missing = [k for k in expected if k not in actual and expected[k] is not None]
    wrong = []
    for k, e in expected.items():
        if k not in actual:
            continue
        a = actual[k]
        if close(e, a):
            continue
        if allow_none_for and allow_none_for(k) and a is None:
            continue
        wrong.append(k)
    if not (missing or wrong):
        return
    parts = []
    if missing:
        parts.append(f"thiếu {len(missing)} dòng, vd {sorted(missing, key=str)[:limit]}")
    if wrong:
        ex = "; ".join(f"{k}: mong đợi {fmt(expected[k])}, có {fmt(actual.get(k))}" for k in sorted(wrong, key=str)[:limit])
        parts.append(f"sai {len(wrong)}/{len(expected)} giá trị, vd {ex}")
    raise Fail(f"{label}: " + " | ".join(parts))


# =========================================================================== MetricFlow

_mf_cache = {}


def sm_metrics():
    return {m["name"]: m for m in semantic_manifest()["metrics"]}


def need_metrics(names):
    have = sm_metrics()
    missing = [n for n in names if n not in have]
    if missing:
        raise Skip(f"chưa định nghĩa metric {missing}")


def mf_query(metrics, group_by, start=None, end=None, saved_query=None):
    """Chạy `mf query ... --csv` → list[dict]. Raise Fail kèm lỗi của MetricFlow."""
    key = (tuple(metrics), tuple(group_by), start, end, saved_query)
    if key in _mf_cache:
        return _mf_cache[key]
    mf = BIN / "mf"
    if not mf.exists():
        raise Skip("không thấy lệnh mf (cài dbt-metricflow: uv sync)")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.csv"
        cmd = [str(mf), "query"]
        if saved_query:
            cmd += ["--saved-query", saved_query]
        else:
            cmd += ["--metrics", ",".join(metrics), "--group-by", ",".join(group_by)]
        if start:
            cmd += ["--start-time", str(start)]
        if end:
            cmd += ["--end-time", str(end)]
        cmd += ["--csv", str(out)]
        env = {**os.environ, "DBT_PROFILES_DIR": str(LAB_DIR)}
        proc = subprocess.run(cmd, cwd=LAB_DIR, env=env, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 or not out.exists():
            text = (proc.stdout + proc.stderr)
            lines = [ln.strip() for ln in text.splitlines()
                     if ln.strip() and "⠋" not in ln and "⠙" not in ln and "github.com" not in ln
                     and "If you think" not in ln]
            msg = " / ".join(lines[-6:])[:600]
            hint = ""
            if re.search(r'syntax error at or near "?,', text) or "AS order" in text:
                hint = " → Gợi ý: đặt tên entity là từ khoá SQL (order, group, user...) làm MetricFlow sinh SQL lỗi."
            raise Fail(f"`mf query --metrics {','.join(metrics)} --group-by {','.join(group_by)}` lỗi: {msg}{hint}")
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    _mf_cache[key] = rows
    return rows


def num(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return s


def by_key(rows, key_col, metric):
    out = {}
    for r in rows:
        k = r[key_col]
        if key_col.startswith("metric_time"):
            k = k[:10]
        out[k] = num(r.get(metric))
    return out


# ------------------------------------------------------------------ đáp án từ mart

class Truth:
    """Đáp án chuẩn tính bằng SQL thẳng trên bảng mart (không qua semantic layer)."""

    def __init__(self):
        self.day = lab_day()
        self.end = bdate(self.day)
        with db() as con:
            fo, fi = find(con, "fct_orders"), find(con, "fct_order_items")
            fr, fs, fa = find(con, "fct_refunds"), find(con, "fct_sessions"), find(con, "fct_ad_spend")
            self.daily = {}
            days = [START + timedelta(days=i) for i in range((self.end - START).days + 1)]

            def series(sql):
                return {str(d): v for d, v in con.execute(sql).fetchall()}

            rev = series(f"""select i.order_date, sum(i.line_amount) from {fi} i join {fo} o using (order_id)
                             where not o.is_cancelled group by 1""")
            rev_all = series(f"select order_date, sum(line_amount) from {fi} group by 1")
            cogs = series(f"""select i.order_date, sum(i.line_cost) from {fi} i join {fo} o using (order_id)
                              where not o.is_cancelled group by 1""")
            orders = series(f"select order_date, count(*) from {fo} where not is_cancelled group by 1")
            orders_all = series(f"select order_date, count(*) from {fo} group by 1")
            buyers = series(f"select order_date, count(distinct customer_id) from {fo} where not is_cancelled group by 1")
            refunds = series(f"select refund_date, sum(refund_amount) from {fr} group by 1")
            sessions = series(f"select session_date, count(*) from {fs} group by 1")
            spend = series(f"select spend_date, sum(spend) from {fa} group by 1")
            b7 = series(f"""select d.d, count(distinct o.customer_id)
                            from (select unnest(generate_series(date '{START}', date '{self.end}', interval 1 day))::date d) d
                            join {fo} o on o.order_date between d.d - 6 and d.d and not o.is_cancelled
                            group by 1""")
            b7_sum = {}
            for d in days:
                b7_sum[str(d)] = sum(buyers.get(str(d - timedelta(days=k)), 0) for k in range(7))

            def f(x):
                return None if x is None else float(x)

            for d in days:
                k = str(d)
                r, c, o = f(rev.get(k)), f(cogs.get(k)), f(orders.get(k))
                rf, s, sp = f(refunds.get(k)), f(sessions.get(k)), f(spend.get(k))
                lag = f(rev.get(str(d - timedelta(days=7))))
                mstart = d.replace(day=1)
                mtd = sum(f(rev.get(str(mstart + timedelta(days=i)))) or 0 for i in range((d - mstart).days + 1))
                self.daily[k] = {
                    "revenue": r, "orders": o, "buyers": f(buyers.get(k)), "refunds": rf if rf else 0.0,
                    "sessions": s, "ad_spend": sp,
                    "aov": r / o if r is not None and o else None,
                    "refund_rate": (rf or 0.0) / r if r else None,
                    "conversion_rate": o / s if o is not None and s else None,
                    "roas": r / sp if r is not None and sp else None,
                    "gross_profit": r - c if r is not None and c is not None else None,
                    "net_revenue": r - (rf or 0.0) if r is not None else None,
                    "revenue_wow": (r - lag) / lag if r is not None and lag else None,
                    "revenue_mtd": float(mtd),
                    "buyers_7d": f(b7.get(k)),
                    # để đoán lỗi
                    "_revenue_all": f(rev_all.get(k)), "_orders_all": f(orders_all.get(k)),
                    "_buyers_7d_sum": float(b7_sum[k]),
                }
            self.zero_refund_days = {str(d) for d in days if not refunds.get(str(d))}

            # theo tháng (chỉ các tháng đủ ngày: 10 và 11)
            self.monthly = {}
            for m, (a, b) in {"2026-10-01": ("2026-10-01", "2026-10-31"), "2026-11-01": ("2026-11-01", "2026-11-30")}.items():
                rv = con.execute(f"""select sum(i.line_amount) from {fi} i join {fo} o using (order_id)
                                     where not o.is_cancelled and i.order_date between '{a}' and '{b}'""").fetchone()[0]
                od, by = con.execute(f"""select count(*), count(distinct customer_id) from {fo}
                                         where not is_cancelled and order_date between '{a}' and '{b}'""").fetchone()
                first = self.daily.get(a, {}).get("revenue_mtd")
                aovs = [self.daily[k]["aov"] for k in self.daily if a <= k <= b and self.daily[k]["aov"] is not None]
                self.monthly[m] = {"revenue": float(rv), "orders": float(od), "buyers": float(by),
                                   "aov": float(rv) / od, "revenue_mtd": float(rv),
                                   "_mtd_first": first, "_aov_avg": sum(aovs) / len(aovs) if aovs else None}

            # theo chiều (toàn bộ khoảng START..end)
            rng = f"between '{START}' and '{self.end}'"
            self.by_channel = {ch: {"revenue": float(rv), "aov": float(rv) / n} for ch, rv, n in con.execute(f"""
                select o.channel, sum(i.line_amount), count(distinct o.order_id)
                from {fi} i join {fo} o using (order_id)
                where not o.is_cancelled and i.order_date {rng} group by 1""").fetchall()}
            self.by_category = {c: float(v) for c, v in con.execute(f"""
                select p.category, sum(i.line_amount)
                from {fi} i join {fo} o using (order_id) join {find(con, 'dim_products')} p using (product_id)
                where not o.is_cancelled and i.order_date {rng} group by 1""").fetchall()}
            self.buyers_by_city = {c: float(v) for c, v in con.execute(f"""
                select c.city, count(distinct o.customer_id)
                from {fo} o join crm.customers c using (customer_id)
                where not o.is_cancelled and o.order_date {rng} group by 1""").fetchall()}
            self.sessions_by_device = {d: float(v) for d, v in con.execute(f"""
                select device, count(*) from {fs} where session_date {rng} group by 1""").fetchall()}
            group = {"google": "paid", "facebook": "paid", "tiktok": "paid", "organic": "organic", "email": "owned"}
            rg, sg = {}, {}
            for src, v in con.execute(f"""select i.utm_source, sum(i.line_amount) from {fi} i join {fo} o using (order_id)
                                          where not o.is_cancelled and i.order_date {rng} group by 1""").fetchall():
                rg[group[src]] = rg.get(group[src], 0.0) + float(v)
            for src, v in con.execute(f"select utm_source, sum(spend) from {fa} where spend_date {rng} group by 1").fetchall():
                sg[group[src]] = sg.get(group[src], 0.0) + float(v)
            self.by_channel_group = {g: {"revenue": rg.get(g), "ad_spend": sg.get(g),
                                         "roas": rg[g] / sg[g] if sg.get(g) else None} for g in rg}


_truth = None


def truth():
    global _truth
    if _truth is None:
        _truth = Truth()
    return _truth


DAY_METRICS = {
    "M3": ["revenue", "orders", "buyers", "refunds", "sessions", "ad_spend"],
    "M4": ["aov", "refund_rate", "conversion_rate", "roas"],
    "M5": ["gross_profit", "net_revenue", "revenue_wow"],
    "M6": ["revenue_mtd", "buyers_7d"],
}


def day_rows(metrics):
    """Ưu tiên 1 truy vấn gộp mọi metric đã có (nhanh); nếu lỗi thì truy vấn riêng nhóm cần chấm."""
    t = truth()
    have = sm_metrics()
    all_m = [m for ms in DAY_METRICS.values() for m in ms if m in have]
    try:
        return mf_query(all_m, ["metric_time__day"], START, t.end)
    except Fail:
        return mf_query(metrics, ["metric_time__day"], START, t.end)


def check_day_metrics(metrics, hints=None, skip_days=None, allow_none=None):
    need_metrics(metrics)
    t = truth()
    rows = day_rows(metrics)
    for m in metrics:
        exp = {k: v[m] for k, v in t.daily.items() if not (skip_days and skip_days(m, k))}
        act = by_key(rows, "metric_time__day", m)
        try:
            compare(f"{m} theo ngày", exp, act, allow_none_for=(lambda k, m=m: allow_none(m, k)) if allow_none else None)
        except Fail as e:
            extra = hints(m, t, act) if hints else ""
            raise Fail(str(e) + (f" → Gợi ý: {extra}" if extra else ""))


# =========================================================================== M — SEMANTIC LAYER (tuần 8)

def check_M1():
    """Time spine"""
    sm = semantic_manifest()
    spines = (sm.get("project_configuration") or {}).get("time_spines") or []
    if not spines:
        raise Skip("chưa khai báo time spine (models: - name: ... time_spine: standard_granularity_column: ...)")
    sp = spines[0]
    rel = sp["node_relation"]
    col = sp["primary_column"]["name"]
    if (sp["primary_column"].get("time_granularity") or "").lower() != "day":
        raise Fail(f"time spine {rel['alias']} phải ở grain day (đang là {sp['primary_column'].get('time_granularity')})")
    with db() as con:
        r = find(con, rel["alias"])
        lo, hi, n = con.execute(f"select min({col}), max({col}), count(*) - count(distinct {col}) from {r}").fetchone()
    if lo is None or lo > date(2026, 1, 1) or hi < date(2027, 12, 31):
        raise Fail(f"time spine chỉ phủ {lo} → {hi}; cần phủ ít nhất 2026-01-01 → 2027-12-31")
    if n:
        raise Fail(f"time spine có {n} ngày bị trùng")


REQUIRED_ENTITIES = {  # entity: semantic model phải có nó là primary
    "sales_order": "fct_orders", "order_item": "fct_order_items", "refund": "fct_refunds",
    "product": "dim_products", "customer": "dim_customers", "session": "fct_sessions",
    "marketing_channel": "dim_marketing_channels",
}
REQUIRED_DIMS = ["sales_order__channel", "sales_order__is_cancelled", "product__category",
                 "customer__city", "session__device", "marketing_channel__channel_group"]


def check_M2():
    """Semantic model, entity, dimension"""
    sm = semantic_manifest()
    models = sm.get("semantic_models") or []
    if not models:
        raise Skip("chưa có semantic model nào")
    primary, dims, fkeys = {}, set(), {}
    for s in models:
        for e in s.get("entities", []):
            if e["type"] == "primary":
                primary.setdefault(e["name"], []).append(s["node_relation"]["alias"])
            else:
                fkeys.setdefault(e["name"], []).append(s["name"])
            if e["name"] in ("order", "group", "user", "select", "from"):
                raise Fail(f"entity `{e['name']}` trùng từ khoá SQL → MetricFlow sinh `AS {e['name']}` và lỗi cú pháp. "
                           f"Đổi tên (vd sales_order)")
        pk = next((e["name"] for e in s.get("entities", []) if e["type"] == "primary"), None)
        for d in s.get("dimensions", []):
            if pk:
                dims.add(f"{pk}__{d['name']}")
    for ent, model in REQUIRED_ENTITIES.items():
        if ent not in primary:
            raise Fail(f"thiếu entity primary `{ent}` (trên {model})")
        if len(primary[ent]) > 1:
            raise Fail(f"entity `{ent}` là primary ở {len(primary[ent])} semantic model {primary[ent]}: chỉ được 1")
        if not primary[ent][0].startswith(model):
            raise Fail(f"entity primary `{ent}` phải đặt trên {model} (đang ở {primary[ent][0]})")
    for ent in ("sales_order", "customer", "marketing_channel", "product"):
        if ent not in fkeys:
            raise Fail(f"chưa có semantic model nào khai báo `{ent}` là foreign entity → không join được")
    missing = [d for d in REQUIRED_DIMS if d not in dims]
    if missing:
        raise Fail(f"thiếu dimension {missing}")


def hints_simple(m, t, act):
    sample = [k for k in t.daily if act.get(k) is not None][:20]
    if m == "revenue" and sample and all(close(act[k], t.daily[k]["_revenue_all"]) for k in sample):
        return "revenue đang tính cả đơn huỷ: lọc {{ Dimension('sales_order__is_cancelled') }} = false"
    if m == "orders" and sample and all(close(act[k], t.daily[k]["_orders_all"]) for k in sample):
        return "orders đang đếm cả đơn huỷ"
    if m == "buyers" and sample and all(close(act[k], t.daily[k]["orders"]) for k in sample):
        return "buyers phải là count_distinct customer_id, không phải count"
    if m == "refunds":
        return "refunds tính theo NGÀY HOÀN TIỀN (agg_time_dimension: refund_date)"
    return ""


def check_M3():
    """Simple metrics"""
    check_day_metrics(DAY_METRICS["M3"], hints=hints_simple,
                      allow_none=lambda m, k: m == "refunds" and k in truth().zero_refund_days)


def check_M4():
    """Ratio metrics"""
    ms = DAY_METRICS["M4"]
    for m in ms:
        if m in sm_metrics() and sm_metrics()[m]["type"] != "ratio":
            raise Fail(f"`{m}` phải là metric type ratio (đang là {sm_metrics()[m]['type']})")
    check_day_metrics(ms, allow_none=lambda m, k: m == "refund_rate" and k in truth().zero_refund_days)
    t = truth()
    rows = mf_query(["aov"], ["metric_time__month"], START, date(2026, 11, 30))
    act = by_key(rows, "metric_time__month", "aov")
    exp = {k: v["aov"] for k, v in t.monthly.items()}
    try:
        compare("aov theo tháng", exp, act)
    except Fail as e:
        k = "2026-11-01"
        if close(act.get(k), t.monthly[k]["_aov_avg"]):
            raise Fail(f"{e} → Gợi ý: đang lấy TRUNG BÌNH của AOV theo ngày; AOV tháng = tổng revenue / tổng orders")
        raise


def hints_derived(m, t, act):
    if m == "net_revenue":
        z = [k for k in t.zero_refund_days if k in act]
        if z and all(act[k] is None for k in z):
            return ("ngày không có hoàn tiền ra NULL: refunds không có dòng → revenue - NULL = NULL. "
                    "Ở dbt-core 1.12.6 YAML kiểu mới, fill_nulls_with bị bỏ qua → dùng coalesce(refunds, 0) trong expr")
    if m == "revenue_wow":
        return "dùng input metric revenue với offset_window: 7 days (alias) rồi (revenue - lag) / lag"
    return ""


def check_M5():
    """Derived metrics"""
    ms = DAY_METRICS["M5"]
    for m in ms:
        if m in sm_metrics() and sm_metrics()[m]["type"] != "derived":
            raise Fail(f"`{m}` phải là metric type derived")
    check_day_metrics(ms, hints=hints_derived,
                      skip_days=lambda m, k: m == "revenue_wow" and k < str(START + timedelta(days=7)))


def check_M6():
    """Cumulative metrics"""
    ms = DAY_METRICS["M6"]
    for m in ms:
        if m in sm_metrics() and sm_metrics()[m]["type"] != "cumulative":
            raise Fail(f"`{m}` phải là metric type cumulative")

    def hints(m, t, act):
        sample = [k for k in t.daily if act.get(k) is not None][:20]
        if m == "buyers_7d" and sample and all(close(act[k], t.daily[k]["_buyers_7d_sum"]) for k in sample):
            return "đang CỘNG buyers của 7 ngày; cumulative trên metric count_distinct phải đếm distinct trong cửa sổ"
        if m == "buyers_7d":
            return "window: 7 days trên metric buyers (count_distinct)"
        return "grain_to_date: month trên metric revenue"

    check_day_metrics(ms, hints=hints)
    t = truth()
    rows = mf_query(["revenue_mtd"], ["metric_time__month"], START, date(2026, 11, 30))
    act = by_key(rows, "metric_time__month", "revenue_mtd")
    exp = {k: v["revenue_mtd"] for k, v in t.monthly.items()}
    try:
        compare("revenue_mtd theo tháng", exp, act)
    except Fail as e:
        k = "2026-11-01"
        if close(act.get(k), t.monthly[k]["_mtd_first"]):
            raise Fail(f"{e} → Gợi ý: khi gom lên tháng, cumulative metric lấy giá trị NGÀY ĐẦU (period_agg mặc định "
                       f"= first). MTD của cả tháng phải là ngày cuối: period_agg: last")
        raise


def check_M7():
    """Truy vấn theo dimension (join qua entity)"""
    need_metrics(["revenue", "aov", "buyers", "sessions", "ad_spend", "roas"])
    t = truth()
    rows = mf_query(["revenue", "aov"], ["sales_order__channel"], START, t.end)
    for m in ("revenue", "aov"):
        compare(f"{m} theo sales_order__channel", {k: v[m] for k, v in t.by_channel.items()},
                by_key(rows, "sales_order__channel", m))
    rows = mf_query(["revenue"], ["product__category"], START, t.end)
    compare("revenue theo product__category", t.by_category, by_key(rows, "product__category", "revenue"))
    rows = mf_query(["buyers"], ["customer__city"], START, t.end)
    compare("buyers theo customer__city", t.buyers_by_city, by_key(rows, "customer__city", "buyers"))
    rows = mf_query(["sessions"], ["session__device"], START, t.end)
    compare("sessions theo session__device", t.sessions_by_device, by_key(rows, "session__device", "sessions"))
    rows = mf_query(["revenue", "ad_spend", "roas"], ["marketing_channel__channel_group"], START, t.end)
    for m in ("revenue", "ad_spend", "roas"):
        compare(f"{m} theo marketing_channel__channel_group",
                {k: v[m] for k, v in t.by_channel_group.items()},
                by_key(rows, "marketing_channel__channel_group", m),
                allow_none_for=lambda k: k in ("organic", "owned"))


def check_M8():
    """Saved query daily_kpis"""
    sm = semantic_manifest()
    sq = {s["name"]: s for s in sm.get("saved_queries") or []}
    if "daily_kpis" not in sq:
        raise Skip("chưa có saved query `daily_kpis`")
    params = sq["daily_kpis"]["query_params"]
    metrics = set(params.get("metrics") or [])
    need = {"revenue", "orders", "aov", "net_revenue"}
    if not need <= metrics:
        raise Fail(f"daily_kpis thiếu metric {sorted(need - metrics)}")
    gb = " ".join(params.get("group_by") or [])
    if "metric_time" not in gb or "day" not in gb:
        raise Fail(f"daily_kpis phải group theo TimeDimension('metric_time', 'day') (đang: {params.get('group_by')})")
    t = truth()
    rows = mf_query([], [], START, t.end, saved_query="daily_kpis")
    col = next((c for c in (rows[0].keys() if rows else []) if c.startswith("metric_time")), None)
    if not rows or not col:
        raise Fail("mf query --saved-query daily_kpis không trả dòng nào / không có cột metric_time")
    compare("daily_kpis.revenue", {k: v["revenue"] for k, v in t.daily.items()}, by_key(rows, col, "revenue"))


# =========================================================================== Q — DATA QUALITY (tuần 9)

_days = {}


def replay_day(d):
    if d in _days:
        return _days[d]
    base = REPLAY / f"day_{d}"
    if not (base / "run_results.json").exists():
        raise Skip(f"chưa có kết quả ngày {d} trong .replay/ → chạy ./scripts/replay.sh (hoặc run_day.sh mỗi ngày)")
    rr = json.loads((base / "run_results.json").read_text(encoding="utf-8"))
    man = json.loads((base / "manifest.json").read_text(encoding="utf-8")) if (base / "manifest.json").exists() else {}
    src = json.loads((base / "sources.json").read_text(encoding="utf-8")) if (base / "sources.json").exists() else {}
    nodes = {**man.get("nodes", {}), **man.get("sources", {})}
    tests, models = [], {}
    for r in rr.get("results", []):
        uid = r["unique_id"]
        n = nodes.get(uid, {})
        if uid.startswith("test."):
            meta = n.get("test_metadata") or {}
            kw = meta.get("kwargs") or {}
            attached = n.get("attached_node") or next(iter((n.get("depends_on") or {}).get("nodes", [])), "")
            if attached and attached.startswith("source.") is False and not attached:
                attached = ""
            tests.append({
                "uid": uid, "status": r["status"], "name": (meta.get("name") or uid.split(".")[2]),
                "namespace": meta.get("namespace"),
                "column": (n.get("column_name") or kw.get("column_name") or "").lower(),
                "attached": attached, "deps": (n.get("depends_on") or {}).get("nodes", []),
                "severity": ((n.get("config") or {}).get("severity") or "").lower(),
            })
        elif uid.startswith("model."):
            models[uid.split(".")[-1]] = r["status"]
    fresh = {r["unique_id"].split(".", 2)[2]: r["status"] for r in src.get("results", [])}
    _days[d] = {"tests": tests, "models": models, "fresh": fresh}
    return _days[d]


def node_name(uid):
    p = uid.split(".")
    return ".".join(p[2:]) if uid.startswith("source.") else p[-1]


def tests_on(d, nodes, column=None):
    """Test gắn vào một trong các node (tên model / 'shop.orders' cho source), lọc theo cột nếu có."""
    out = []
    for t in replay_day(d)["tests"]:
        targets = {node_name(u) for u in ([t["attached"]] if t["attached"] else t["deps"]) if u}
        if not targets & set(nodes):
            continue
        if column and t["column"] != column and column not in t["uid"].lower():
            continue
        out.append(t)
    return out


BAD = ("fail", "warn", "error")


def detector(nodes, column, bad_days, good_days, label, name_filter=None):
    """Có ít nhất 1 test (cùng unique_id) bật ở MỌI ngày bad_days và im lặng ở MỌI ngày good_days."""
    for d in bad_days + good_days:
        replay_day(d)
    candidates = {t["uid"]: t for t in tests_on(bad_days[0], nodes, column)}
    if name_filter:
        candidates = {u: t for u, t in candidates.items() if name_filter(t)}
    if not candidates:
        raise Fail(f"{label}: chưa có test nào gắn vào {nodes}" + (f" (cột {column})" if column else ""))
    st = {u: {d: next((x["status"] for x in replay_day(d)["tests"] if x["uid"] == u), None)
              for d in bad_days + good_days} for u in candidates}
    good = [u for u, s in st.items() if all(s[d] in BAD for d in bad_days) and all(s[d] == "pass" for d in good_days)]
    if good:
        return [candidates[u] for u in good]
    detail = "; ".join(f"{candidates[u]['name']}: " + ", ".join(f"ngày {d}={s[d]}" for d in bad_days + good_days)
                       for u, s in list(st.items())[:3])
    raise Fail(f"{label}: không test nào bật đúng ngày {bad_days} và im lặng ngày {good_days}. {detail}")


FRESH_SOURCES = ["shop.orders", "shop.order_items", "shop.refunds", "crm.customers", "erp.products",
                 "web.sessions", "mkt.ad_spend"]
AD_SPEND_EXPECTED = {0: "pass", 1: "pass", 2: "pass", 3: "pass", 4: "warn", 5: "error", 6: "error", 7: "pass"}


def check_Q1():
    """Freshness theo SLA, không báo động giả"""
    for d in range(MAX_DAY + 1):
        fr = replay_day(d)["fresh"]
        missing = [s for s in FRESH_SOURCES if s not in fr]
        if missing:
            raise Fail(f"ngày {d}: chưa cấu hình freshness cho {missing} (mọi nguồn nghiệp vụ đều phải được theo dõi)")
        got = fr["mkt.ad_spend"]
        if got != AD_SPEND_EXPECTED[d]:
            raise Fail(f"mkt.ad_spend ngày {d}: mong đợi {AD_SPEND_EXPECTED[d]}, có {got} "
                       f"(SLA: warn sau 12 giờ, error sau 36 giờ, đo theo _loaded_at)")
        for s in FRESH_SOURCES:
            if s == "mkt.ad_spend" or fr[s] == "pass":
                continue
            hint = ""
            if s in ("erp.products", "shop.refunds"):
                hint = (" → bảng này ít dòng mới nên _loaded_at đứng yên dù connector vẫn chạy. "
                        "Đo 'connector còn sống không' bằng loaded_at_query trên ingest.sync_log (status = 'success')")
            raise Fail(f"{s} ngày {d}: freshness = {fr[s]} (báo động giả){hint}")


def check_Q2():
    """Volume anomaly: connector nạp thiếu đơn"""
    try:
        hits = detector(["shop.orders", "stg_shop__orders", "fct_orders"], None, [2], [0, 1, 3], "Đơn ngày 02/12 về thiếu",
                        name_filter=lambda t: "volume" in t["name"] or "row_count" in t["name"])
    except Fail as e:
        if "ngày 2=pass" in str(e):
            raise Fail(f"{e} → Gợi ý: test có nhưng không bật. Xem test_results_description trong bảng "
                       f"elementary_test_results: nếu 'average' thấp bất thường thì cửa sổ huấn luyện đang chứa các "
                       f"ngày chưa có dữ liệu (vd do seasonality: day_of_week). Kiểm tra training_period/seasonality/"
                       f"timestamp_column")
        raise
    if not any(t["namespace"] == "elementary" or "elementary" in t["uid"] for t in hits):
        raise Fail("phải dùng test volume_anomalies của Elementary")


def check_Q3():
    """Null spike trên cột được phép NULL"""
    nodes = ["web.sessions", "stg_web__sessions", "fct_sessions"]
    for d in range(MAX_DAY + 1):
        for t in tests_on(d, nodes, "customer_id"):
            if t["name"] == "not_null":
                raise Fail("customer_id NULL là bình thường (khách chưa đăng nhập): bỏ test not_null, dùng anomaly null_percent")
    detector(nodes, "customer_id", [3], [0, 1, 2, 7], "Lỗi tracking ngày 03/12")


def check_Q4():
    """Giá trị mới 'bnpl': cảnh báo, không chặn"""
    nodes = ["shop.orders", "stg_shop__orders", "fct_orders"]
    hits = detector(nodes, "payment_method", [4, 5, 6, 7], [0, 1, 2, 3], "Phương thức thanh toán bnpl")
    for t in hits:
        for d in (4, 5, 6, 7):
            s = next(x["status"] for x in replay_day(d)["tests"] if x["uid"] == t["uid"])
            if s != "warn":
                raise Fail(f"{t['name']} ngày {d} = {s}: đây là thay đổi nghiệp vụ, không phải lỗi → severity: warn")


def check_Q5():
    """Đổi tên cột ở nguồn: phát hiện + pipeline vẫn chạy"""
    detector(["crm.customers", "stg_crm__customers"], None, [5], [3, 4], "CRM đổi tên cột phone",
             name_filter=lambda t: "schema_change" in t["name"])
    for d in range(MAX_DAY + 1):
        st = replay_day(d)["models"]
        for m in ("stg_crm__customers",):
            if st.get(m) not in (None, "success"):
                raise Fail(f"ngày {d}: {m} = {st.get(m)} → staging phải chạy được với cả schema cũ (phone) và mới "
                           f"(phone_number). Gợi ý: adapter.get_columns_in_relation(source(...))")
        if "stg_crm__customers" not in st:
            raise Fail(f"ngày {d}: không thấy stg_crm__customers trong run_results")
    with db() as con:
        rel = find(con, "stg_crm__customers")
        n, nn = con.execute(f"select count(*), count(phone) from {rel}").fetchone()
    if n == 0 or nn / n < 0.95:
        raise Fail(f"stg_crm__customers.phone chỉ có {nn}/{n} giá trị: cột mới phone_number chưa được map vào phone")


def check_Q6():
    """Đơn giá sai đơn vị: chặn trước khi lên dashboard"""
    nodes = ["shop.order_items", "stg_shop__order_items", "fct_order_items"]
    hits = detector(nodes, "unit_price", [6], [0, 1, 2, 3, 4, 5, 7], "Đơn giá app ngày 06/12")
    s6 = {t["uid"]: next(x["status"] for x in replay_day(6)["tests"] if x["uid"] == t["uid"]) for t in hits}
    if not any(v in ("fail", "error") for v in s6.values()):
        raise Fail("test bắt được nhưng chỉ warn: lỗi này làm sai doanh thu → severity: error để chặn downstream")
    if replay_day(6)["models"].get("fct_order_items") == "success":
        raise Fail("ngày 06/12 fct_order_items vẫn được build với giá sai → đặt test ở tầng staging/source "
                   "để `dbt build` skip fct_order_items (dashboard giữ số hôm qua thay vì số sai)")


def check_Q7():
    """Không báo động giả ở ngày sạch, không model nào lỗi"""
    for d in (0, 1, 7):
        x = replay_day(d)
        bad = [f"{t['name']} ({node_name(t['attached'] or (t['deps'] or [''])[0])})={t['status']}"
               for t in x["tests"] if t["status"] in ("fail", "error")]
        if bad:
            raise Fail(f"ngày {d} là ngày SẠCH nhưng có test đỏ: {bad[:4]}")
        fr = [f"{s}={v}" for s, v in x["fresh"].items() if v != "pass"]
        if fr:
            raise Fail(f"ngày {d} là ngày SẠCH nhưng freshness báo: {fr}")
    for d in range(MAX_DAY + 1):
        err = [m for m, s in replay_day(d)["models"].items() if s == "error"]
        if err:
            raise Fail(f"ngày {d}: model lỗi {err}")


# =========================================================================== G — GOVERNANCE (tuần 10)

def lab_models(man):
    return {uid: n for uid, n in man["nodes"].items()
            if n["resource_type"] == "model" and n["package_name"] == "lab"}


def by_folder(man, folder):
    return {uid: n for uid, n in lab_models(man).items() if n["original_file_path"].startswith(f"models/{folder}/")}


PUBLIC_MARTS = ["fct_orders", "fct_order_items", "fct_refunds", "dim_products", "dim_customers",
                "fct_sessions", "fct_ad_spend", "dim_marketing_channels"]


def check_G1():
    """Groups và chủ sở hữu"""
    man = manifest()
    groups = man.get("groups") or {}
    if not groups:
        raise Skip("chưa khai báo groups")
    names = {g["name"] for g in groups.values()}
    if not {"commerce", "customer", "growth"} <= names:
        raise Fail(f"cần 3 group commerce, customer, growth (đang có {sorted(names)})")
    for g in groups.values():
        if not (g.get("owner") or {}).get("email"):
            raise Fail(f"group {g['name']} chưa có owner.email")
    expect = {"staging/shop": "commerce", "staging/erp": "commerce", "staging/crm": "customer",
              "staging/web": "growth", "staging/mkt": "growth", "marts/commerce": "commerce",
              "marts/customer": "customer", "marts/growth": "growth", "growth": "growth"}
    for uid, n in lab_models(man).items():
        for folder, g in expect.items():
            if n["original_file_path"].startswith(f"models/{folder}/"):
                if n.get("group") != g:
                    raise Fail(f"{n['name']} (models/{folder}) phải thuộc group {g}, đang là {n.get('group')}")


def check_G2():
    """Access: private / protected / public"""
    man = manifest()
    if not man.get("groups"):
        raise Skip("làm G1 trước")
    for uid, n in by_folder(man, "staging").items():
        if n.get("access") != "private":
            raise Fail(f"{n['name']}: staging phải private (đang {n.get('access')})")
    for uid, n in by_folder(man, "marts").items():
        if n.get("access") != "public":
            raise Fail(f"{n['name']}: mart phải public (đang {n.get('access')})")
    g = next((n for n in lab_models(man).values() if n["name"] == "growth_campaign_daily"), None)
    if not g:
        raise Fail("không thấy growth_campaign_daily (đừng xoá model này: sửa nó)")
    nodes = man["nodes"]
    for dep in g["depends_on"]["nodes"]:
        d = nodes.get(dep, {})
        if d.get("group") != g.get("group") and d.get("access") != "public":
            raise Fail(f"growth_campaign_daily ref {d.get('name')} (group {d.get('group')}, {d.get('access')})")
        if d.get("name", "").startswith("stg_shop__"):
            raise Fail("growth_campaign_daily vẫn ref staging của Commerce → đổi sang fct_orders")


def check_G3():
    """Contract trên mọi model public"""
    man = manifest()
    pub = [n for n in lab_models(man).values() if n.get("access") == "public"]
    if not pub:
        raise Skip("chưa có model public (làm G2)")
    with db() as con:
        for n in pub:
            c = (n.get("config") or {}).get("contract") or {}
            if not c.get("enforced"):
                raise Fail(f"{n['name']}: contract chưa enforced")
            cols = n.get("columns") or {}
            nodt = [k for k, v in cols.items() if not v.get("data_type")]
            if nodt:
                raise Fail(f"{n['name']}: cột thiếu data_type {nodt}")
            rel = find(con, n.get("alias") or n["name"])
            if set(columns(con, rel)) != {k.lower() for k in cols}:
                raise Fail(f"{n['name']}: bảng trong DB lệch contract (build lại?)")


def check_G4():
    """Model versions: dim_customers v1 → v2"""
    man = manifest()
    vs = [n for n in lab_models(man).values() if n["name"] == "dim_customers" and n.get("version") is not None]
    if not vs:
        raise Skip("dim_customers chưa có versions")
    by_v = {str(n["version"]): n for n in vs}
    if set(by_v) != {"1", "2"}:
        raise Fail(f"cần đúng 2 version 1 và 2 (đang {sorted(by_v)})")
    if str(by_v["2"].get("latest_version")) != "2":
        raise Fail("latest_version phải là 2")
    dd = by_v["1"].get("deprecation_date")
    if not dd:
        raise Fail("v1 chưa có deprecation_date")
    if str(dd)[:10] != "2027-01-31":
        raise Fail(f"v1 deprecation_date phải là 2027-01-31 (đang {dd})")
    with db() as con:
        c1 = set(columns(con, find(con, "dim_customers_v1")))
        c2 = set(columns(con, find(con, "dim_customers_v2")))
    need1 = {"customer_id", "full_name", "email", "phone", "city", "segment", "birth_date", "signup_date"}
    if need1 - c1:
        raise Fail(f"dim_customers_v1 phải giữ nguyên giao diện cũ, thiếu {sorted(need1 - c1)}")
    if {"phone", "birth_date", "segment"} & c2:
        raise Fail(f"dim_customers_v2 không được có {sorted({'phone', 'birth_date', 'segment'} & c2)}")
    if not {"age_band", "customer_segment"} <= c2:
        raise Fail(f"dim_customers_v2 thiếu {sorted({'age_band', 'customer_segment'} - c2)}")


PII = {"full_name": "name", "email": "email", "phone": "phone", "birth_date": "date"}


def check_G5():
    """PII: gắn nhãn + che dữ liệu"""
    man = manifest()
    if "macro.lab.mask_pii" not in man.get("macros", {}):
        raise Skip("chưa có macro mask_pii")
    vs = {str(n.get("version")): n for n in lab_models(man).values() if n["name"] == "dim_customers"}
    for v, n in vs.items():
        cols = n.get("columns") or {}
        for c in PII:
            if c not in cols:
                continue
            meta = {**(cols[c].get("meta") or {}), **((cols[c].get("config") or {}).get("meta") or {})}
            if meta.get("pii") is not True:
                raise Fail(f"dim_customers v{v}.{c}: chưa gắn meta pii: true")
    with db() as con:
        for rel_name in ("dim_customers_v1", "dim_customers_v2"):
            try:
                rel = find(con, rel_name)
            except Skip:
                continue
            cols = columns(con, rel)
            rows = con.execute(f"select {', '.join(c for c in ('full_name', 'email', 'phone') if c in cols)} from {rel}").fetchall()
            for r in rows[:500]:
                rec = dict(zip([c for c in ("full_name", "email", "phone") if c in cols], r))
                if "email" in rec and rec["email"] and not re.fullmatch(r".\*\*\*@[^@]+", rec["email"]):
                    raise Fail(f"{rel_name}.email chưa che đúng mẫu x***@domain: {rec['email']!r}")
                if "phone" in rec and rec["phone"] and not re.fullmatch(r"\*+\d{3}", rec["phone"]):
                    raise Fail(f"{rel_name}.phone chưa che đúng mẫu *******123: {rec['phone']!r}")
                if "full_name" in rec and rec["full_name"] and not rec["full_name"].endswith(" ***"):
                    raise Fail(f"{rel_name}.full_name chưa che (giữ họ + ' ***'): {rec['full_name']!r}")
            if "birth_date" in cols:
                bad = con.execute(f"select count(*) from {rel} where birth_date is not null "
                                  f"and (month(birth_date) <> 1 or day(birth_date) <> 1)").fetchone()[0]
                if bad:
                    raise Fail(f"{rel_name}.birth_date chưa che: {bad} dòng không phải ngày 01/01")


def check_G6():
    """Exposures"""
    man = manifest()
    exps = list((man.get("exposures") or {}).values())
    if len(exps) < 2:
        raise Skip("cần ít nhất 2 exposure")
    nodes = man["nodes"]
    for e in exps:
        if not (e.get("owner") or {}).get("email"):
            raise Fail(f"exposure {e['name']} chưa có owner.email")
        if not e.get("maturity"):
            raise Fail(f"exposure {e['name']} chưa có maturity")
        deps = (e.get("depends_on") or {}).get("nodes") or []
        if not deps:
            raise Fail(f"exposure {e['name']} chưa có depends_on")
        for d in deps:
            n = nodes.get(d)
            if n and n["resource_type"] == "model" and n.get("access") != "public":
                raise Fail(f"exposure {e['name']} phụ thuộc {n['name']} ({n.get('access')}): chỉ dùng model public")
    if not any(any(d.startswith("metric.") for d in (e.get("depends_on") or {}).get("nodes") or []) for e in exps):
        raise Fail("ít nhất 1 exposure nên phụ thuộc metric (metric('revenue')...) để thấy lineage tới semantic layer")


# =========================================================================== O — ORCHESTRATION (tuần 10)

DAGSTER_PROBE = r"""
import json, sys
sys.path.insert(0, '.')
from orchestration.dagster_maystore.definitions import defs
ag = defs.resolve_asset_graph()
out = {"assets": {}, "checks": [], "schedules": {}}
for k in ag.get_all_asset_keys():
    a = ag.get(k)
    out["assets"]["/".join(k.path)] = {"group": a.group_name, "materializable": a.is_materializable}
out["checks"] = ["/".join(c.asset_key.path) + ":" + c.name for c in ag.asset_check_keys]
for s in defs.schedules or []:
    out["schedules"][s.name] = {"cron": s.cron_schedule, "tz": s.execution_timezone, "job": s.job_name}
if "--materialize" in sys.argv:
    from dagster import AssetSelection, AssetKey, DagsterInstance, materialize
    from orchestration.dagster_maystore import definitions as m
    key = next(k for k in ag.get_all_asset_keys() if k.path[-1] == "fct_ad_spend")
    assets = [d for d in (defs.assets or [])]
    r = materialize(assets, selection=AssetSelection.keys(key).upstream(), resources=defs.resources,
                    instance=DagsterInstance.ephemeral(), raise_on_error=False)
    out["materialize"] = {"success": r.success,
                          "assets": ["/".join(e.asset_key.path) for e in r.get_asset_materialization_events()],
                          "checks": len(r.get_asset_check_evaluations())}
print("@@JSON@@" + json.dumps(out))
"""

_dagster = {}


def dagster_info(materialize=False):
    key = "m" if materialize else "p"
    if key in _dagster:
        return _dagster[key]
    if not (LAB_DIR / "orchestration" / "dagster_maystore" / "definitions.py").exists():
        raise Skip("chưa có orchestration/dagster_maystore/definitions.py")
    if not (TARGET / "manifest.json").exists():
        raise Skip("chưa có target/manifest.json (dbt parse)")
    args = [sys.executable, "-c", DAGSTER_PROBE] + (["--materialize"] if materialize else [])
    env = {**os.environ, "DBT_PROFILES_DIR": str(LAB_DIR), "DAGSTER_HOME": tempfile.mkdtemp(prefix="dagster_home_")}
    proc = subprocess.run(args, cwd=LAB_DIR, env=env, capture_output=True, text=True, timeout=600)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("@@JSON@@")), None)
    if not line:
        err = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()][-5:]
        raise Fail("nạp Definitions lỗi: " + " / ".join(err)[:600])
    _dagster[key] = json.loads(line[len("@@JSON@@"):])
    return _dagster[key]


def asset_by_name(info, name):
    return [k for k in info["assets"] if k.split("/")[-1] == name]


def check_O1():
    """Dagster: dbt model thành asset"""
    info = dagster_info()
    if not info["assets"]:
        raise Skip("Definitions chưa có asset nào")
    for m in [m for m in PUBLIC_MARTS if m != "dim_customers"] + ["growth_campaign_daily"]:
        if not asset_by_name(info, m):
            raise Fail(f"không có asset cho model {m}")
    if not (asset_by_name(info, "dim_customers") or asset_by_name(info, "dim_customers_v2")):
        raise Fail("không có asset cho dim_customers")
    if any("elementary" in k or k.split("/")[-1].startswith(("dbt_", "elementary_")) for k in info["assets"]):
        raise Fail("bảng hệ thống của Elementary đang thành asset → exclude='package:elementary'")


def check_O2():
    """Dagster: tên asset nguồn + group theo đội"""
    info = dagster_info()
    if not info["assets"]:
        raise Skip("Definitions chưa có asset nào")
    raw = [k for k in info["assets"] if k.startswith("raw/")]
    if not {"raw/shop/orders", "raw/web/sessions", "raw/mkt/ad_spend"} <= set(raw):
        raise Fail(f"source phải có asset key raw/<schema>/<bảng> (đang thấy: {sorted(raw)[:5]})")
    if any(info["assets"][k]["materializable"] for k in raw):
        raise Fail("asset nguồn không được materialize bởi Dagster (do connector tạo)")
    for model, g in {"fct_orders": "commerce", "fct_sessions": "growth", "stg_crm__customers": "customer"}.items():
        ks = asset_by_name(info, model)
        if not ks or info["assets"][ks[0]]["group"] != g:
            raise Fail(f"asset {model} phải ở group {g} (đang {info['assets'][ks[0]]['group'] if ks else 'không có'})")


def check_O3():
    """Dagster: lịch 06:30 giờ Việt Nam"""
    info = dagster_info()
    s = info["schedules"]
    if not s:
        raise Skip("chưa có schedule")
    ok = [n for n, v in s.items() if v["cron"] == "30 6 * * *" and v["tz"] == "Asia/Ho_Chi_Minh"]
    if not ok:
        raise Fail(f"cần 1 schedule cron '30 6 * * *', execution_timezone 'Asia/Ho_Chi_Minh' (đang {s})")


def check_O4():
    """Dagster: asset check từ dbt test + chạy thật"""
    info = dagster_info()
    if not info["assets"]:
        raise Skip("Definitions chưa có asset nào")
    if not any(c.split(":")[0].endswith("fct_orders") and "unique" in c for c in info["checks"]):
        raise Fail("test dbt chưa thành asset check (cần thấy check unique_... trên fct_orders)")
    info = dagster_info(materialize=True)
    m = info.get("materialize") or {}
    if not m.get("success"):
        raise Fail(f"materialize fct_ad_spend + upstream thất bại: {m}")
    if not any(a.endswith("fct_ad_spend") for a in m["assets"]) or m["checks"] == 0:
        raise Fail(f"materialize không ra fct_ad_spend hoặc không chạy asset check nào: {m}")


AIRFLOW_PROBE = r"""
import json, os, sys
try:
    from airflow.dag_processing.dagbag import DagBag      # Airflow ≥ 3.1
except ImportError:
    from airflow.models.dagbag import DagBag
bag = DagBag(dag_folder=sys.argv[1])
d = bag.dags.get("mayshop_dbt")
out = {"errors": {k: str(v)[:300] for k, v in bag.import_errors.items()}}
if d:
    out.update({"tasks": [t.task_id for t in d.tasks], "schedule": str(getattr(d, "schedule", None) or getattr(d.timetable, "_expression", "")
                                                                   or getattr(d.timetable, "summary", "")),
                "max_active_tasks": d.max_active_tasks, "catchup": d.catchup})
print("@@JSON@@" + json.dumps(out))
"""


def check_O5():
    """Airflow 3 + Cosmos (venv riêng)"""
    af = LAB_DIR / "orchestration" / "airflow"
    py = af / ".venv" / "bin" / "python"
    dags = af / "dags"
    if not (dags / "mayshop_dbt.py").exists():
        raise Skip("chưa có orchestration/airflow/dags/mayshop_dbt.py")
    if not py.exists():
        raise Skip("chưa có venv Airflow: cd orchestration/airflow && uv sync")
    home = tempfile.mkdtemp(prefix="airflow_home_")
    env = {**os.environ, "AIRFLOW_HOME": home, "AIRFLOW__CORE__LOAD_EXAMPLES": "False",
           "MAYSHOP_LAB_DIR": str(LAB_DIR), "MAYSHOP_DBT_BIN": str(BIN / "dbt")}
    env.pop("VIRTUAL_ENV", None)
    proc = subprocess.run([str(py), "-c", AIRFLOW_PROBE, str(dags)], cwd=af, env=env,
                          capture_output=True, text=True, timeout=600)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("@@JSON@@")), None)
    if not line:
        raise Fail("nạp DAG lỗi: " + " / ".join((proc.stdout + proc.stderr).strip().splitlines()[-4:])[:500])
    info = json.loads(line[len("@@JSON@@"):])
    if info["errors"]:
        raise Fail(f"DAG import error: {info['errors']}")
    if "tasks" not in info:
        raise Fail("không có DAG id mayshop_dbt")
    tasks = info["tasks"]
    if not any(t.startswith("fct_orders") for t in tasks):
        raise Fail(f"DAG chưa có task cho fct_orders (đang {len(tasks)} task)")
    if any("elementary" in t or t.startswith("dbt_") for t in tasks):
        raise Fail("DAG đang render cả model của package Elementary → select path:models")
    if "30 6 * * *" not in (info.get("schedule") or ""):
        raise Fail(f"schedule phải là '30 6 * * *' (đang {info.get('schedule')})")
    if info.get("max_active_tasks") != 1:
        raise Fail("DuckDB chỉ cho 1 tiến trình ghi: đặt max_active_tasks=1")


# =========================================================================== chạy

CHECKS = [
    ("M1", "Time spine", check_M1), ("M2", "Semantic model, entity, dimension", check_M2),
    ("M3", "Simple metric", check_M3), ("M4", "Ratio metric", check_M4), ("M5", "Derived metric", check_M5),
    ("M6", "Cumulative metric", check_M6), ("M7", "Truy vấn theo dimension", check_M7),
    ("M8", "Saved query", check_M8),
    ("Q1", "Freshness theo SLA", check_Q1), ("Q2", "Volume anomaly", check_Q2), ("Q3", "Null spike", check_Q3),
    ("Q4", "Giá trị mới: warn", check_Q4), ("Q5", "Schema change", check_Q5), ("Q6", "Đơn giá sai đơn vị", check_Q6),
    ("Q7", "Không báo động giả", check_Q7),
    ("G1", "Groups", check_G1), ("G2", "Access", check_G2), ("G3", "Contracts", check_G3),
    ("G4", "Versions", check_G4), ("G5", "PII", check_G5), ("G6", "Exposures", check_G6),
    ("O1", "Dagster assets", check_O1), ("O2", "Dagster translator", check_O2), ("O3", "Dagster schedule", check_O3),
    ("O4", "Dagster asset checks + chạy", check_O4), ("O5", "Airflow + Cosmos", check_O5),
]


def summary_day(d):
    try:
        x = replay_day(d)
    except Skip:
        return
    fr = {s: v for s, v in x["fresh"].items() if v != "pass"}
    tests = [f"{t['name']}@{node_name(t['attached'] or (t['deps'] or [''])[0])}={t['status']}"
             for t in x["tests"] if t["status"] in BAD]
    err = [m for m, s in x["models"].items() if s in ("error", "skipped")]
    print(f"📋 Ngày {d}: freshness {fr or 'xanh'} · test bật {tests or 'không'} · model lỗi/skip {err or 'không'}")


def main(argv):
    if len(argv) > 2 and argv[1] == "--summary-day":
        summary_day(int(argv[2]))
        return
    wanted = [a.upper() for a in argv[1:]]
    chosen = [c for c in CHECKS if not wanted or any(c[0].startswith(w) for w in wanted)]
    try:
        print(f"📅 Lab đang ở ngày {lab_day()}\n")
    except Skip as e:
        print(f"⚠️  {e}\n")
    n_pass = 0
    for cid, title, fn in chosen:
        try:
            fn()
            print(f"{PASS}  {cid} {title}")
            n_pass += 1
        except Skip as e:
            print(f"{SKIP}  {cid} {title} — {e}")
        except Fail as e:
            print(f"{FAIL}  {cid} {title} — {e}")
        except Exception as e:  # lỗi bất ngờ: in gọn để không che các bài khác
            print(f"{FAIL}  {cid} {title} — lỗi khi chấm: {type(e).__name__}: {e}")
    print(f"\n{n_pass}/{len(chosen)} bài PASS")


if __name__ == "__main__":
    main(sys.argv)
