#!/usr/bin/env python3
"""Giả lập hệ thống nguồn thay đổi theo từng "ngày" cho lab incremental / snapshot / SCD2.

Chạy từ thư mục lab/:
  python scripts/simulate.py reset     # XOÁ toàn bộ lab.duckdb (cả model/snapshot), nạp dữ liệu ngày 0
  python scripts/simulate.py next      # áp dụng thay đổi của ngày kế tiếp (1 → 5)
  python scripts/simulate.py status    # đang ở ngày nào, đã xảy ra những gì
  python scripts/simulate.py goto N    # reset rồi nhảy thẳng tới ngày N
                                       # (cảnh báo: snapshot sẽ không thấy các ngày ở giữa)

Kịch bản đầy đủ của từng ngày: xem bai-tap/00-setup.md.
"""
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb

LAB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LAB_DIR / "lab.duckdb"
MAX_DAY = 5
FIRST_LOAD = datetime(2026, 1, 1, 6, 0)


def load_ts(day: int) -> datetime:
    """Thời điểm công cụ ingest nạp dữ liệu của ngày `day` vào kho (6h sáng hôm sau)."""
    return FIRST_LOAD + timedelta(days=day)


def business_date(day: int) -> date:
    """Ngày nghiệp vụ của đơn/sự kiện mới phát sinh trong ngày `day` (day >= 1)."""
    return date(2025, 12, 31) + timedelta(days=day)


def at(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute))


# --------------------------------------------------------------------------- schema

DDL = """
create schema raw;
create table raw.customers (
    customer_id int, full_name varchar, email varchar, city varchar, tier varchar,
    updated_at timestamp, _loaded_at timestamp
);
create table raw.customer_changelog (
    customer_id int, op varchar, full_name varchar, email varchar, city varchar, tier varchar,
    changed_at timestamp, _loaded_at timestamp
);
create table raw.products (
    product_id int, product_name varchar, category varchar, list_price_cents int,
    _loaded_at timestamp
);
create table raw.orders (
    order_id int, customer_id int, order_date date, status varchar, amount_cents int,
    updated_at timestamp, _loaded_at timestamp
);
create table raw.order_items (
    order_id int, line_no int, product_id int, quantity int, unit_price_cents int,
    _loaded_at timestamp
);
create table raw.events (
    event_id varchar, user_id int, event_type varchar, event_ts timestamp, _loaded_at timestamp
);
create table raw._lab_state (current_day int, changed_at timestamp);
create table raw._lab_log (day int, seq int, message varchar);
"""

CUSTOMERS = [
    (1, "Nguyen Van An", "an.nguyen@mail.com", "Ha Noi", "gold"),
    (2, "Tran Thi Binh", "  Binh.Tran@Mail.com ", "Ho Chi Minh", "silver"),
    (3, "Le Van Cuong", "cuong.le@mail.com", "Ha Noi", "bronze"),
    (4, "Pham Thi Dung", "dung.pham@mail.com", "Da Nang", "silver"),
    (5, "Hoang Van Em", "em.hoang@mail.com", "Hue", "silver"),
    (6, "Vu Thi Phuong", "phuong.vu@mail.com", "Can Tho", "bronze"),
    (7, "Dang Van Giang", "giang.dang@mail.com", "Ha Noi", "bronze"),
    (8, "Bui Thi Hoa", "hoa.bui@mail.com", "Ho Chi Minh", "bronze"),
    (9, "Do Van Khanh", "khanh.do@mail.com", "Da Nang", "gold"),
    (10, "Ngo Thi Lan", "lan.ngo@mail.com", "Hue", "silver"),
]

PRODUCTS = [
    (1, "  Basic T-Shirt ", "Apparel", 1999),
    (2, "Running Shoes", "Footwear", 8999),
    (3, "Backpack", "Accessories", 4599),
    (4, "Water Bottle", "Accessories", 1299),
    (5, "Phone Case", "Accessories", 1599),
    (6, "Hoodie", "Apparel", 3999),
    (7, "Sneakers ", "Footwear", 6999),
    (8, "Cap", "", 999),
]

EVENT_TYPES = ["page_view", "page_view", "page_view", "add_to_cart", "checkout"]


# --------------------------------------------------------------------------- helpers

class Sim:
    def __init__(self, con, day):
        self.con = con
        self.day = day
        self.rng = random.Random(1000 + day)
        self.seq = 0

    def log(self, msg):
        self.seq += 1
        self.con.execute("insert into raw._lab_log values (?, ?, ?)", [self.day, self.seq, msg])

    # ---- customers
    def insert_customer(self, cid, name, email, city, tier, updated_at):
        lt = load_ts(self.day)
        self.con.execute(
            "insert into raw.customers values (?, ?, ?, ?, ?, ?, ?)",
            [cid, name, email, city, tier, updated_at, lt],
        )
        self.con.execute(
            "insert into raw.customer_changelog values (?, 'I', ?, ?, ?, ?, ?, ?)",
            [cid, name, email, city, tier, updated_at, lt],
        )

    def update_customer(self, cid, changed_at, bump_updated_at=True, **cols):
        """Cập nhật khách hàng. bump_updated_at=False giả lập lỗi nguồn quên cập nhật updated_at."""
        lt = load_ts(self.day)
        sets = ", ".join(f"{k} = ?" for k in cols)
        params = list(cols.values())
        if bump_updated_at:
            sets += ", updated_at = ?"
            params.append(changed_at)
        sets += ", _loaded_at = ?"
        params += [lt, cid]
        self.con.execute(f"update raw.customers set {sets} where customer_id = ?", params)
        # changelog (CDC) luôn ghi đúng thời điểm thay đổi thật
        self.con.execute(
            """insert into raw.customer_changelog
               select customer_id, 'U', full_name, email, city, tier, ?, ?
               from raw.customers where customer_id = ?""",
            [changed_at, lt, cid],
        )

    def delete_customer(self, cid, changed_at):
        lt = load_ts(self.day)
        self.con.execute(
            """insert into raw.customer_changelog
               select customer_id, 'D', full_name, email, city, tier, ?, ?
               from raw.customers where customer_id = ?""",
            [changed_at, lt, cid],
        )
        self.con.execute("delete from raw.customers where customer_id = ?", [cid])

    def active_customer_ids(self):
        return [r[0] for r in self.con.execute("select customer_id from raw.customers order by 1").fetchall()]

    # ---- products
    def update_product(self, pid, **cols):
        sets = ", ".join(f"{k} = ?" for k in cols) + ", _loaded_at = ?"
        self.con.execute(
            f"update raw.products set {sets} where product_id = ?",
            list(cols.values()) + [load_ts(self.day), pid],
        )

    def product_prices(self):
        return dict(self.con.execute("select product_id, list_price_cents from raw.products").fetchall())

    def has_channel(self):
        cols = [r[0] for r in self.con.execute("describe raw.orders").fetchall()]
        return "channel" in cols

    # ---- orders
    def new_orders(self, order_date, n, status, updated_at_hour=None, customer_ids=None, fixed_updated_at=None):
        con, rng = self.con, self.rng
        next_id = con.execute("select coalesce(max(order_id), 1000) + 1 from raw.orders").fetchone()[0]
        prices = self.product_prices()
        pids = sorted(prices)
        cust_pool = customer_ids or self.active_customer_ids()
        lt = load_ts(self.day)
        channel_col = self.has_channel()
        ids = []
        for i in range(n):
            oid = next_id + i
            cid = cust_pool[i] if customer_ids else rng.choice(cust_pool)
            total = 0
            for line_no in range(1, rng.randint(1, 3) + 1):
                pid = rng.choice(pids)
                qty = rng.randint(1, 3)
                price = prices[pid]
                total += qty * price
                con.execute(
                    "insert into raw.order_items values (?, ?, ?, ?, ?, ?)",
                    [oid, line_no, pid, qty, price, lt],
                )
            upd = fixed_updated_at or at(order_date, updated_at_hour or rng.randint(8, 21), rng.randint(0, 59))
            if channel_col:
                con.execute(
                    "insert into raw.orders values (?, ?, ?, ?, ?, ?, ?, ?)",
                    [oid, cid, order_date, status, total, upd, lt, rng.choice(["web", "app"])],
                )
            else:
                con.execute(
                    "insert into raw.orders values (?, ?, ?, ?, ?, ?, ?)",
                    [oid, cid, order_date, status, total, upd, lt],
                )
            ids.append(oid)
        return ids

    def progress_statuses(self):
        """Đơn 'placed' từ hôm trước → 'shipped'; 'shipped' đủ 3 ngày → 'delivered'."""
        bd = business_date(self.day)
        lt = load_ts(self.day)
        n1 = self.con.execute(
            """update raw.orders set status = 'shipped', updated_at = ?, _loaded_at = ?
               where status = 'placed' and order_date <= ?""",
            [at(bd, 16), lt, bd - timedelta(days=1)],
        ).fetchone()[0]
        n2 = self.con.execute(
            """update raw.orders set status = 'delivered', updated_at = ?, _loaded_at = ?
               where status = 'shipped' and order_date <= ?""",
            [at(bd, 17), lt, bd - timedelta(days=3)],
        ).fetchone()[0]
        self.log(f"Cập nhật trạng thái: {n1} đơn placed→shipped, {n2} đơn shipped→delivered (updated_at và _loaded_at đều đổi)")

    # ---- events
    def new_events(self, event_date, n, prefix, start=0):
        lt = load_ts(self.day)
        rows = []
        for i in range(start, start + n):
            ts = at(event_date, 0) + timedelta(seconds=self.rng.randint(0, 86399))
            rows.append([f"{prefix}{i:03d}", self.rng.randint(1, 11), self.rng.choice(EVENT_TYPES), ts, lt])
        self.con.executemany("insert into raw.events values (?, ?, ?, ?, ?)", rows)

    def redeliver_events(self, event_ids):
        """Công cụ ingest gửi lại (at-least-once): cùng event_id, cùng event_ts, _loaded_at mới."""
        lt = load_ts(self.day)
        placeholders = ", ".join("?" for _ in event_ids)
        self.con.execute(
            f"""insert into raw.events
                select event_id, user_id, event_type, event_ts, ?
                from raw.events where event_id in ({placeholders})""",
            [lt] + list(event_ids),
        )


# --------------------------------------------------------------------------- days

def day_0(s: Sim):
    for cid, name, email, city, tier in CUSTOMERS:
        s.insert_customer(cid, name, email, city, tier, datetime(2025, 12, 1, 8) + timedelta(hours=cid))
    s.con.executemany(
        "insert into raw.products values (?, ?, ?, ?, ?)",
        [list(p) + [load_ts(0)] for p in PRODUCTS],
    )
    for offset in range(5):  # 27/12 → 31/12
        d = date(2025, 12, 27) + timedelta(days=offset)
        status = "delivered" if d <= date(2025, 12, 28) else ("shipped" if d <= date(2025, 12, 30) else "placed")
        s.new_orders(d, 6, status)
    start = 0
    for offset in range(3):  # sự kiện 29/12 → 31/12
        s.new_events(date(2025, 12, 29) + timedelta(days=offset), 30, "ev_00_", start)
        start += 30
    s.log("Nạp ban đầu: 10 khách hàng, 8 sản phẩm, 30 đơn (27–31/12/2025), 90 sự kiện (29–31/12/2025)")


def day_1(s: Sim):
    bd = business_date(1)
    s.progress_statuses()
    s.update_customer(3, at(bd, 10), city="Da Nang")
    s.log("Khách 3 chuyển Ha Noi → Da Nang lúc 2026-01-01 10:00 (updated_at được cập nhật)")
    s.update_product(2, list_price_cents=7499)
    s.log("Sản phẩm 2 giảm giá 8999 → 7499 (bảng products KHÔNG có updated_at)")
    s.new_orders(bd, 6, "placed")
    s.new_events(bd, 30, "ev_01_")
    s.log(f"6 đơn mới ngày {bd}, 30 sự kiện mới")


def day_2(s: Sim):
    bd = business_date(2)
    s.progress_statuses()
    s.update_customer(2, at(bd, 9), email="binh.tran@newmail.com")
    s.log("Khách 2 đổi email (updated_at được cập nhật; city/tier không đổi)")
    s.new_orders(bd, 5, "placed")
    late = s.new_orders(date(2025, 12, 28), 3, "delivered", updated_at_hour=14)
    s.log(f"DỮ LIỆU ĐẾN MUỘN: 3 đơn {late} có order_date = 2025-12-28, updated_at = 2025-12-28 14:xx, "
          f"nhưng _loaded_at = {load_ts(2)}; trạng thái delivered nên sẽ không bao giờ được cập nhật nữa")
    oid = s.new_orders(bd, 1, "placed", customer_ids=[11])
    s.log(f"LATE-ARRIVING DIMENSION: đơn {oid} của khách 11, nhưng khách 11 chưa có trong raw.customers")
    s.new_events(bd, 30, "ev_02_")
    s.redeliver_events([f"ev_01_{i:03d}" for i in range(5)])
    s.log("30 sự kiện mới + GỬI LẠI 5 sự kiện ev_01_000..004 (trùng event_id, _loaded_at mới)")


def day_3(s: Sim):
    bd = business_date(3)
    s.progress_statuses()
    s.insert_customer(11, "Ly Van Minh", "minh.ly@mail.com", "Can Tho", "bronze", datetime(2026, 1, 1, 20))
    s.log("Khách 11 xuất hiện (updated_at = 2026-01-01 20:00, tức là đăng ký TRƯỚC đơn ngày 2026-01-02)")
    s.update_customer(5, at(bd, 9), bump_updated_at=False, tier="gold")
    s.log("Khách 5 lên hạng silver → gold, NHƯNG nguồn QUÊN cập nhật updated_at (changelog vẫn ghi đúng)")
    s.delete_customer(7, at(bd, 12))
    s.log("Khách 7 bị XOÁ CỨNG khỏi raw.customers (hard delete)")
    s.update_product(5, category="Electronics")
    s.log("Sản phẩm 5 đổi category Accessories → Electronics")
    s.new_orders(bd, 6, "placed")
    s.new_events(bd, 30, "ev_03_")
    s.new_events(business_date(1), 6, "ev_03_L")
    s.log("30 sự kiện mới + 6 sự kiện ĐẾN MUỘN ev_03_L000..005 có event_ts ngày 2026-01-01")


def day_4(s: Sim):
    bd = business_date(4)
    # DuckDB: ALTER phải đứng trước mọi UPDATE trên cùng bảng trong 1 transaction
    s.con.execute("alter table raw.orders add column channel varchar")
    s.log("THAY ĐỔI SCHEMA: raw.orders thêm cột channel (đơn cũ = null, đơn mới = web/app)")
    s.progress_statuses()
    cancelled = [r[0] for r in s.con.execute(
        "select order_id from raw.orders where order_date = ? and status <> 'cancelled' order by order_id limit 2",
        [business_date(3)],
    ).fetchall()]
    s.con.execute(
        f"update raw.orders set status = 'cancelled', updated_at = ?, _loaded_at = ? "
        f"where order_id in ({', '.join(str(c) for c in cancelled)})",
        [at(bd, 11), load_ts(4)],
    )
    s.log(f"Huỷ 2 đơn {cancelled} của ngày {business_date(3)} → doanh thu ngày đó phải giảm")
    s.update_customer(3, at(bd, 10), city="Ho Chi Minh")
    s.log("Khách 3 chuyển tiếp Da Nang → Ho Chi Minh lúc 2026-01-04 10:00")
    s.new_orders(bd, 6, "placed")
    s.new_events(bd, 30, "ev_04_")
    s.log(f"6 đơn mới ngày {bd} (có channel), 30 sự kiện mới")


def day_5(s: Sim):
    bd = business_date(5)
    s.progress_statuses()
    s.update_customer(8, at(bd, 15), tier="silver")
    s.log("Khách 8 lên hạng bronze → silver")
    s.update_product(2, list_price_cents=8999)
    s.log("Sản phẩm 2 tăng giá trở lại 7499 → 8999")
    s.con.execute("insert into raw.products values (9, 'Smart Watch', 'Electronics', 19999, ?)", [load_ts(5)])
    s.log("Sản phẩm mới 9: Smart Watch")
    s.new_orders(bd, 6, "placed")
    late = s.new_orders(business_date(1), 2, "delivered", updated_at_hour=13)
    s.log(f"DỮ LIỆU ĐẾN MUỘN: 2 đơn {late} có order_date = {business_date(1)} (trễ 4 ngày), trạng thái delivered")
    s.new_events(bd, 30, "ev_05_")
    s.redeliver_events([f"ev_04_{i:03d}" for i in range(10, 14)])
    s.log("30 sự kiện mới + GỬI LẠI 4 sự kiện ev_04_010..013")


DAYS = [day_0, day_1, day_2, day_3, day_4, day_5]


# --------------------------------------------------------------------------- CLI

def connect():
    try:
        return duckdb.connect(str(DB_PATH))
    except duckdb.IOException as e:
        sys.exit(f"Không mở được {DB_PATH}: {e}\n→ Đóng DBeaver / duckdb CLI / tiến trình dbt khác đang giữ file rồi thử lại.")


def current_day(con):
    try:
        row = con.execute("select current_day from raw._lab_state").fetchone()
        return row[0] if row else None
    except duckdb.CatalogException:
        return None


def apply_day(con, day):
    s = Sim(con, day)
    con.execute("begin")
    DAYS[day](s)
    con.execute("delete from raw._lab_state")
    con.execute("insert into raw._lab_state values (?, ?)", [day, datetime.now()])
    con.execute("commit")
    print(f"=== Đã chuyển sang NGÀY {day} (_loaded_at = {load_ts(day)}) ===")
    for (msg,) in con.execute("select message from raw._lab_log where day = ? order by seq", [day]).fetchall():
        print(f"  • {msg}")


def wipe_database():
    """Xoá hẳn file DuckDB: mất cả raw lẫn mọi model/snapshot dbt đã build → làm lại sạch từ đầu."""
    for f in (DB_PATH, DB_PATH.with_name(DB_PATH.name + ".wal")):
        f.unlink(missing_ok=True)


def reset(con):
    con.execute(DDL)
    apply_day(con, 0)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"reset", "next", "status", "goto"}:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd in {"reset", "goto"}:
        wipe_database()
    con = connect()
    try:
        if cmd == "reset":
            reset(con)
            print("\n(Đã xoá toàn bộ lab.duckdb: mọi model/snapshot dbt cũ cũng mất, build lại từ đầu.)")
        elif cmd == "next":
            day = current_day(con)
            if day is None:
                sys.exit("Chưa có dữ liệu. Chạy: python scripts/simulate.py reset")
            if day >= MAX_DAY:
                sys.exit(f"Đã ở ngày cuối ({MAX_DAY}). Muốn làm lại: python scripts/simulate.py reset")
            apply_day(con, day + 1)
        elif cmd == "goto":
            target = int(sys.argv[2])
            if not 0 <= target <= MAX_DAY:
                sys.exit(f"N phải trong khoảng 0..{MAX_DAY}")
            reset(con)
            for d in range(1, target + 1):
                apply_day(con, d)
            print("\n⚠️  Đã nhảy nhiều ngày một lúc: snapshot/SCD2 chạy sau lệnh này sẽ KHÔNG thấy trạng thái các ngày ở giữa.")
        elif cmd == "status":
            day = current_day(con)
            if day is None:
                print("Chưa có dữ liệu. Chạy: python scripts/simulate.py reset")
                return
            print(f"Đang ở NGÀY {day}/{MAX_DAY}. Các sự kiện đã xảy ra:")
            for d, msg in con.execute("select day, message from raw._lab_log order by day, seq").fetchall():
                print(f"  [ngày {d}] {msg}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
