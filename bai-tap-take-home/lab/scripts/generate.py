#!/usr/bin/env python3
"""Sinh dữ liệu cho bài take-home "Ngân hàng số Sen" vào lab/takehome.duckdb.

  python scripts/generate.py          # tạo lại từ đầu (xoá file cũ)

Nguồn (mô phỏng những gì một ngân hàng thật đưa cho đội dữ liệu):
  core.customers    khách hàng (trạng thái hiện tại)
  core.accounts     tài khoản (trạng thái hiện tại, có close_date)
  core.txn_cdc      NHẬT KÝ CDC của bảng giao dịch (kiểu Debezium): r = snapshot ban đầu, c = tạo, u = sửa, d = xoá
  ref.fx_rates      tỷ giá USD→VND theo NGÀY LÀM VIỆC (cuối tuần, ngày lễ không có dòng)
  gl.daily_balances số dư sổ cái (General Ledger) cuối ngày theo sản phẩm × loại tiền
Schema _check chỉ dùng để chấm. Toàn bộ dữ liệu sinh tất định từ SEED.
"""
import csv
import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb

LAB = Path(__file__).resolve().parent.parent
DB = LAB / "takehome.duckdb"
TMP = LAB / ".gen"
SEED = 1902
START = date(2026, 11, 1)          # đầu kỳ báo cáo
AS_OF = date(2027, 1, 31)          # ngày khoá sổ
HIST = date(2026, 9, 1)            # tài khoản cũ nhất mở từ ngày này
VN = timezone(timedelta(hours=7))
SNAPSHOT_TS = datetime(2026, 10, 31, 17, 0, tzinfo=timezone.utc)   # = 01/11 00:00 giờ VN: connector chụp snapshot ban đầu
GL_ERROR = (date(2027, 1, 15), "SAVING", "VND", Decimal(2_000_000))  # sổ cái hạch toán nhầm 1 ngày


def q2(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def days(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def month_end(d: date) -> bool:
    return (d + timedelta(days=1)).day == 1


def main():
    rng = random.Random(SEED)
    if DB.exists():
        DB.unlink()
    TMP.mkdir(exist_ok=True)

    # ------------------------------------------------------------------ tỷ giá (chỉ ngày làm việc, nghỉ 01/01)
    fx = {}
    r = Decimal("25380.00")
    for d in days(HIST - timedelta(days=5), AS_OF):
        r = q2(r + Decimal(rng.uniform(-25, 28)))
        if d.weekday() < 5 and d != date(2027, 1, 1):
            fx[d] = r

    def rate(cur, d):
        if cur == "VND":
            return Decimal(1)
        k = d
        while k not in fx:
            k -= timedelta(days=1)
        return fx[k]

    # ------------------------------------------------------------------ khách, tài khoản
    names = ["An", "Bình", "Chi", "Dũng", "Giang", "Hà", "Khoa", "Lan", "Minh", "Nga", "Phúc", "Quỳnh", "Sơn", "Trang", "Vy"]
    hos = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi"]
    customers, accounts = [], []
    aid = 100000
    for i in range(1, 151):
        cid = f"C{i:04d}"
        created = HIST + timedelta(days=rng.randint(0, 130))
        customers.append((cid, f"{rng.choice(hos)} {rng.choice(names)}", rng.choices(["retail", "priority", "sme"], [80, 15, 5])[0],
                          rng.choice(["HN", "HCM", "DN"]), datetime.combine(created, time(9, 0))))
        prods = [("CASA", "VND")]
        if rng.random() < 0.4:
            prods.append(("SAVING", "VND"))
        if rng.random() < 0.15:
            prods.append(("CASA", "USD"))
        for p, cur in prods:
            aid += 1
            od = created + timedelta(days=rng.randint(0, 20))
            if od > AS_OF - timedelta(days=3):
                od = AS_OF - timedelta(days=3)
            cd = None
            if rng.random() < 0.06:
                cd = max(od + timedelta(days=10), date(2026, 12, 1)) + timedelta(days=rng.randint(0, 50))
                if cd >= AS_OF:
                    cd = None
            accounts.append({"account_id": f"A{aid}", "customer_id": cid, "product": p, "currency": cur,
                             "open_date": od, "close_date": cd})

    # ------------------------------------------------------------------ giao dịch "sự thật" (theo từng tài khoản, tuần tự)
    txns = []   # dict: txn_id, account_id, value_date, booking_utc, amount, txn_type, channel
    tid = 0

    def add(acc, vd, amount, ttype, channel, booking_local=None):
        nonlocal tid
        tid += 1
        if booking_local is None:
            booking_local = datetime.combine(vd, time(rng.randint(6, 22), rng.randint(0, 59)), tzinfo=VN)
        txns.append({"txn_id": f"T{tid:07d}", "account_id": acc["account_id"], "value_date": vd,
                     "booking_utc": booking_local.astimezone(timezone.utc), "amount": amount,
                     "txn_type": ttype, "channel": channel, "currency": acc["currency"]})
        return txns[-1]

    for acc in accounts:
        usd = acc["currency"] == "USD"
        bal = Decimal(0)
        end = acc["close_date"] or AS_OF
        unit = (lambda lo, hi: q2(rng.uniform(lo, hi))) if usd else (lambda lo, hi: Decimal(rng.randint(lo // 1000, hi // 1000) * 1000))
        first = unit(200, 3000) if usd else unit(2_000_000, 80_000_000)
        add(acc, acc["open_date"], first, "DEPOSIT", rng.choice(["BRANCH", "MOBILE"]))
        bal += first
        for d in days(acc["open_date"] + timedelta(days=1), end):
            if acc["product"] == "SAVING":
                if month_end(d) and bal > 0:
                    it = (q2(bal * Decimal("0.004")) if usd else Decimal(int(bal * Decimal("0.004") / 1000) * 1000))
                    if it > 0:
                        add(acc, d, it, "INTEREST", "SYSTEM",
                            datetime.combine(d, time(23, 50), tzinfo=VN))   # 23:50 giờ VN = 16:50 UTC
                        bal += it
                if rng.random() < 0.03:
                    a = unit(50, 500) if usd else unit(1_000_000, 20_000_000)
                    add(acc, d, a, "DEPOSIT", "MOBILE")
                    bal += a
                continue
            if d.day == 5 and not usd:
                a = unit(8_000_000, 40_000_000)
                add(acc, d, a, "SALARY", "SYSTEM")
                bal += a
            for _ in range(rng.choice([0, 0, 0, 1, 1, 2])):
                if rng.random() < 0.35:
                    a = unit(20, 800) if usd else unit(100_000, 10_000_000)
                    add(acc, d, a, "TRANSFER_IN", rng.choice(["MOBILE", "INTERNET"]))
                    bal += a
                else:
                    cap = bal * Decimal("0.4")
                    a = unit(10, 300) if usd else unit(50_000, 5_000_000)
                    if a <= cap:
                        add(acc, d, -a, rng.choice(["TRANSFER_OUT", "CARD", "ATM"]), rng.choice(["MOBILE", "CARD", "ATM"]))
                        bal -= a
        if acc["close_date"] and bal != 0:
            add(acc, acc["close_date"], -bal, "CLOSE", "BRANCH")

    # ghi sổ lùi ngày: 1% giao dịch (không phải lãi/đóng) có booking muộn hơn value_date 1–3 ngày
    for t in txns:
        if t["txn_type"] in ("DEPOSIT", "TRANSFER_IN", "TRANSFER_OUT") and rng.random() < 0.01:
            t["booking_utc"] += timedelta(days=rng.randint(1, 3))

    # ------------------------------------------------------------------ nhật ký CDC
    events = []   # (commit_utc, op, after/before image)

    def image(t, status):
        return {"txn_id": t["txn_id"], "account_id": t["account_id"], "booking_ts": t["booking_utc"],
                "value_date": t["value_date"], "amount": t["amount"], "currency": t["currency"],
                "txn_type": t["txn_type"], "channel": t["channel"], "status": status}

    final = {}    # txn_id -> trạng thái cuối (None = đã xoá)
    acc_close = {a["account_id"]: a["close_date"] for a in accounts}
    for t in txns:
        commit = t["booking_utc"] + timedelta(seconds=rng.randint(1, 90))
        op = "r" if commit < SNAPSHOT_TS else "c"
        if op == "r":
            commit = SNAPSHOT_TS + timedelta(seconds=rng.randint(0, 600))
        events.append((commit, op, image(t, "POSTED")))
        final[t["txn_id"]] = image(t, "POSTED")
        # chỉ đảo / sửa / xoá các KHOẢN CHI của tài khoản chưa đóng → số dư chỉ tăng, không bao giờ âm
        if t["amount"] >= 0 or acc_close.get(t["account_id"]) is not None:
            continue
        x = rng.random()
        if x < 0.03:                              # đảo giao dịch (reversal) vài ngày sau
            when = commit + timedelta(days=rng.randint(1, 4), hours=rng.randint(0, 5))
            if when.astimezone(VN).date() <= AS_OF:
                events.append((when, "u", image(t, "REVERSED")))
                final[t["txn_id"]] = image(t, "REVERSED")
        elif x < 0.045:                           # sửa số tiền (nhập sai)
            when = commit + timedelta(hours=rng.randint(1, 30))
            if when.astimezone(VN).date() <= AS_OF:
                fixed = dict(t)
                fixed["amount"] = q2(t["amount"] * Decimal("0.9")) if t["currency"] == "USD" else \
                    Decimal(int(t["amount"] * Decimal("0.9") / 1000) * 1000)
                events.append((when, "u", image(fixed, "POSTED")))
                final[t["txn_id"]] = image(fixed, "POSTED")
        elif x < 0.05:                            # nhập nhầm → xoá hẳn
            when = commit + timedelta(minutes=rng.randint(5, 600))
            if when.astimezone(VN).date() <= AS_OF:
                events.append((when, "d", image(t, "POSTED")))
                final[t["txn_id"]] = None

    events.sort(key=lambda e: (e[0], e[2]["txn_id"]))
    rows = []
    for lsn, (commit, op, img) in enumerate(events, 1):
        rows.append((lsn * 10, op, commit, img))
    # connector khởi động lại: phát lại nguyên 1 lô 40 sự kiện (cùng lsn) đã gửi
    k = rng.randint(len(rows) // 2, len(rows) - 100)
    rows += rows[k:k + 40]

    # ------------------------------------------------------------------ sổ cái (GL) tính từ trạng thái cuối
    posted = [v for v in final.values() if v and v["status"] == "POSTED"]
    acc_by = {a["account_id"]: a for a in accounts}
    delta = {}
    for v in posted:
        delta.setdefault(v["account_id"], {}).setdefault(v["value_date"], Decimal(0))
        delta[v["account_id"]][v["value_date"]] += v["amount"]
    gl = {}
    for a in accounts:
        bal = Decimal(0)
        dd = delta.get(a["account_id"], {})
        for d in days(a["open_date"], a["close_date"] or AS_OF):
            bal += dd.get(d, Decimal(0))
            if d >= START:
                key = (d, a["product"], a["currency"])
                gl[key] = gl.get(key, Decimal(0)) + bal
        # ghi sổ trước open_date (backdated) không xảy ra: open_date là giao dịch đầu tiên
    gl[(GL_ERROR[0], GL_ERROR[1], GL_ERROR[2])] += GL_ERROR[3]
    for d in days(START, AS_OF):                  # sản phẩm không có tài khoản mở trong ngày → GL = 0
        for p, c in (("CASA", "VND"), ("SAVING", "VND"), ("CASA", "USD")):
            gl.setdefault((d, p, c), Decimal(0))

    # ------------------------------------------------------------------ ghi DuckDB
    con = duckdb.connect(str(DB))
    for s in ("core", "ref", "gl", "_check"):
        con.execute(f"create schema {s}")

    def write(table, cols, data):
        path = TMP / f"{table}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([c for c, _ in cols])
            for row in data:
                w.writerow(["" if v is None else v for v in row])
        types = ", ".join(f"'{c}': '{t}'" for c, t in cols)
        con.execute(f"create table {table} as select * from read_csv('{path}', header=true, nullstr='', "
                    f"columns={{{types}}})")

    write("core.customers", [("customer_id", "VARCHAR"), ("full_name", "VARCHAR"), ("segment", "VARCHAR"),
                             ("branch", "VARCHAR"), ("created_at", "TIMESTAMP")], customers)
    write("core.accounts", [("account_id", "VARCHAR"), ("customer_id", "VARCHAR"), ("product", "VARCHAR"),
                            ("currency", "VARCHAR"), ("open_date", "DATE"), ("close_date", "DATE")],
          [(a["account_id"], a["customer_id"], a["product"], a["currency"], a["open_date"], a["close_date"])
           for a in accounts])
    write("core.txn_cdc", [("lsn", "BIGINT"), ("op", "VARCHAR"), ("commit_ts", "TIMESTAMPTZ"),
                           ("txn_id", "VARCHAR"), ("account_id", "VARCHAR"), ("booking_ts", "TIMESTAMPTZ"),
                           ("value_date", "DATE"), ("amount", "DECIMAL(18,2)"), ("currency", "VARCHAR"),
                           ("txn_type", "VARCHAR"), ("channel", "VARCHAR"), ("status", "VARCHAR")],
          [(lsn, op, commit.isoformat(), i["txn_id"], i["account_id"], i["booking_ts"].isoformat(), i["value_date"],
            i["amount"], i["currency"], i["txn_type"], i["channel"], i["status"]) for lsn, op, commit, i in rows])
    write("ref.fx_rates", [("rate_date", "DATE"), ("currency", "VARCHAR"), ("vnd_per_unit", "DECIMAL(12,2)")],
          [(d, "USD", v) for d, v in sorted(fx.items())])
    write("gl.daily_balances", [("balance_date", "DATE"), ("product", "VARCHAR"), ("currency", "VARCHAR"),
                                ("gl_balance", "DECIMAL(20,2)")],
          [(d, p, c, v) for (d, p, c), v in sorted(gl.items())])
    con.execute("create table _check.meta as select ?::date as start_date, ?::date as as_of_date, ?::int as seed",
                [START, AS_OF, SEED])
    con.close()
    for f in TMP.glob("*.csv"):
        f.unlink()
    TMP.rmdir()
    n_ev = len(rows)
    print(f"✅ takehome.duckdb: {len(customers)} khách, {len(accounts)} tài khoản, {len(txns)} giao dịch, "
          f"{n_ev} sự kiện CDC, {len(fx)} ngày tỷ giá, {len(gl)} dòng sổ cái")


if __name__ == "__main__":
    main()
