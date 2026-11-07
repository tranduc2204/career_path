#!/usr/bin/env python3
"""Giả lập 5 hệ thống nguồn của "Mây Shop" (quý IV/2026) thay đổi theo từng NGÀY cho lab GĐ3.

Chạy từ thư mục lab/:
  python scripts/simulate.py reset     # XOÁ toàn bộ lab.duckdb (cả model dbt, cả lịch sử Elementary), nạp ngày 0
  python scripts/simulate.py next      # sang ngày kế tiếp (1 → 7)
  python scripts/simulate.py status    # đang ở ngày nào, đã xảy ra những gì
  python scripts/simulate.py goto N    # reset rồi nhảy thẳng tới ngày N
                                       # (Elementary sẽ không có kết quả của các ngày ở giữa: dùng replay.sh để chấm DQ)

Ngày N có ngày nghiệp vụ 2026-11-30 + N. Connector nạp dữ liệu của mỗi ngày lúc 06:00 sáng hôm sau,
dbt chạy lúc 06:30. Ngày 0 có sẵn 60 ngày lịch sử (01/10 → 29/11), mỗi ngày đã được nạp đều đặn.

Đồng hồ của lab: simulate.py ghi "bây giờ" (06:30 sáng hôm sau ngày nghiệp vụ) vào 2 dòng có đánh dấu
`# LAB_CLOCK` trong dbt_project.yml. Macro macros/lab_clock.sql và biến custom_run_started_at của Elementary
dùng giá trị này, nên freshness và anomaly detection chạy như thể đang ở đúng ngày của lab.

Toàn bộ kịch bản được công khai trong bai-tap/00-setup.md. Schema _lab chỉ dùng để chấm bài: đừng đọc nó trong model.
"""
import csv
import random
import re
import sys
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb

LAB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LAB_DIR / "lab.duckdb"
CACHE = LAB_DIR / ".sim_cache"
PROJECT_YML = LAB_DIR / "dbt_project.yml"

D0 = date(2026, 11, 30)              # ngày nghiệp vụ của ngày 0
HISTORY_START = date(2026, 10, 1)    # lịch sử có sẵn từ ngày này
MAX_DAY = 7
SEED = 2026
INITIAL_LOAD = datetime(2026, 10, 1, 6, 0)   # lần nạp đầu tiên của connector (toàn bộ dữ liệu trước 01/10)

SOURCE_SCHEMAS = ["shop", "crm", "erp", "web", "mkt", "ingest", "_lab"]


def bdate(day: int) -> date:
    return D0 + timedelta(days=day)


def load_of(d: date) -> datetime:
    """Thời điểm connector nạp dữ liệu phát sinh ngày nghiệp vụ d (06:00 sáng hôm sau)."""
    return datetime.combine(d + timedelta(days=1), time(6, 0))


def load_ts(day: int) -> datetime:
    return load_of(bdate(day))


def lab_now(day: int) -> datetime:
    """'Bây giờ' của lab ở ngày `day`: 06:30, ngay sau khi connector nạp xong."""
    return load_ts(day) + timedelta(minutes=30)


def round_1000(x: float) -> int:
    return int(x / 1000 + 0.5) * 1000


def ascii_slug(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


# =========================================================================== KỊCH BẢN (công khai)

EVENTS = {
    0: "Nạp ban đầu: 60 ngày lịch sử (01/10 → 29/11) + ngày 30/11. ~2.400 khách cũ, 50 sản phẩm, ~1.200 phiên/ngày, ~110 đơn/ngày",
    1: "Ngày bình thường (không có sự cố)",
    2: "Connector shop chỉ kịp kéo ~30% đơn ngày 02/12 (và các dòng hàng của chúng). Phần còn lại về vào lần nạp sau",
    3: "70% đơn ngày 02/12 về trễ. Lỗi tracking: ~90% phiên web ngày 03/12 mất customer_id (khách vẫn đăng nhập và mua bình thường). Sản phẩm P007 giảm giá niêm yết",
    4: "Connector quảng cáo (mkt) hết hạn token: không nạp được (sync_log ghi failed). Website mở phương thức thanh toán mới 'bnpl' (mua trước trả sau)",
    5: "Connector mkt vẫn lỗi. CRM nâng cấp phiên bản: cột `phone` của crm.customers đổi tên thành `phone_number`",
    6: "Connector mkt vẫn lỗi. Bản phát hành app lỗi: đơn kênh app ngày 06/12 ghi unit_price theo NGHÌN đồng (299 thay vì 299000). Sản phẩm P021 tăng giá",
    7: "Connector mkt chạy lại, nạp bù chi phí 04 → 07/12. Đội app sửa và ghi lại (restate) đúng unit_price các dòng ngày 06/12. Hết kịch bản",
}

PARTIAL_DAY = 2          # ngày connector shop nạp thiếu
PARTIAL_SHARE = 0.30
NULL_SPIKE_DAY = 3       # lỗi tracking customer_id trên web.sessions
NULL_SPIKE_SHARE = 0.90
BNPL_DAY = 4
MKT_OUTAGE = (4, 5, 6)   # các ngày connector mkt lỗi
RENAME_DAY = 5           # crm.customers: phone → phone_number
UNIT_BUG_DAY = 6         # app ghi unit_price theo nghìn đồng
PRICE_CHANGES = [(3, "P007", 0.80), (6, "P021", 1.15)]   # (ngày lab, sản phẩm, hệ số giá)

CATEGORIES = [  # (tên, số SP, khoảng giá)
    ("Thời trang", 12, (149_000, 899_000)),
    ("Giày dép", 7, (299_000, 1_590_000)),
    ("Điện tử", 9, (390_000, 4_990_000)),
    ("Phụ kiện", 8, (49_000, 490_000)),
    ("Nhà cửa", 8, (99_000, 1_290_000)),
    ("Làm đẹp", 6, (89_000, 690_000)),
]
BRANDS = ["Mây", "Sóng", "Lúa", "Gió", "Nắng", "Trúc", "Sen", "Đá"]
NOUNS = {
    "Thời trang": ["Áo thun", "Áo sơ mi", "Quần jean", "Váy", "Áo khoác", "Quần short"],
    "Giày dép": ["Giày chạy", "Sandal", "Giày lười", "Dép"],
    "Điện tử": ["Tai nghe", "Loa", "Sạc nhanh", "Đồng hồ", "Bàn phím", "Chuột"],
    "Phụ kiện": ["Ốp lưng", "Cáp sạc", "Ví", "Mũ", "Kính"],
    "Nhà cửa": ["Gối", "Đèn ngủ", "Bình nước", "Chảo", "Thảm"],
    "Làm đẹp": ["Sữa rửa mặt", "Kem chống nắng", "Son", "Nước hoa hồng"],
}
HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô", "Lý", "Mai", "Trương", "Phan", "Võ"]
DEM = ["Văn", "Thị", "Minh", "Thu", "Hoàng", "Ngọc", "Đức", "Thanh", "Quang", "Kim"]
TEN = ["An", "Bình", "Cường", "Dung", "Em", "Phương", "Giang", "Hoa", "Khánh", "Lan", "Minh", "Ngọc", "Phúc",
       "Quân", "Sơn", "Tâm", "Uyên", "Vy", "Yến", "Huy", "Trang", "Linh", "Nam", "Hải", "Thảo"]
CITIES = [("Ho Chi Minh", 34), ("Ha Noi", 30), ("Da Nang", 8), ("Hai Phong", 6), ("Can Tho", 5),
          ("Binh Duong", 6), ("Dong Nai", 4), ("Hue", 3), ("Nha Trang", 4)]
DOMAINS = ["gmail.com", "gmail.com", "gmail.com", "yahoo.com", "maymail.vn", "outlook.com"]
SEGMENTS = [("retail", 85), ("vip", 12), ("b2b", 3)]
DEVICES = [("mobile", 60), ("desktop", 25), ("app", 15)]
UTM = [("google", 30), ("facebook", 25), ("tiktok", 15), ("organic", 20), ("email", 10)]
PAID_BASE = {"google": 4_500_000, "facebook": 3_500_000, "tiktok": 2_500_000}
PAYMENTS = [("cod", 35), ("card", 30), ("ewallet", 30), ("bank_transfer", 5)]
PAGES = ["/", "/sale", "/category/thoi-trang", "/category/dien-tu", "/product", "/blog"]
REASONS = ["damaged", "wrong_item", "changed_mind", "late_delivery"]


def wchoice(rng, items):
    vals, weights = zip(*items)
    return rng.choices(vals, weights=weights, k=1)[0]


# =========================================================================== SINH DỮ LIỆU "SỰ THẬT"

class World:
    """Toàn bộ dữ liệu của cả dòng thời gian, sinh tất định từ SEED."""

    def __init__(self):
        rng = random.Random(SEED)
        end = bdate(MAX_DAY)
        self.end = end

        # ---- sản phẩm
        self.products = []           # dict
        pid = 0
        for cat, n, (lo, hi) in CATEGORIES:
            for _ in range(n):
                pid += 1
                price = int(rng.uniform(lo, hi)) // 10_000 * 10_000 + 9_000   # giá kiểu 299.000
                self.products.append({
                    "product_id": f"P{pid:03d}",
                    "product_name": f"{rng.choice(NOUNS[cat])} {rng.choice(BRANDS)} {pid:02d}",
                    "category": cat,
                    "brand": rng.choice(BRANDS),
                    "list_price": price,
                    "unit_cost": round_1000(price * rng.uniform(0.45, 0.70)),
                    "popularity": rng.uniform(0.3, 3.0),
                })
        self.prod_by_id = {p["product_id"]: p for p in self.products}
        # giá niêm yết theo thời gian
        self.price_hist = {p["product_id"]: [(date.min, p["list_price"])] for p in self.products}
        for day, prod, factor in PRICE_CHANGES:
            base = self.price_hist[prod][-1][1]
            self.price_hist[prod].append((bdate(day), round_1000(base * factor)))

        # ---- khách hàng
        self.customers = []
        cid = 0

        def new_customer(signup: date):
            nonlocal cid
            cid += 1
            ho, dem, ten = rng.choice(HO), rng.choice(DEM), rng.choice(TEN)
            email = f"{ascii_slug(ten)}.{ascii_slug(ho)}{cid}@{rng.choice(DOMAINS)}"
            if rng.random() < 0.05:   # nhập tay: viết hoa, dính khoảng trắng
                email = f" {email.capitalize()} "
            c = {
                "customer_id": cid,
                "full_name": f"{ho} {dem} {ten}",
                "email": email,
                "phone": "09" + "".join(str(rng.randint(0, 9)) for _ in range(8)),
                "city": wchoice(rng, CITIES),
                "segment": wchoice(rng, SEGMENTS),
                "birth_date": date(rng.randint(1965, 2006), rng.randint(1, 12), rng.randint(1, 28)),
                "signup_date": signup,
                "signup_ts": datetime.combine(signup, time(rng.randint(7, 22), rng.randint(0, 59))),
                "changes": [],          # (date, field, value)
            }
            self.customers.append(c)
            return c

        old_start = date(2025, 1, 1)
        for _ in range(2400):
            new_customer(old_start + timedelta(days=rng.randint(0, (HISTORY_START - old_start).days - 1)))
        self.customers.sort(key=lambda c: c["signup_ts"])
        for i, c in enumerate(self.customers, 1):     # đánh lại id theo thứ tự đăng ký
            c["customer_id"] = i
        cid = len(self.customers)
        for d in daterange(HISTORY_START, end):
            for _ in range(max(3, int(rng.gauss(16, 4)))):
                new_customer(d)
        # thay đổi thuộc tính (Type 1, nguồn ghi đè)
        for d in daterange(HISTORY_START, end):
            eligible = [c for c in self.customers if c["signup_date"] < d]
            for c in rng.sample(eligible, 4):
                if rng.random() < 0.5:
                    c["changes"].append((d, "city", wchoice(rng, CITIES)))
                else:
                    c["changes"].append((d, "segment", wchoice(rng, SEGMENTS)))

        # ---- phiên web, đơn hàng, dòng hàng
        self.sessions = []
        self.orders = []
        self.items = []
        signed = []          # khách đã đăng ký (tăng dần theo ngày)
        ci = 0
        prods = self.products
        weights = [p["popularity"] for p in prods]
        for d in daterange(HISTORY_START, end):
            while ci < len(self.customers) and self.customers[ci]["signup_date"] <= d:
                signed.append(self.customers[ci])
                ci += 1
            wf = 1.25 if d.weekday() >= 5 else 1.0
            trend = 1 + 0.002 * (d - HISTORY_START).days
            n = int(1100 * wf * trend * rng.uniform(0.92, 1.08))
            day_sessions = []
            for i in range(n):
                start = datetime.combine(d, time(7, 0)) + timedelta(seconds=rng.randint(0, 17 * 3600 - 1))
                logged = rng.random() < 0.6
                s = {
                    "session_id": f"S{d:%Y%m%d}{i:05d}",
                    "customer_id": rng.choice(signed)["customer_id"] if logged else None,
                    "session_start": start,
                    "device": wchoice(rng, DEVICES),
                    "utm_source": wchoice(rng, UTM),
                    "landing_page": rng.choice(PAGES),
                    "bdate": d,
                }
                day_sessions.append(s)
            day_sessions.sort(key=lambda s: s["session_start"])
            self.sessions.extend(day_sessions)
            # đơn hàng từ các phiên đã đăng nhập
            day_orders = []
            for s in day_sessions:
                if s["customer_id"] is None or rng.random() >= 0.16:
                    continue
                ots = s["session_start"] + timedelta(minutes=rng.randint(3, 45))
                if ots.date() != d:
                    ots = datetime.combine(d, time(23, 59, 0))
                pay_items = PAYMENTS + ([("bnpl", 9)] if d >= bdate(BNPL_DAY) else [])
                o = {
                    "customer_id": s["customer_id"],
                    "session_id": s["session_id"],
                    "order_ts": ots,
                    "order_date": d,
                    "channel": "app" if s["device"] == "app" else "web",
                    "utm_source": s["utm_source"],
                    "payment_method": wchoice(rng, pay_items),
                    "cancelled": rng.random() < 0.06,
                    "lines": [],
                }
                k = rng.choice([1, 1, 1, 2, 2, 3, 4])
                chosen = []
                while len(chosen) < k:
                    p = rng.choices(prods, weights=weights, k=1)[0]
                    if p not in chosen:
                        chosen.append(p)
                for ln, p in enumerate(chosen, 1):
                    disc = rng.choice([0, 0, 0, 0, 0.1, 0.2])
                    o["lines"].append({
                        "line_no": ln,
                        "product_id": p["product_id"],
                        "quantity": rng.choice([1, 1, 1, 1, 2, 2, 3]),
                        "unit_price": round_1000(self.price_at(p["product_id"], d) * (1 - disc)),
                        "unit_cost": p["unit_cost"],
                    })
                items_amount = sum(li["quantity"] * li["unit_price"] for li in o["lines"])
                o["shipping_fee"] = 0 if items_amount >= 500_000 else 30_000
                o["items_amount"] = items_amount
                day_orders.append(o)
            day_orders.sort(key=lambda o: o["order_ts"])
            self.orders.extend(day_orders)
        for i, o in enumerate(self.orders, 100001):
            o["order_id"] = i
            for li in o["lines"]:
                self.items.append({"order_id": i, **li, "order": o})

        # ---- hoàn tiền (chỉ đơn hoàn tất)
        self.refunds = []
        for o in self.orders:
            if o["cancelled"] or rng.random() >= 0.016:
                continue
            rd = o["order_date"] + timedelta(days=rng.randint(3, 12))
            if rd > end:
                continue
            amt = o["items_amount"] if rng.random() < 0.7 else round_1000(o["items_amount"] * 0.5)
            self.refunds.append({
                "order_id": o["order_id"],
                "refund_ts": datetime.combine(rd, time(rng.randint(9, 17), rng.randint(0, 59))),
                "refund_date": rd,
                "amount": amt,
                "reason": rng.choice(REASONS),
            })
        self.refunds.sort(key=lambda r: (r["refund_ts"], r["order_id"]))
        for i, r in enumerate(self.refunds, 1):
            r["refund_id"] = f"R{i:05d}"

        # ---- chi phí quảng cáo
        self.spend = []
        for d in daterange(HISTORY_START, end):
            wf = 1.2 if d.weekday() >= 5 else 1.0
            for src, base in PAID_BASE.items():
                self.spend.append({"spend_date": d, "utm_source": src,
                                   "spend": round_1000(base * wf * rng.uniform(0.85, 1.15))})

        # ---- quyết định ngẫu nhiên cho các sự cố (tất định)
        partial_orders = [o for o in self.orders if o["order_date"] == bdate(PARTIAL_DAY)]
        self.late_orders = {o["order_id"] for o in partial_orders if rng.random() >= PARTIAL_SHARE}
        spike = [s for s in self.sessions if s["bdate"] == bdate(NULL_SPIKE_DAY) and s["customer_id"] is not None]
        self.spike_sessions = {s["session_id"] for s in spike if rng.random() < NULL_SPIKE_SHARE}

    def price_at(self, pid, d):
        price = None
        for start, p in self.price_hist[pid]:
            if start <= d:
                price = p
        return price


# =========================================================================== TRẠNG THÁI THẤY ĐƯỢC Ở NGÀY N

def order_avail_day(w: World, o) -> int:
    """Ngày lab mà đơn lần đầu có mặt trong kho (âm = lịch sử, có sẵn từ ngày 0)."""
    day = (o["order_date"] - D0).days
    if o["order_id"] in w.late_orders:
        day += 1
    return day


def first_load(w: World, o) -> datetime:
    """Lần đầu đơn (và các dòng hàng của nó) được nạp vào kho."""
    extra = timedelta(days=1) if o["order_id"] in w.late_orders else timedelta(0)
    return load_of(o["order_date"]) + extra


def order_state(w: World, o, day: int):
    """(status, updated_at, _loaded_at) của đơn nhìn từ ngày lab `day`, hoặc None nếu chưa về.
    Vòng đời: placed (ngày đặt) → shipped / cancelled (D+1) → completed (D+3). Bảng nguồn GHI ĐÈ trạng thái."""
    if order_avail_day(w, o) > day:
        return None
    B = bdate(day)
    d = o["order_date"]
    status, upd, chg = "placed", o["order_ts"], d
    if d + timedelta(days=1) <= B:
        status = "cancelled" if o["cancelled"] else "shipped"
        upd, chg = datetime.combine(d + timedelta(days=1), time(10, 0)), d + timedelta(days=1)
    if not o["cancelled"] and d + timedelta(days=3) <= B:
        status = "completed"
        upd, chg = datetime.combine(d + timedelta(days=3), time(15, 0)), d + timedelta(days=3)
    return status, upd, max(first_load(w, o), load_of(chg))


def item_state(w: World, it, day: int):
    """(unit_price, _loaded_at) của dòng hàng nhìn từ ngày `day`, hoặc None nếu chưa về."""
    o = it["order"]
    avail = order_avail_day(w, o)
    if avail > day:
        return None
    loaded = first_load(w, o)
    price = it["unit_price"]
    if o["order_date"] == bdate(UNIT_BUG_DAY) and o["channel"] == "app":
        if day < MAX_DAY:
            price = price // 1000
        else:
            loaded = load_ts(MAX_DAY)    # restate
    return price, loaded


def customer_state(w: World, c, day: int):
    B = bdate(day)
    if c["signup_date"] > B:
        return None
    row = {k: c[k] for k in ("customer_id", "full_name", "email", "phone", "city", "segment", "birth_date", "signup_date")}
    upd = c["signup_ts"]
    loaded = INITIAL_LOAD if c["signup_date"] < HISTORY_START else load_of(c["signup_date"])
    for d, f, v in c["changes"]:
        if d <= B:
            row[f] = v
            upd = datetime.combine(d, time(11, 0))
            loaded = load_of(d)
    row["updated_at"] = upd
    row["_loaded_at"] = loaded
    return row


def spend_loaded(day_lab_of_date: int, day: int):
    """_loaded_at của chi phí ngày nghiệp vụ có chỉ số ngày lab `day_lab_of_date`, nhìn từ ngày `day`."""
    k = day_lab_of_date
    if k in MKT_OUTAGE:
        return load_ts(MAX_DAY) if day >= MAX_DAY else None
    if k > day:
        return None
    return load_ts(k) if k >= 0 else None   # None ở đây không xảy ra: lịch sử xử lý riêng


# =========================================================================== GHI VÀO DUCKDB

def write_table(con, schema, table, columns, rows):
    """columns: list (tên, kiểu SQL). Ghi qua CSV để nhanh."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{schema}.{table}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow([c for c, _ in columns])
        for r in rows:
            wr.writerow(["" if v is None else v for v in r])
    types = ", ".join(f"'{c}': '{t}'" for c, t in columns)
    con.execute(f'drop table if exists {schema}."{table}"')
    con.execute(f"""create table {schema}."{table}" as
                    select * from read_csv('{path}', header=true, columns={{{types}}}, nullstr='',
                                           quote='"', escape='"')""")


def materialize(con, w: World, day: int):
    B = bdate(day)
    for s in SOURCE_SCHEMAS:
        con.execute(f"create schema if not exists {s}")

    # ---- erp.products
    rows = []
    for p in w.products:
        price, loaded = p["list_price"], INITIAL_LOAD
        for d, pid, _ in PRICE_CHANGES:
            if pid == p["product_id"] and d <= day:
                price, loaded = w.price_at(pid, bdate(d)), load_ts(d)
        rows.append((p["product_id"], p["product_name"], p["category"], p["brand"], price, p["unit_cost"], loaded))
    write_table(con, "erp", "products", [("product_id", "VARCHAR"), ("product_name", "VARCHAR"), ("category", "VARCHAR"),
                                         ("brand", "VARCHAR"), ("list_price", "BIGINT"), ("unit_cost", "BIGINT"),
                                         ("_loaded_at", "TIMESTAMP")], rows)

    # ---- crm.customers
    phone_col = "phone_number" if day >= RENAME_DAY else "phone"
    rows = []
    for c in w.customers:
        st = customer_state(w, c, day)
        if st:
            rows.append((st["customer_id"], st["full_name"], st["email"], st["phone"], st["city"], st["segment"],
                         st["birth_date"], st["signup_date"], st["updated_at"], st["_loaded_at"]))
    write_table(con, "crm", "customers", [("customer_id", "INTEGER"), ("full_name", "VARCHAR"), ("email", "VARCHAR"),
                                          (phone_col, "VARCHAR"), ("city", "VARCHAR"), ("segment", "VARCHAR"),
                                          ("birth_date", "DATE"), ("signup_date", "DATE"), ("updated_at", "TIMESTAMP"),
                                          ("_loaded_at", "TIMESTAMP")], rows)

    # ---- web.sessions
    rows = []
    for s in w.sessions:
        if s["bdate"] > B:
            break
        cust = None if s["session_id"] in w.spike_sessions else s["customer_id"]
        rows.append((s["session_id"], cust, s["session_start"], s["device"], s["utm_source"], s["landing_page"],
                     load_of(s["bdate"])))
    write_table(con, "web", "sessions", [("session_id", "VARCHAR"), ("customer_id", "INTEGER"),
                                         ("session_start", "TIMESTAMP"), ("device", "VARCHAR"),
                                         ("utm_source", "VARCHAR"), ("landing_page", "VARCHAR"),
                                         ("_loaded_at", "TIMESTAMP")], rows)

    # ---- shop.orders, shop.order_items
    orows, irows = [], []
    for o in w.orders:
        if o["order_date"] > B:
            break
        st = order_state(w, o, day)
        if not st:
            continue
        status, upd, loaded = st
        orows.append((o["order_id"], o["customer_id"], o["session_id"], o["order_ts"], o["channel"], o["utm_source"],
                      o["payment_method"], o["shipping_fee"], status, upd, loaded))
    for it in w.items:
        o = it["order"]
        if o["order_date"] > B:
            break
        st = item_state(w, it, day)
        if not st:
            continue
        price, loaded = st
        irows.append((it["order_id"], it["line_no"], it["product_id"], it["quantity"], price, it["unit_cost"], loaded))
    write_table(con, "shop", "orders", [("order_id", "BIGINT"), ("customer_id", "INTEGER"), ("session_id", "VARCHAR"),
                                        ("order_ts", "TIMESTAMP"), ("channel", "VARCHAR"), ("utm_source", "VARCHAR"),
                                        ("payment_method", "VARCHAR"), ("shipping_fee", "BIGINT"),
                                        ("status", "VARCHAR"), ("updated_at", "TIMESTAMP"),
                                        ("_loaded_at", "TIMESTAMP")], orows)
    write_table(con, "shop", "order_items", [("order_id", "BIGINT"), ("line_no", "INTEGER"), ("product_id", "VARCHAR"),
                                             ("quantity", "INTEGER"), ("unit_price", "BIGINT"),
                                             ("unit_cost", "BIGINT"), ("_loaded_at", "TIMESTAMP")], irows)

    # ---- shop.refunds
    rows = [(r["refund_id"], r["order_id"], r["refund_ts"], r["amount"], r["reason"], load_of(r["refund_date"]))
            for r in w.refunds if r["refund_date"] <= B]
    write_table(con, "shop", "refunds", [("refund_id", "VARCHAR"), ("order_id", "BIGINT"), ("refund_ts", "TIMESTAMP"),
                                         ("amount", "BIGINT"), ("reason", "VARCHAR"), ("_loaded_at", "TIMESTAMP")], rows)

    # ---- mkt.ad_spend
    rows = []
    for sp in w.spend:
        k = (sp["spend_date"] - D0).days
        if k < 0:
            rows.append((sp["spend_date"], sp["utm_source"], sp["spend"], load_of(sp["spend_date"])))
            continue
        loaded = spend_loaded(k, day)
        if loaded:
            rows.append((sp["spend_date"], sp["utm_source"], sp["spend"], loaded))
    write_table(con, "mkt", "ad_spend", [("spend_date", "DATE"), ("utm_source", "VARCHAR"), ("spend", "BIGINT"),
                                         ("_loaded_at", "TIMESTAMP")], rows)

    # ---- ingest.sync_log: mỗi lần connector chạy ghi 1 dòng / bảng, kể cả khi 0 dòng mới hoặc lỗi
    counts = {}
    for schema, table in [("shop", "orders"), ("shop", "order_items"), ("shop", "refunds"), ("crm", "customers"),
                          ("erp", "products"), ("web", "sessions"), ("mkt", "ad_spend")]:
        for ts, n in con.execute(f'select _loaded_at, count(*) from {schema}."{table}" group by 1').fetchall():
            counts[(schema, table, ts)] = n
    rows = []
    sync_days = list(daterange(HISTORY_START - timedelta(days=1), B))
    for d in sync_days:
        ts = load_of(d)
        for schema, table in [("shop", "orders"), ("shop", "order_items"), ("shop", "refunds"), ("crm", "customers"),
                              ("erp", "products"), ("web", "sessions"), ("mkt", "ad_spend")]:
            k = (d - D0).days
            if schema == "mkt" and k in MKT_OUTAGE:
                rows.append((f"{schema}_connector", f"{schema}.{table}", ts + timedelta(minutes=2), 0, "failed",
                             "401 Unauthorized: access token expired"))
                continue
            n = counts.get((schema, table, ts), 0)
            rows.append((f"{schema}_connector", f"{schema}.{table}", ts + timedelta(minutes=2), n, "success", None))
    write_table(con, "ingest", "sync_log", [("connector", "VARCHAR"), ("table_name", "VARCHAR"),
                                            ("synced_at", "TIMESTAMP"), ("rows_synced", "BIGINT"),
                                            ("status", "VARCHAR"), ("error_message", "VARCHAR")], rows)

    # ---- _lab: chỉ để chấm
    con.execute("create or replace table _lab.state as select ? as day, ?::date as bdate, ?::timestamp as lab_now",
                [day, B, lab_now(day)])


def set_clock(day: int):
    """Cập nhật 2 dòng `# LAB_CLOCK` trong dbt_project.yml."""
    now = lab_now(day)
    s = PROJECT_YML.read_text(encoding="utf-8")
    s2 = re.sub(r'^(\s*lab_now:\s*)"[^"]*"(\s*# LAB_CLOCK.*)$', rf'\g<1>"{now:%Y-%m-%d %H:%M:%S}"\g<2>', s, flags=re.M)
    s2 = re.sub(r'^(\s*custom_run_started_at:\s*)"[^"]*"(\s*# LAB_CLOCK.*)$', rf'\g<1>"{now:%Y-%m-%dT%H:%M:%S}"\g<2>',
                s2, flags=re.M)
    if s2.count("# LAB_CLOCK") < 2 or s2 == s and f"{now:%Y-%m-%d %H:%M:%S}" not in s:
        print("⚠️  không tìm thấy 2 dòng `# LAB_CLOCK` (lab_now, custom_run_started_at) trong dbt_project.yml")
    PROJECT_YML.write_text(s2, encoding="utf-8")


def current_day(con):
    try:
        return con.execute("select day from _lab.state").fetchone()[0]
    except duckdb.Error:
        return None


def go(day: int, fresh: bool):
    if fresh and DB_PATH.exists():
        DB_PATH.unlink()
        wal = DB_PATH.with_suffix(".duckdb.wal")
        if wal.exists():
            wal.unlink()
    w = World()
    con = duckdb.connect(str(DB_PATH))
    materialize(con, w, day)
    con.close()
    set_clock(day)
    print(f"📅 Ngày {day} — nghiệp vụ {bdate(day):%d/%m/%Y}, 'bây giờ' = {lab_now(day):%d/%m/%Y %H:%M}")
    print(f"   {EVENTS[day]}")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "reset":
        go(0, fresh=True)
        print("   Đã xoá lab.duckdb và nạp lại ngày 0. Chạy: dbt build")
    elif cmd == "next":
        if not DB_PATH.exists():
            sys.exit("Chưa có lab.duckdb: chạy `python scripts/simulate.py reset` trước")
        con = duckdb.connect(str(DB_PATH))
        day = current_day(con)
        con.close()
        if day is None:
            sys.exit("lab.duckdb không có _lab.state: chạy reset")
        if day >= MAX_DAY:
            sys.exit(f"Đã ở ngày cuối ({MAX_DAY}). Muốn làm lại: reset hoặc ./scripts/replay.sh")
        go(day + 1, fresh=False)
    elif cmd == "goto":
        n = int(argv[2])
        if not 0 <= n <= MAX_DAY:
            sys.exit(f"N phải từ 0 tới {MAX_DAY}")
        go(n, fresh=True)
        print("   ⚠️  goto bỏ qua các ngày ở giữa: Elementary/freshness không có lịch sử của chúng. Chấm DQ bằng replay.sh")
    elif cmd == "status":
        if not DB_PATH.exists():
            print("Chưa có lab.duckdb")
            return
        con = duckdb.connect(str(DB_PATH), read_only=True)
        day = current_day(con)
        con.close()
        if day is None:
            print("lab.duckdb không có _lab.state")
            return
        print(f"📅 Đang ở ngày {day} — nghiệp vụ {bdate(day):%d/%m/%Y}, 'bây giờ' = {lab_now(day):%d/%m/%Y %H:%M}")
        for k in range(day + 1):
            print(f"   ngày {k} ({bdate(k):%d/%m}): {EVENTS[k]}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
