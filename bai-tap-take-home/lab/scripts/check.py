#!/usr/bin/env python3
"""Tự chấm PHẦN KHÁCH QUAN của take-home (chạy từ lab/ sau `dbt build`).

  python scripts/check.py

Đáp án tính bằng Python thuần trực tiếp từ dữ liệu nguồn (không dùng SQL của bạn).
Phần chủ quan (cấu trúc project, test, tài liệu, quyết định) tự chấm bằng rubric trong README.
"""
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

LAB = Path(__file__).resolve().parent.parent
DB = LAB / "takehome.duckdb"
PASS, FAIL, SKIP = "✅ PASS", "❌ FAIL", "⏭️  SKIP"
TOL = Decimal("0.01")


class Skip(Exception):
    pass


class Fail(Exception):
    pass


con = duckdb.connect(str(DB), read_only=True)
START, AS_OF = con.execute("select start_date, as_of_date from _check.meta").fetchone()


def days(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


# =========================================================================== đáp án chuẩn

events = con.execute("""select distinct lsn, op, txn_id, account_id, value_date, amount, currency, txn_type, channel, status
                        from core.txn_cdc order by lsn""").fetchall()
state = {}
for lsn, op, tid, acc, vd, amt, cur, tt, ch, st in events:
    state[tid] = None if op == "d" else dict(account_id=acc, value_date=vd, amount=amt, currency=cur,
                                             txn_type=tt, channel=ch, status=st)
posted = {k: v for k, v in state.items() if v and v["status"] == "POSTED"}

accounts = {a: dict(customer_id=c, product=p, currency=cur, open_date=o, close_date=cl) for a, c, p, cur, o, cl in
            con.execute("select account_id, customer_id, product, currency, open_date, close_date from core.accounts").fetchall()}
fx = dict(((d, c), v) for d, c, v in con.execute("select rate_date, currency, vnd_per_unit from ref.fx_rates").fetchall())


def rate(cur, d):
    if cur == "VND":
        return Decimal(1)
    k = d
    while (k, cur) not in fx:
        k -= timedelta(days=1)
    return fx[(k, cur)]


EXP_TXN = {}
for tid, v in posted.items():
    a = accounts[v["account_id"]]
    EXP_TXN[tid] = dict(account_id=v["account_id"], customer_id=a["customer_id"], value_date=v["value_date"],
                        amount=v["amount"], currency=v["currency"], amount_vnd=v["amount"] * rate(v["currency"], v["value_date"]),
                        txn_type=v["txn_type"], channel=v["channel"])

delta = defaultdict(lambda: defaultdict(Decimal))
for v in posted.values():
    delta[v["account_id"]][v["value_date"]] += v["amount"]
EXP_BAL = {}
for acc, a in accounts.items():
    bal = Decimal(0)
    end = a["close_date"] or AS_OF
    for d in days(a["open_date"], end):
        bal += delta[acc].get(d, Decimal(0))
        if d >= START:
            EXP_BAL[(acc, d)] = (bal, bal * rate(a["currency"], d))

gl = {(d, p, c): v for d, p, c, v in con.execute("select balance_date, product, currency, gl_balance from gl.daily_balances").fetchall()}
sums = defaultdict(Decimal)
for (acc, d), (b, _) in EXP_BAL.items():
    a = accounts[acc]
    sums[(d, a["product"], a["currency"])] += b
EXP_REC = {}
for k, g in gl.items():
    s = sums.get(k, Decimal(0))
    EXP_REC[k] = (s, g, s - g, abs(s - g) < TOL)

EXP_CUST = {}
months = sorted({date(d.year, d.month, 1) for d in days(START, AS_OF)})
by_cust_day = defaultdict(Decimal)
open_days = defaultdict(set)
for (acc, d), (_, bv) in EXP_BAL.items():
    c = accounts[acc]["customer_id"]
    by_cust_day[(c, d)] += bv
    open_days[(c, date(d.year, d.month, 1))].add(d)
for (c, m), ds in open_days.items():
    tx = [t for t in EXP_TXN.values() if t["customer_id"] == c and date(t["value_date"].year, t["value_date"].month, 1) == m]
    EXP_CUST[(c, m)] = dict(
        total_inflow_vnd=sum((t["amount_vnd"] for t in tx if t["amount"] > 0), Decimal(0)),
        total_outflow_vnd=sum((-t["amount_vnd"] for t in tx if t["amount"] < 0), Decimal(0)),
        txn_count=len(tx),
        avg_daily_balance_vnd=sum(by_cust_day[(c, d)] for d in ds) / len(ds),
        is_active=any(t["channel"] != "SYSTEM" for t in tx),
    )


# =========================================================================== tiện ích

def rel(name):
    r = con.execute("""select table_schema from information_schema.tables where table_name = ?
                       and table_schema not in ('core','ref','gl','_check') order by table_schema""", [name]).fetchall()
    if not r:
        raise Skip(f"chưa có bảng `{name}`")
    return f'"{r[0][0]}"."{name}"'


def cols(r):
    s, t = [x.strip('"') for x in r.split(".")]
    return [x[0] for x in con.execute("select column_name from information_schema.columns where table_schema=? and table_name=?",
                                      [s, t]).fetchall()]


def need(r, cs):
    have = cols(r)
    miss = [c for c in cs if c not in have]
    if miss:
        raise Fail(f"{r} thiếu cột {miss}")


def num_eq(a, b):
    if a is None or b is None:
        return a is None and b is None
    a, b = Decimal(str(a)), Decimal(str(b))
    return abs(a - b) <= max(TOL, abs(b) * Decimal("1e-9"))


def compare(label, exp, act, fields, limit=3):
    miss = [k for k in exp if k not in act]
    extra = [k for k in act if k not in exp]
    wrong = []
    for k in exp:
        if k in act:
            for f in fields:
                e, a = exp[k][f], act[k][f]
                ok = (e == a) if isinstance(e, (bool, str, date)) or f == "txn_count" else num_eq(a, e)
                if not ok:
                    wrong.append((k, f, e, a))
                    break
    msg = []
    if miss:
        msg.append(f"thiếu {len(miss)} dòng (vd {sorted(miss, key=str)[:limit]})")
    if extra:
        msg.append(f"thừa {len(extra)} dòng (vd {sorted(extra, key=str)[:limit]})")
    if wrong:
        msg.append(f"sai {len(wrong)} dòng, vd " + "; ".join(f"{k} {f}: mong đợi {e}, có {a}" for k, f, e, a in wrong[:limit]))
    if msg:
        raise Fail(f"{label}: " + " | ".join(msg))


# =========================================================================== các bài

def check_1():
    """fct_transactions"""
    r = rel("fct_transactions")
    f = ["account_id", "customer_id", "value_date", "amount", "currency", "amount_vnd", "txn_type", "channel"]
    need(r, ["txn_id"] + f)
    rows = con.execute(f"select txn_id, {', '.join(f)} from {r}").fetchall()
    if len(rows) != len({x[0] for x in rows}):
        raise Fail("txn_id bị trùng: nhật ký CDC có sự kiện phát lại (cùng lsn) và mỗi giao dịch có nhiều sự kiện")
    act = {x[0]: dict(zip(f, x[1:])) for x in rows}
    deleted = [k for k, v in state.items() if v is None]
    reversed_ = [k for k, v in state.items() if v and v["status"] == "REVERSED"]
    if any(k in act for k in deleted):
        raise Fail("còn giao dịch đã bị xoá (op = 'd') trong bảng")
    if any(k in act for k in reversed_):
        raise Fail("còn giao dịch đã bị đảo (status = 'REVERSED')")
    try:
        compare("fct_transactions", EXP_TXN, act, f)
    except Fail as e:
        hint = ""
        if "amount_vnd" in str(e):
            hint = " → Gợi ý: tỷ giá chỉ có ngày làm việc (cuối tuần, 01/01 không có): dùng tỷ giá gần nhất TRƯỚC đó; VND = 1"
        elif "value_date" in str(e):
            hint = " → Gợi ý: ngày nghiệp vụ là value_date, không phải ngày của booking_ts/commit_ts (UTC, có ghi sổ lùi ngày)"
        elif "amount" in str(e):
            hint = " → Gợi ý: lấy bản ghi có lsn LỚN NHẤT của mỗi txn_id (sự kiện 'u' sửa số tiền)"
        raise Fail(str(e) + hint)


def check_2():
    """fct_account_daily_balance"""
    r = rel("fct_account_daily_balance")
    need(r, ["account_id", "balance_date", "balance", "balance_vnd"])
    rows = con.execute(f"select account_id, balance_date, balance, balance_vnd from {r}").fetchall()
    act = {(a, d): dict(balance=b, balance_vnd=bv) for a, d, b, bv in rows}
    if len(act) != len(rows):
        raise Fail("trùng (account_id, balance_date)")
    exp = {k: dict(balance=v[0], balance_vnd=v[1]) for k, v in EXP_BAL.items()}
    try:
        compare("fct_account_daily_balance", exp, act, ["balance", "balance_vnd"])
    except Fail as e:
        hint = ""
        s = str(e)
        if "thiếu" in s:
            hint = " → Gợi ý: bảng phải DÀY ĐẶC (mọi ngày, kể cả ngày không có giao dịch) từ max(open_date, 01/11/2026) tới min(close_date, as_of_date)"
        elif "balance:" in s:
            hint = (" → Gợi ý: số dư = luỹ kế MỌI giao dịch từ ngày mở tài khoản, kể cả trước 01/11/2026 "
                    "(nằm trong snapshot op = 'r')")
        raise Fail(s + hint)


def check_3():
    """rpt_gl_reconciliation"""
    r = rel("rpt_gl_reconciliation")
    f = ["balance_date", "product", "currency", "total_account_balance", "gl_balance", "difference", "is_matched"]
    need(r, f)
    rows = con.execute(f"select {', '.join(f)} from {r}").fetchall()
    act = {(x[0], x[1], x[2]): dict(total_account_balance=x[3], gl_balance=x[4], difference=x[5], is_matched=x[6]) for x in rows}
    exp = {k: dict(total_account_balance=v[0], gl_balance=v[1], difference=v[2], is_matched=v[3]) for k, v in EXP_REC.items()}
    compare("rpt_gl_reconciliation", exp, act, ["total_account_balance", "gl_balance", "difference", "is_matched"])
    unmatched = [k for k, v in act.items() if not v["is_matched"]]
    if len(unmatched) != 1:
        raise Fail(f"có {len(unmatched)} dòng lệch sổ cái (đúng ra chỉ 1 ngày GL hạch toán nhầm)")


def check_4():
    """mart_customer_monthly"""
    r = rel("mart_customer_monthly")
    f = ["total_inflow_vnd", "total_outflow_vnd", "txn_count", "avg_daily_balance_vnd", "is_active"]
    need(r, ["customer_id", "month_start"] + f)
    rows = con.execute(f"select customer_id, month_start, {', '.join(f)} from {r}").fetchall()
    act = {(x[0], x[1]): dict(zip(f, x[2:])) for x in rows}
    try:
        compare("mart_customer_monthly", EXP_CUST, act, f)
    except Fail as e:
        hint = ""
        if "avg_daily_balance_vnd" in str(e):
            hint = " → Gợi ý: trung bình theo NGÀY khách có ≥1 tài khoản mở trong tháng, của TỔNG số dư các tài khoản (semi-additive)"
        elif "is_active" in str(e):
            hint = " → Gợi ý: lãi (INTEREST) và lương (SALARY) do hệ thống tạo (channel SYSTEM) không tính là khách hoạt động"
        raise Fail(str(e) + hint)


def check_5():
    """Test và tài liệu tối thiểu (đọc manifest)"""
    mf = LAB / "target" / "manifest.json"
    if not mf.exists():
        raise Skip("chưa có target/manifest.json")
    m = json.loads(mf.read_text())
    tests = [n for n in m["nodes"].values() if n["resource_type"] == "test"]
    def has_unique(model, col):
        return any(t.get("test_metadata", {}).get("name") in ("unique", "unique_combination_of_columns")
                   and any(d.endswith(f".{model}") for d in t["depends_on"]["nodes"]) for t in tests) or \
            any(t.get("test_metadata", {}).get("name") == "unique_combination_of_columns" for t in tests
                if any(d.endswith(f".{model}") for d in t["depends_on"]["nodes"]))
    for model in ("fct_transactions", "fct_account_daily_balance", "rpt_gl_reconciliation", "mart_customer_monthly"):
        if not has_unique(model, None):
            raise Fail(f"{model} chưa có test khoá (unique / unique_combination_of_columns / constraint)")
    if not m.get("sources"):
        raise Fail("chưa khai báo sources")
    undocumented = [n["name"] for n in m["nodes"].values() if n["resource_type"] == "model"
                    and n["package_name"] == m["metadata"].get("project_name", "sen_bank") and not n.get("description")]
    if undocumented:
        raise Fail(f"model chưa có description: {undocumented[:5]}")
    if not (LAB / "README.md").exists():
        raise Fail("chưa có lab/README.md (giả định, quyết định, việc sẽ làm tiếp)")
    txt = (LAB / "README.md").read_text(encoding="utf-8").lower()
    for sec in ("giả định", "quyết định", "tiếp theo"):
        if sec not in txt:
            raise Fail(f"README.md thiếu mục '{sec}'")


CHECKS = [("1", "fct_transactions", check_1), ("2", "fct_account_daily_balance", check_2),
          ("3", "rpt_gl_reconciliation", check_3), ("4", "mart_customer_monthly", check_4),
          ("5", "Test + tài liệu tối thiểu", check_5)]

n = 0
for cid, title, fn in CHECKS:
    try:
        fn()
        print(f"{PASS}  {cid}. {title}")
        n += 1
    except Skip as e:
        print(f"{SKIP}  {cid}. {title} — {e}")
    except Fail as e:
        print(f"{FAIL}  {cid}. {title} — {e}")
print(f"\n{n}/{len(CHECKS)} phần khách quan PASS. Phần chủ quan: tự chấm theo rubric trong README.md của bài.")
sys.exit(0 if n == len(CHECKS) else 1)
