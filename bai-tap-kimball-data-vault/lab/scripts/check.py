#!/usr/bin/env python3
"""Tự chấm lab Kimball + Data Vault. Chạy từ thư mục lab/ SAU KHI đã `dbt build`.

  python scripts/check.py            # chấm tất cả
  python scripts/check.py K4 V2      # chỉ chấm vài bài

Kết quả:  ✅ PASS   ❌ FAIL   ⏭️  SKIP (chưa làm / chưa tới ngày cần thiết)
Đáp án chuẩn được tính TRỰC TIẾP từ dữ liệu nguồn bằng Python, không phụ thuộc code của bạn.
"""
import hashlib
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb
import yaml

LAB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LAB_DIR / "lab.duckdb"
D0 = date(2026, 3, 1)
LOW, HIGH = datetime(1900, 1, 1), datetime(9999, 12, 31)
SYSTEM_SCHEMAS = {"crm", "shop", "pos", "wms", "erp", "_lab", "information_schema", "pg_catalog", "main"}

PASS, FAIL, SKIP = "✅ PASS", "❌ FAIL", "⏭️  SKIP"


class Skip(Exception):
    pass


class Fail(Exception):
    pass


con: duckdb.DuckDBPyConnection
DAY: int
BDATE: date


# =========================================================================== tiện ích

def q(sql, params=None):
    return con.execute(sql, params or []).fetchall()


def q1(sql, params=None):
    return con.execute(sql, params or []).fetchone()[0]


def find(name):
    rows = q("""select table_schema from information_schema.tables
                where table_name = ? and table_schema not in ('crm','shop','pos','wms','erp','_lab')
                order by table_schema like 'dev%' desc, table_schema""", [name])
    if not rows:
        raise Skip(f"chưa thấy bảng/view `{name}` (chưa viết hoặc chưa build?)")
    return f'"{rows[0][0]}"."{name}"'


def exists(name):
    try:
        find(name)
        return True
    except Skip:
        return False


def columns(rel):
    schema, table = [p.strip('"') for p in rel.split(".")]
    return [r[0].lower() for r in q(
        "select column_name from information_schema.columns where table_schema = ? and table_name = ?", [schema, table])]


def need_cols(rel, cols):
    have = columns(rel)
    missing = [c for c in cols if c.lower() not in have]
    if missing:
        raise Fail(f"{rel} thiếu cột {missing} (đang có: {have})")


def need_day(n, why):
    if DAY < n:
        raise Skip(f"cần tới ngày {n} ({why}); hiện ở ngày {DAY}")


def dkey(d):
    if d is None:
        return -1
    if isinstance(d, datetime):
        d = d.date()
    return d.year * 10000 + d.month * 100 + d.day


def norm(v):
    """Chuẩn hoá để so sánh: Decimal/float → số, chuỗi → strip."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str):
        return v.strip()
    return v


def rnd(x: Decimal) -> int:
    return int(x.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def diff_report(expected: dict, actual: dict, label, fmt=lambda k, v: f"{k}: {v}", limit=4):
    """So 2 dict {khoá: giá trị}. Raise Fail với mô tả ngắn gọn các khác biệt."""
    missing = [k for k in expected if k not in actual]
    extra = [k for k in actual if k not in expected]
    wrong = [k for k in expected if k in actual and expected[k] != actual[k]]
    if not (missing or extra or wrong):
        return
    parts = []
    if missing:
        parts.append(f"thiếu {len(missing)} {label}, vd {sorted(missing, key=str)[:limit]}")
    if extra:
        parts.append(f"thừa {len(extra)} {label}, vd {sorted(extra, key=str)[:limit]}")
    if wrong:
        ex = sorted(wrong, key=str)[:limit]
        parts.append(f"sai {len(wrong)} {label}: " + "; ".join(f"{k} có {actual[k]} cần {expected[k]}" for k in ex))
    raise Fail(" | ".join(parts))


def dv_hash(*parts):
    """Hash key kiểu automate_dv (shim DuckDB): UPPER(MD5(chuỗi chuẩn hoá))."""
    if len(parts) == 1:
        s = str(parts[0]).strip().upper()
    else:
        s = "||".join((str(p).strip().upper() if p is not None and str(p).strip() != "" else "^^") for p in parts)
    return hashlib.md5(s.encode()).hexdigest().upper()


# =========================================================================== đáp án chuẩn (tính từ nguồn)

def crm_rows():
    return q("""select upper(trim(customer_code)), _extract_date, trim(full_name), nullif(lower(trim(email)), ''),
                       trim(city), trim(loyalty_tier), _loaded_at
                from crm.customers order by 1, 2""")


def truth_customers():
    """dim_customer chuẩn: {(code, valid_from): dict}. Theo dõi city/tier; Type 1 tên + email; inferred; '-1'."""
    rows = crm_rows()
    by_code = defaultdict(list)
    for code, d, name, email, city, tier, _lt in rows:
        by_code[code].append((d, name, email, city, tier))
    out = {}
    for code, files in by_code.items():
        latest_name, latest_email = files[-1][1], files[-1][2]
        versions = []
        for i, (d, _n, _e, city, tier) in enumerate(files):
            if i == 0 or (city, tier) != versions[-1][1:]:
                versions.append((LOW if i == 0 else datetime.combine(d, datetime.min.time()), city, tier))
        for i, (vf, city, tier) in enumerate(versions):
            vt = versions[i + 1][0] if i + 1 < len(versions) else HIGH
            out[(code, vf)] = dict(full_name=latest_name, email=latest_email, city=city, loyalty_tier=tier,
                                   valid_to=vt, is_current=vt == HIGH, is_inferred=False)
    seen = {r[0] for r in q("select distinct upper(trim(customer_code)) from shop.orders")}
    seen |= {r[0] for r in q("select distinct nullif(upper(trim(customer_code)), '') from pos.sales") if r[0]}
    for code in seen - set(by_code):
        out[(code, LOW)] = dict(full_name="Chưa xác định", email=None, city="Chưa xác định",
                                loyalty_tier="Chưa xác định", valid_to=HIGH, is_current=True, is_inferred=True)
    return out


def customer_at(truth, code, ts):
    """(valid_from, city, tier) của phiên bản khách hiệu lực tại ts."""
    if code is None:
        return None
    for (c, vf), v in truth.items():
        if c == code and vf <= ts < v["valid_to"]:
            return vf, v["city"], v["loyalty_tier"]
    return None


def shop_orders():
    return {r[0]: dict(zip(["customer_code", "channel", "payment_method", "is_gift", "shipping_fee", "total_amount",
                             "status", "order_ts", "paid_at", "cancelled_at"], r[1:]))
            for r in q("""select upper(trim(order_number)), upper(trim(customer_code)), lower(channel),
                                 lower(payment_method), is_gift, shipping_fee, total_amount, lower(status), order_ts,
                                 paid_at, cancelled_at from shop.orders""")}


def products_now():
    return {r[0]: dict(product_name=r[1], brand=r[2], category_code=r[3], list_price=r[4])
            for r in q("select upper(trim(sku)), trim(product_name), trim(brand), upper(trim(category_code)), list_price "
                       "from erp.products")}


def categories():
    return {r[0]: dict(name=r[1], parent=r[2])
            for r in q("select upper(trim(category_code)), trim(category_name), upper(trim(parent_code)) from erp.categories")}


def category_info():
    cats = categories()
    info = {}
    for code in cats:
        path, cur = [], code
        while cur:
            path.append(cur)
            cur = cats[cur]["parent"]
        l1 = path[-1]
        info[code] = dict(level=len(path), l1=l1, l1_name=cats[l1]["name"], ancestors=path)
    return info


def truth_sales_lines():
    """Mọi dòng bán (đơn online không huỷ + POS) kèm phân bổ voucher/phí ship. Khoá (order_number, line_no)."""
    orders = shop_orders()
    disc = defaultdict(int)
    for o, amt in q("select upper(trim(order_number)), discount_amount from shop.order_vouchers"):
        disc[o] += amt
    lines = defaultdict(list)
    for o, ln, sku, qty, price in q("select upper(trim(order_number)), line_no, upper(trim(sku)), quantity, unit_price "
                                    "from shop.order_lines"):
        h = orders[o]
        if h["status"] == "cancelled":
            continue
        lines[o].append(dict(source_system="shop", order_number=o, line_no=ln, sku=sku, quantity=qty, unit_price=price,
                             order_ts=h["order_ts"], customer_code=h["customer_code"], channel=h["channel"],
                             payment_method=h["payment_method"], is_gift=h["is_gift"], store_code=None,
                             order_discount_total=disc[o], shipping_fee=h["shipping_fee"]))
    for r in q("""select upper(trim(receipt_no)), upper(trim(store_code)), nullif(upper(trim(customer_code)), ''),
                         lower(payment_method), sale_ts, line_no, upper(trim(sku)), quantity, unit_price from pos.sales"""):
        rec, store, cust, pay, ts, ln, sku, qty, price = r
        lines[rec].append(dict(source_system="pos", order_number=rec, line_no=ln, sku=sku, quantity=qty, unit_price=price,
                               order_ts=ts, customer_code=cust, channel="store", payment_method=pay, is_gift=False,
                               store_code=store, order_discount_total=0, shipping_fee=0))
    out = {}
    for o, ls in lines.items():
        ls.sort(key=lambda x: x["line_no"])
        gross_total = sum(x["quantity"] * x["unit_price"] for x in ls)
        dsum = ssum = 0
        for i, x in enumerate(ls):
            gross = x["quantity"] * x["unit_price"]
            if i < len(ls) - 1:
                d = rnd(Decimal(x["order_discount_total"]) * gross / gross_total)
                s = rnd(Decimal(x["shipping_fee"]) * gross / gross_total)
                dsum, ssum = dsum + d, ssum + s
            else:
                d, s = x["order_discount_total"] - dsum, x["shipping_fee"] - ssum
            out[(o, x["line_no"])] = dict(x, gross_amount=gross, discount_allocated=d, shipping_fee_allocated=s,
                                          net_amount=gross - d + s)
    return out


def truth_fulfillment():
    orders = shop_orders()
    ev = defaultdict(lambda: defaultdict(list))
    wh = {}
    for o, t, ts, w in q("select upper(trim(order_number)), lower(event_type), event_ts, upper(warehouse_code) "
                         "from wms.shipment_events"):
        ev[o][t].append(ts)
        wh[o] = w
    qty = dict(q("select upper(trim(order_number)), sum(quantity) from shop.order_lines group by 1"))
    out = {}
    for o, h in orders.items():
        e = ev[o]
        first = {t: min(e[t]) if e[t] else None for t in ("packed", "shipped", "delivered", "returned")}
        if h["cancelled_at"]:
            status = "cancelled"
        elif first["returned"]:
            status = "returned"
        elif first["delivered"]:
            status = "delivered"
        elif first["shipped"]:
            status = "shipped"
        elif first["packed"]:
            status = "packed"
        elif h["paid_at"]:
            status = "paid"
        else:
            status = "placed"
        od = h["order_ts"].date()
        out[o] = dict(
            order_date_key=dkey(h["order_ts"]), paid_date_key=dkey(h["paid_at"]), packed_date_key=dkey(first["packed"]),
            shipped_date_key=dkey(first["shipped"]), delivered_date_key=dkey(first["delivered"]),
            returned_date_key=dkey(first["returned"]), cancelled_date_key=dkey(h["cancelled_at"]),
            current_status=status, order_total_amount=h["total_amount"], item_quantity=qty.get(o),
            failed_delivery_count=len(e["delivery_failed"]),
            days_to_ship=(first["shipped"].date() - od).days if first["shipped"] else None,
            days_to_deliver=(first["delivered"].date() - od).days if first["delivered"] else None,
            warehouse_code=wh.get(o, "-1"), customer_code=h["customer_code"], order_ts=h["order_ts"],
        )
    return out


def truth_inventory():
    mv = q("select upper(trim(sku)), upper(warehouse_code), movement_date, qty_change from wms.stock_movements")
    start = min(r[2] for r in mv)
    skus = [r[0] for r in q("select upper(trim(sku)) from erp.products")]
    whs = [r[0] for r in q("select upper(location_code) from erp.locations where lower(location_type) = 'warehouse'")]
    daily = defaultdict(lambda: [0, 0])
    for sku, w, d, qch in mv:
        daily[(sku, w, d)][0 if qch > 0 else 1] += abs(qch)
    out = {}
    for sku in skus:
        for w in whs:
            on_hand, d = 0, start
            while d <= BDATE:
                qin, qout = daily.get((sku, w, d), (0, 0))
                on_hand += qin - qout
                out[(dkey(d), sku, w)] = (on_hand, qin, qout)
                d += timedelta(days=1)
    return out


def truth_coverage():
    out = set()
    for code, sku, s, e in q("select upper(trim(promo_code)), upper(trim(sku)), start_date, end_date from erp.promotions"):
        d = s
        while d <= e:
            out.add((dkey(d), sku, code))
            d += timedelta(days=1)
    return out


def truth_voucher_bridge(lines):
    sold = {k[0] for k in lines}
    by_order = defaultdict(list)
    for o, v, amt in q("select upper(trim(order_number)), upper(trim(voucher_code)), discount_amount from shop.order_vouchers"):
        if o in sold:
            by_order[o].append((v, amt))
    out = {}
    for o in sold:
        vs = by_order.get(o)
        if not vs:
            out[(o, "KHONG_VOUCHER")] = 1.0
            continue
        total = sum(a for _, a in vs)
        for v, a in vs:
            out[(o, v)] = a / total
    return out


# =========================================================================== truy vấn bài làm

def fact_lines(rel):
    """Đọc fct_sales (hoặc fct_sales_dv) và giải nghĩa khoá qua các dimension của chính bài làm."""
    dim_c = find("dim_customer_dv") if rel.endswith('"fct_sales_dv"') else find("dim_customer")
    rows = q(f"""
        select f.order_number, f.line_no, f.source_system, f.order_date_key, f.quantity, f.unit_price, f.gross_amount,
               f.discount_allocated, f.shipping_fee_allocated, f.net_amount,
               c.customer_code, c.city, c.loyalty_tier, cast(c.valid_from as timestamp), f.customer_key,
               f.product_key, f.order_profile_key, f.store_location_key
        from {rel} f left join {dim_c} c on c.customer_key = f.customer_key""")
    return {(r[0], r[1]): r for r in rows}


def check_lines_against_truth(rel, truth_lines, truth_c):
    need_cols(rel, ["order_date_key", "customer_key", "product_key", "order_profile_key", "store_location_key",
                    "source_system", "order_number", "line_no", "order_ts", "quantity", "unit_price", "gross_amount",
                    "discount_allocated", "shipping_fee_allocated", "net_amount"])
    got = fact_lines(rel)
    exp_amounts = {k: (v["order_date_key"] if "order_date_key" in v else dkey(v["order_ts"]), v["quantity"],
                       v["unit_price"], v["gross_amount"], v["discount_allocated"], v["shipping_fee_allocated"],
                       v["net_amount"]) for k, v in truth_lines.items()}
    act_amounts = {k: (r[3], r[4], norm(r[5]), norm(r[6]), norm(r[7]), norm(r[8]), norm(r[9])) for k, r in got.items()}
    exp_amounts = {k: tuple(norm(x) for x in v) for k, v in exp_amounts.items()}
    diff_report(exp_amounts, act_amounts, "dòng (order_number, line_no)",
                limit=3) if set(exp_amounts) != set(act_amounts) else None
    wrong = [k for k in exp_amounts if exp_amounts[k] != act_amounts[k]]
    if wrong:
        k = sorted(wrong)[0]
        raise Fail(f"{len(wrong)} dòng sai số liệu, vd {k}: (date_key, qty, unit_price, gross, discount, ship, net) = "
                   f"{act_amounts[k]}, cần {exp_amounts[k]}. Xem lại cách phân bổ: theo tỷ trọng gross_amount, làm tròn "
                   f"tới đồng, dòng có line_no lớn nhất nhận phần dư.")
    bad_c = []
    for k, v in truth_lines.items():
        r = got[k]
        want = customer_at(truth_c, v["customer_code"], v["order_ts"])
        if want is None:
            if r[10] != "-1":
                bad_c.append((k, r[10], "-1 (khách vãng lai)"))
            continue
        if (r[10], r[13], r[11], r[12]) != (v["customer_code"], want[0], want[1], want[2]):
            fmt = lambda d: d.strftime("%Y-%m-%d") if d else None
            bad_c.append((k, f"{r[10]}/{r[11]}/{r[12]}/từ {fmt(r[13])}",
                          f"{v['customer_code']}/{want[1]}/{want[2]}/từ {fmt(want[0])}"))
    if bad_c:
        ex = bad_c[:3]
        raise Fail(f"{len(bad_c)} dòng trỏ sai phiên bản khách (khách/thành phố/hạng/hiệu lực từ): "
                   + "; ".join(f"{k} có {a} cần {b}" for k, a, b in ex)
                   + ". Join theo khoảng hiệu lực: valid_from <= order_ts < valid_to.")
    return got


def resolve_dim(rel_dim, key_col, attr_cols):
    cols = ", ".join(attr_cols)
    return {r[0]: (r[1:] if len(r) > 2 else r[1]) for r in q(f"select {key_col}, {cols} from {rel_dim}")}


# =========================================================================== KIMBALL

def check_K2():
    rel, rm = find("dim_date"), find("dim_month")
    need_cols(rel, ["date_key", "full_date", "day_of_week", "day_name_vi", "is_weekend", "month_key", "month_number",
                    "month_name_vi", "quarter_number", "year_number", "month_start_date"])
    n = q1(f"select count(*) from {rel} where date_key <> -1")
    if n != 365:
        raise Fail(f"dim_date có {n} ngày thật, cần đủ 365 ngày của năm 2026")
    if q1(f"select count(*) - count(distinct date_key) from {rel}"):
        raise Fail("date_key bị trùng")
    if not q1(f"select count(*) from {rel} where date_key = -1"):
        raise Fail("thiếu dòng date_key = -1 ('Chưa xảy ra') cho các mốc chưa tới")
    r = q(f"""select day_of_week, is_weekend, month_key, quarter_number, day_name_vi
              from {rel} where full_date = date '2026-03-01'""")
    if not r or tuple(r[0][:4]) != (7, True, 202603, 1):
        raise Fail(f"01/03/2026 (Chủ Nhật) sai thuộc tính: (day_of_week, is_weekend, month_key, quarter) = "
                   f"{r[0][:4] if r else None}, cần (7, True, 202603, 1). Dùng isodow() (Thứ Hai = 1).")
    need_cols(rm, ["month_key", "month_start_date", "month_number", "month_name_vi", "quarter_number", "year_number"])
    if q1(f"select count(*) from {rm}") != 12:
        raise Fail("dim_month phải có đúng 12 tháng của 2026")
    bad = q1(f"""select count(*) from {rm} m where not exists (
                   select 1 from {rel} d where d.month_key = m.month_key and d.month_start_date = m.month_start_date
                   and d.month_number = m.month_number and d.month_name_vi = m.month_name_vi
                   and d.quarter_number = m.quarter_number and d.year_number = m.year_number)""")
    if bad:
        raise Fail(f"{bad} tháng trong dim_month có thuộc tính khác dim_date → không 'conformed', drill-across sẽ lệch")
    return "dim_date 365 ngày + dòng -1; dim_month conformed với dim_date"


def check_K3():
    rel = find("dim_product")
    need_cols(rel, ["product_key", "sku", "product_name", "brand", "list_price", "category_code", "category_name",
                    "category_l1_code", "category_l1_name"])
    info, cats = category_info(), categories()
    exp = {sku: (p["product_name"], p["brand"], p["list_price"], p["category_code"], cats[p["category_code"]]["name"],
                 info[p["category_code"]]["l1"], info[p["category_code"]]["l1_name"])
           for sku, p in products_now().items()}
    got = {r[0]: tuple(norm(x) for x in r[1:]) for r in q(
        f"""select sku, product_name, brand, list_price, category_code, category_name, category_l1_code, category_l1_name
            from {rel} where product_key <> '-1'""")}
    diff_report(exp, got, "sản phẩm")
    if not q1(f"select count(*) from {rel} where product_key = '-1'"):
        raise Fail("dim_product thiếu thành viên '-1' (Không xác định)")
    if q1(f"select count(*) - count(distinct product_key) from {rel}"):
        raise Fail("product_key bị trùng")
    rl = find("dim_location")
    need_cols(rl, ["location_key", "location_code", "location_name", "location_type", "city"])
    keys = {r[0] for r in q(f"select location_key from {rl}")}
    if not {"-1", "-2"} <= keys or len(keys) != 6:
        raise Fail(f"dim_location cần 4 địa điểm + '-1' (không xác định) + '-2' (không áp dụng); đang có {len(keys)} dòng")
    rv = find("dim_voucher")
    need_cols(rv, ["voucher_key", "voucher_code", "voucher_type", "voucher_name"])
    if q1(f"select count(*) from {rv} where voucher_key = '-2' and voucher_code = 'KHONG_VOUCHER'") != 1:
        raise Fail("dim_voucher cần thành viên voucher_key '-2', voucher_code 'KHONG_VOUCHER' cho đơn không dùng voucher")
    rp = find("dim_promotion")
    need_cols(rp, ["promotion_key", "promo_code", "promo_name", "discount_pct", "start_date", "end_date"])
    exp_p = {r[0]: (r[1], r[2]) for r in q("select upper(trim(promo_code)), min(start_date), max(end_date) "
                                           "from erp.promotions group by 1")}
    got_p = {r[0]: (r[1], r[2]) for r in q(f"select promo_code, start_date, end_date from {rp}")}
    diff_report(exp_p, got_p, "chương trình KM (1 dòng / promo_code)")
    rc = find("dim_category_l1")
    need_cols(rc, ["category_l1_key", "category_l1_code", "category_l1_name"])
    got_c = {r[0]: r[1] for r in q(f"select category_l1_code, category_l1_name from {rc}")}
    exp_c = {c: v["name"] for c, v in cats.items() if v["parent"] is None}
    diff_report(exp_c, got_c, "danh mục cấp 1")
    sku07 = got.get("SKU07")
    return f"dim Type 1 đúng (SKU07 đang ở {sku07[3] if sku07 else '?'}), có đủ thành viên đặc biệt"


def check_K4():
    rel = find("dim_customer")
    need_cols(rel, ["customer_key", "customer_code", "full_name", "email", "city", "loyalty_tier", "valid_from",
                    "valid_to", "is_current", "is_inferred"])
    truth = truth_customers()
    exp = {(c, vf): (v["full_name"], v["email"], v["city"], v["loyalty_tier"], v["valid_to"], v["is_current"],
                     v["is_inferred"]) for (c, vf), v in truth.items()}
    got = {}
    for r in q(f"""select customer_code, cast(valid_from as timestamp), full_name, email, city, loyalty_tier,
                          cast(valid_to as timestamp), is_current, is_inferred
                   from {rel} where customer_code <> '-1'"""):
        got[(r[0], r[1])] = tuple(norm(x) for x in r[2:])
    exp = {k: tuple(norm(x) for x in v) for k, v in exp.items()}
    diff_report(exp, got, "phiên bản (customer_code, valid_from)", limit=3)
    if q1(f"select count(*) from {rel} where customer_key = '-1' and customer_code = '-1'") != 1:
        raise Fail("thiếu dòng unknown member: customer_key = '-1', customer_code = '-1'")
    bad = q1(f"""select count(*) from {rel} where customer_key <> '-1' and customer_key <>
                 md5(cast(customer_code as varchar) || '-' || cast(valid_from as varchar))""")
    if bad:
        raise Fail(f"{bad} dòng có customer_key không phải dbt_utils.generate_surrogate_key(['customer_code', 'valid_from'])"
                   " → khoá của inferred member sẽ không ổn định khi khách thật tới")
    n5 = sum(1 for (c, _vf) in exp if c == "C005")
    return f"{len(exp)} phiên bản đúng (C005 có {n5} phiên bản), khoá ổn định theo (customer_code, valid_from)"


def check_K5():
    rp = find("dim_order_profile")
    need_cols(rp, ["order_profile_key", "channel", "payment_method", "is_gift"])
    if q1(f"select count(*) - count(distinct (channel, payment_method, is_gift)) from {rp}"):
        raise Fail("dim_order_profile có tổ hợp (channel, payment_method, is_gift) bị lặp")
    rel = find("fct_sales")
    truth_c, lines = truth_customers(), truth_sales_lines()
    got = check_lines_against_truth(rel, lines, truth_c)
    prof = resolve_dim(rp, "order_profile_key", ["channel", "payment_method", "is_gift"])
    prod = resolve_dim(find("dim_product"), "product_key", ["sku"])
    loc = resolve_dim(find("dim_location"), "location_key", ["location_code"])
    for k, v in lines.items():
        r = got[k]
        if prod.get(r[15]) != v["sku"]:
            raise Fail(f"dòng {k}: product_key trỏ tới {prod.get(r[15])}, cần {v['sku']}")
        p = prof.get(r[16])
        if p is None or tuple(p) != (v["channel"], v["payment_method"], v["is_gift"]):
            raise Fail(f"dòng {k}: order_profile_key trỏ tới {p}, cần {(v['channel'], v['payment_method'], v['is_gift'])}")
        want_store = v["store_code"] or "-2"
        if loc.get(r[17]) != want_store:
            raise Fail(f"dòng {k}: store_location_key trỏ tới {loc.get(r[17])}, cần {want_store}")
    if q1(f"select count(*) from {rel} where order_number = 'W0013'") and DAY >= 3:
        raise Fail("đơn W0013 đã huỷ (ngày 3) mà vẫn có trong fct_sales")
    total = sum(v["net_amount"] for v in lines.values())
    return f"{len(lines)} dòng đúng grain, phân bổ khớp đầu đơn, tổng net_amount = {total:,}đ"


def check_K6():
    need_day(2, "khách C013 mua online từ ngày 2 khi CRM chưa có")
    rel, rf = find("dim_customer"), find("fct_sales")
    need_cols(rel, ["is_inferred"])
    rows = q(f"""select cast(valid_from as timestamp), is_inferred, city, customer_key
                 from {rel} where customer_code = 'C013' order by valid_from""")
    if not rows:
        raise Fail("dim_customer không có C013 → đơn W0015 sẽ rơi vào '-1' hoặc mất khi inner join")
    w15 = q(f"select distinct customer_key from {rf} where order_number = 'W0015'")
    if not w15:
        raise Fail("fct_sales không có đơn W0015")
    if DAY == 2:
        if not (len(rows) == 1 and rows[0][1] is True and rows[0][0] == LOW):
            raise Fail(f"ngày 2: C013 phải là 1 dòng inferred (is_inferred = true, valid_from 1900-01-01), đang có {rows}")
        if w15[0][0] != rows[0][3]:
            raise Fail("ngày 2: W0015 chưa trỏ vào dòng inferred của C013")
        return "ngày 2: C013 là inferred member, W0015 đã gắn vào. Sang ngày 3 chấm lại!"
    first = rows[0]
    if first[1] or first[0] != LOW or first[2] != "Ho Chi Minh":
        raise Fail(f"từ ngày 3: phiên bản đầu của C013 phải là dữ liệu CRM thật (Ho Chi Minh), valid_from 1900-01-01, "
                   f"is_inferred = false; đang có {first[:3]}")
    if w15[0][0] != first[3]:
        raise Fail("W0015 không trỏ vào phiên bản đầu của C013 (khoá phải giữ nguyên khi inferred → thật)")
    msg = "C013: inferred → dữ liệu thật mà KHÔNG đổi khoá"
    if DAY >= 4:
        c14 = q(f"select is_inferred from {rel} where customer_code = 'C014'")
        if c14 != [(True,)]:
            raise Fail(f"C014 (chỉ có ở POS, CRM không có) phải là 1 dòng inferred; đang có {c14}")
        msg += "; C014 vẫn là inferred"
    return msg


def check_K7():
    need_day(2, "POS đồng bộ hoá đơn 01–02/03 ở ngày 2")
    rel, rc = find("fct_sales"), find("dim_customer")
    rows = dict(q(f"""select f.order_number, c.city from {rel} f join {rc} c using (customer_key)
                      where f.order_number in ('HN-0003', 'HN-0004')"""))
    if rows.get("HN-0003") != "Ha Noi":
        raise Fail(f"HN-0003 (C003 mua 01/03, về kho ngày 2) phải mang thành phố LÚC MUA = Ha Noi, đang là "
                   f"{rows.get('HN-0003')}. Dữ liệu trễ vẫn phải join theo thời điểm phát sinh (sale_ts), không theo hiện tại.")
    if rows.get("HN-0004") != "Da Nang":
        raise Fail(f"HN-0004 (02/03) phải là Da Nang, đang là {rows.get('HN-0004')}")
    n_pos = q1("select count(*) from pos.sales")
    n_fact = q1(f"select count(*) from {rel} where source_system = 'pos'")
    if n_pos != n_fact:
        raise Fail(f"fct_sales có {n_fact} dòng POS, nguồn có {n_pos}")
    msg = "dòng POS về trễ vẫn nhận đúng phiên bản khách tại thời điểm mua"
    if DAY >= 4:
        tier = q(f"""select c.loyalty_tier from {rel} f join {rc} c using (customer_key) where f.order_number = 'W0019'""")
        if tier != [("Silver",)]:
            raise Fail(f"W0019 (C005 mua 04/03 khi đang Silver) đang có hạng {tier}")
        msg += "; W0019 mang hạng Silver dù C005 đã về Member"
    return msg


def check_K8():
    rel = find("fct_order_fulfillment")
    cols = ["order_number", "customer_key", "order_profile_key", "warehouse_location_key", "order_date_key",
            "paid_date_key", "packed_date_key", "shipped_date_key", "delivered_date_key", "returned_date_key",
            "cancelled_date_key", "current_status", "order_total_amount", "item_quantity", "failed_delivery_count",
            "days_to_ship", "days_to_deliver"]
    need_cols(rel, cols)
    truth = truth_fulfillment()
    measure_cols = cols[4:]
    exp = {o: tuple(norm(v[c]) for c in measure_cols) for o, v in truth.items()}
    got = {r[0]: tuple(norm(x) for x in r[1:]) for r in q(f"select order_number, {', '.join(measure_cols)} from {rel}")}
    if set(exp) != set(got):
        diff_report({k: 1 for k in exp}, {k: 1 for k in got}, "đơn")
    wrong = [o for o in exp if exp[o] != got[o]]
    if wrong:
        o = sorted(wrong)[0]
        detail = [f"{c}: có {a} cần {b}" for c, a, b in zip(measure_cols, got[o], exp[o]) if a != b]
        nulls = q1(f"select count(*) from {rel} where " + " or ".join(f"{c} is null" for c in cols[4:11]))
        hint = " Mốc chưa xảy ra phải là -1, không phải null." if nulls else ""
        raise Fail(f"{len(wrong)} đơn sai, vd {o}: " + "; ".join(detail[:4]) + "." + hint)
    loc = resolve_dim(find("dim_location"), "location_key", ["location_code"])
    for o, wkey in q(f"select order_number, warehouse_location_key from {rel}"):
        if loc.get(wkey) != truth[o]["warehouse_code"]:
            raise Fail(f"{o}: kho trỏ tới {loc.get(wkey)}, cần {truth[o]['warehouse_code']} "
                       f"('-1' nếu chưa có sự kiện kho nào)")
    truth_c, orders = truth_customers(), shop_orders()
    cust = {r[0]: (r[1], r[2]) for r in q(f"""select f.order_number, c.customer_code, cast(c.valid_from as timestamp)
                                             from {rel} f left join {find('dim_customer')} c using (customer_key)""")}
    prof = resolve_dim(find("dim_order_profile"), "order_profile_key", ["channel", "payment_method", "is_gift"])
    for o, t in truth.items():
        want = customer_at(truth_c, t["customer_code"], t["order_ts"])
        if cust.get(o) != (t["customer_code"], want[0]):
            raise Fail(f"{o}: customer_key trỏ tới {cust.get(o)}, cần phiên bản ({t['customer_code']}, {want[0]}) "
                       f"hiệu lực lúc đặt đơn")
        h = orders[o]
        okey = q1(f"select order_profile_key from {rel} where order_number = ?", [o])
        if tuple(prof.get(okey) or ()) != (h["channel"], h["payment_method"], h["is_gift"]):
            raise Fail(f"{o}: order_profile_key trỏ tới {prof.get(okey)}")
    return f"{len(exp)} đơn, mọi mốc đúng kể cả sự kiện về trễ / sai thứ tự"


def check_K9():
    rel = find("fct_inventory_daily")
    need_cols(rel, ["snapshot_date_key", "product_key", "warehouse_location_key", "quantity_on_hand", "quantity_in",
                    "quantity_out"])
    prod = resolve_dim(find("dim_product"), "product_key", ["sku"])
    loc = resolve_dim(find("dim_location"), "location_key", ["location_code"])
    got = {(r[0], prod.get(r[1]), loc.get(r[2])): (r[3], r[4], r[5])
           for r in q(f"select snapshot_date_key, product_key, warehouse_location_key, quantity_on_hand, quantity_in, "
                      f"quantity_out from {rel}")}
    exp = truth_inventory()
    if set(exp) - set(got):
        missing = sorted(set(exp) - set(got))
        raise Fail(f"thiếu {len(missing)} dòng (ngày, sku, kho), vd {missing[:3]}. Snapshot phải DÀY ĐẶC: mọi sản phẩm × "
                   f"kho × ngày từ ngày biến động đầu tiên tới ngày dữ liệu mới nhất, kể cả ngày không có biến động.")
    diff_report(exp, got, "dòng (date_key, sku, kho) — (on_hand, in, out)", limit=3)
    msg = f"{len(exp)} dòng snapshot đúng"
    if DAY >= 3:
        msg += f"; SKU04 @ KHO_HN ngày 02/03 = {got[(20260302, 'SKU04', 'KHO_HN')][0]} (đã tính điều chỉnh về trễ)"
    return msg


def check_K10():
    rel, rr = find("fct_promotion_coverage"), find("rpt_promo_no_sales")
    need_cols(rel, ["date_key", "product_key", "promotion_key"])
    prod = resolve_dim(find("dim_product"), "product_key", ["sku"])
    promo = resolve_dim(find("dim_promotion"), "promotion_key", ["promo_code"])
    got = {(r[0], prod.get(r[1]), promo.get(r[2])) for r in q(f"select date_key, product_key, promotion_key from {rel}")}
    exp = truth_coverage()
    diff_report({k: 1 for k in exp}, {k: 1 for k in got}, "dòng coverage (date_key, sku, promo)")
    need_cols(rr, ["date_key", "sku", "promo_code"])
    sold = {(dkey(v["order_ts"]), v["sku"]) for v in truth_sales_lines().values()}
    exp_r = {k for k in exp if k[0] <= dkey(BDATE) and (k[0], k[1]) not in sold}
    got_r = {tuple(r) for r in q(f"select date_key, sku, promo_code from {rr}")}
    diff_report({k: 1 for k in exp_r}, {k: 1 for k in got_r}, "dòng 'được KM mà không bán được'")
    return f"{len(exp)} dòng coverage; {len(exp_r)} (ngày, sản phẩm) được KM mà không bán được tính tới {BDATE:%d/%m}"


def check_K11():
    rel, rr = find("bridge_order_voucher"), find("rpt_revenue_by_voucher")
    need_cols(rel, ["order_number", "voucher_key", "weighting_factor"])
    vou = resolve_dim(find("dim_voucher"), "voucher_key", ["voucher_code"])
    lines = truth_sales_lines()
    exp = truth_voucher_bridge(lines)
    got = {(r[0], vou.get(r[1])): round(float(r[2]), 9) for r in q(f"select order_number, voucher_key, weighting_factor from {rel}")}
    diff_report({k: round(v, 9) for k, v in exp.items()}, got, "cặp (đơn, voucher) — trọng số")
    bad = q(f"select order_number, sum(weighting_factor) from {rel} group by 1 having abs(sum(weighting_factor) - 1) > 1e-9")
    if bad:
        raise Fail(f"tổng trọng số của đơn phải = 1, sai ở {bad[:3]}")
    need_cols(rr, ["voucher_code", "order_count", "weighted_net_amount", "impact_net_amount"])
    net_by_order = defaultdict(int)
    for (o, _ln), v in lines.items():
        net_by_order[o] += v["net_amount"]
    exp_w, exp_i, exp_n = defaultdict(float), defaultdict(int), defaultdict(int)
    for (o, v), w in exp.items():
        exp_w[v] += net_by_order[o] * w
        exp_i[v] += net_by_order[o]
        exp_n[v] += 1
    got_r = {r[0]: (r[1], float(r[2]), float(r[3])) for r in q(
        f"select voucher_code, order_count, weighted_net_amount, impact_net_amount from {rr}")}
    for v in exp_w:
        g = got_r.get(v)
        if g is None:
            raise Fail(f"rpt_revenue_by_voucher thiếu voucher {v}")
        if g[0] != exp_n[v] or abs(g[1] - exp_w[v]) > 1 or abs(g[2] - exp_i[v]) > 1:
            raise Fail(f"{v}: (order_count, weighted, impact) = {g}, cần ({exp_n[v]}, {exp_w[v]:.0f}, {exp_i[v]})")
    total = sum(net_by_order.values())
    over = sum(exp_i.values()) - total
    return f"tổng weighted = tổng doanh thu {total:,}đ; cộng impact vượt {over:,}đ do đơn nhiều voucher bị đếm nhiều lần"


def check_K12():
    rel, rr = find("bridge_category_hierarchy"), find("rpt_sales_by_category")
    need_cols(rel, ["ancestor_category_code", "descendant_category_code", "distance"])
    info = category_info()
    exp = {}
    for code, v in info.items():
        for dist, anc in enumerate(v["ancestors"]):
            exp[(anc, code)] = dist
    got = {(r[0], r[1]): r[2] for r in q(f"select ancestor_category_code, descendant_category_code, distance from {rel}")}
    diff_report(exp, got, "cặp (tổ tiên, con cháu) — distance")
    need_cols(rr, ["category_code", "net_amount", "quantity"])
    prods = products_now()
    net, qty = defaultdict(int), defaultdict(int)
    for v in truth_sales_lines().values():
        for anc in info[prods[v["sku"]]["category_code"]]["ancestors"]:
            net[anc] += v["net_amount"]
            qty[anc] += v["quantity"]
    exp_r = {c: (net[c], qty[c]) for c in info}
    got_r = {r[0]: (norm(r[1]), norm(r[2])) for r in q(f"select category_code, net_amount, quantity from {rr}")}
    diff_report({k: tuple(map(norm, v)) for k, v in exp_r.items()}, got_r, "danh mục — (net, quantity)")
    return f"closure table {len(exp)} cặp; doanh thu cộng dồn đúng ở cả 11 danh mục (TT = {net['TT']:,}đ)"


def check_K13():
    rel, rr = find("fct_sales_target"), find("rpt_target_vs_actual")
    need_cols(rel, ["month_key", "category_l1_key", "target_amount"])
    if q1(f"select count(*) from {rel}") != 3:
        raise Fail("fct_sales_target phải có 3 dòng (tháng 3 × 3 danh mục cấp 1)")
    need_cols(rr, ["month_key", "category_l1_code", "target_amount", "actual_net_amount"])
    info, prods = category_info(), products_now()
    actual = defaultdict(int)
    for v in truth_sales_lines().values():
        mk = v["order_ts"].year * 100 + v["order_ts"].month
        actual[(mk, info[prods[v["sku"]]["category_code"]]["l1"])] += v["net_amount"]
    targets = {(t.year * 100 + t.month, c): a for t, c, a in q("select target_month, upper(category_code), target_amount "
                                                               "from erp.sales_targets")}
    exp = {k: (targets.get(k), actual.get(k, 0)) for k in set(actual) | set(targets)}
    got = {(r[0], r[1]): (norm(r[2]), norm(r[3])) for r in q(
        f"select month_key, category_l1_code, target_amount, actual_net_amount from {rr}")}
    diff_report({k: tuple(map(norm, v)) for k, v in exp.items()}, got, "dòng (tháng, danh mục cấp 1) — (target, actual)")
    feb = sorted(k for k in exp if k[0] == 202602)
    return f"drill-across đúng; {len(feb)} dòng tháng 2 chỉ có thực tế, không có chỉ tiêu (cần full outer join)"


def check_K14():
    path = LAB_DIR / "bus_matrix.yml"
    if not path.exists():
        raise Skip("chưa có file lab/bus_matrix.yml")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    procs = doc.get("bus_matrix") or []
    if len(procs) < 5:
        raise Fail(f"bus_matrix cần ít nhất 5 quy trình nghiệp vụ, đang có {len(procs)}")
    kinds = {"transaction", "periodic_snapshot", "accumulating_snapshot", "factless"}
    for p in procs:
        for field in ("process", "fact", "grain", "type", "dimensions"):
            if not p.get(field):
                raise Fail(f"quy trình {p.get('process') or p} thiếu trường `{field}`")
        if p["type"] not in kinds:
            raise Fail(f"{p['fact']}: type phải là một trong {sorted(kinds)}")
        fact = find(p["fact"])
        fcols = columns(fact)
        for dim in p["dimensions"]:
            if not dim.startswith("dim_"):
                raise Fail(f"{p['fact']}: '{dim}' không phải tên model dimension")
            drel = find(dim)
            key = dim[4:] + "_key"
            if key not in columns(drel):
                raise Fail(f"{dim} phải có cột khoá `{key}`")
            fks = [c for c in fcols if c == key or c.endswith("_" + key)]
            if not fks:
                raise Fail(f"bus matrix nói {p['fact']} dùng {dim} nhưng fact không có cột {key} hoặc *_{key}")
            for fk in fks:
                orphan = q1(f"select count(*) from {fact} f where f.{fk} is not null "
                            f"and f.{fk} not in (select {key} from {drel})")
                if orphan:
                    raise Fail(f"{p['fact']}.{fk} có {orphan} giá trị không có trong {dim}.{key}")
    shared = defaultdict(set)
    for p in procs:
        for dim in p["dimensions"]:
            shared[dim].add(p["fact"])
    conformed = sorted(d for d, f in shared.items() if len(f) > 1)
    return f"{len(procs)} quy trình khớp model thật; dimension dùng chung (conformed): {', '.join(conformed)}"


# =========================================================================== DATA VAULT

def vault_rows(rel, cols):
    return q(f"select {', '.join(cols)} from {rel}")


def check_V1():
    checks = {
        "v_stg_crm__customers": [("CUSTOMER_HK", "customer_code")],
        "v_stg_shop__orders": [("ORDER_HK", "order_number"), ("CUSTOMER_HK", "customer_code")],
        "v_stg_erp__products": [("PRODUCT_HK", "sku"), ("CATEGORY_HK", "category_code")],
        "v_stg_shop__order_lines": [("ORDER_HK", "order_number"), ("PRODUCT_HK", "sku")],
    }
    for model, pairs in checks.items():
        rel = find(model)
        need_cols(rel, ["RECORD_SOURCE", "LOAD_DATETIME"] + [hk for hk, _ in pairs])
        for hk, bk in pairs:
            bad = q1(f"select count(*) from {rel} where {bk} is not null and {hk} <> upper(md5(upper(trim(cast({bk} as varchar)))))")
            if bad:
                raise Fail(f"{model}.{hk}: {bad} dòng không phải hash chuẩn của {bk} (UPPER(MD5(UPPER(TRIM(bk))))). "
                           f"Dùng automate_dv.stage với hashed_columns, đừng tự viết hash.")
        if q1(f"select count(*) from {rel} where RECORD_SOURCE is null or LOAD_DATETIME is null"):
            raise Fail(f"{model}: RECORD_SOURCE / LOAD_DATETIME không được null")
    rel = find("v_stg_pos__sales")
    need_cols(rel, ["ORDER_HK", "CUSTOMER_HK", "PRODUCT_HK", "RECORD_SOURCE", "LOAD_DATETIME"])
    if q1(f"select count(*) from {rel} where CUSTOMER_HK is null"):
        raise Fail("v_stg_pos__sales: khách vãng lai đang có CUSTOMER_HK null → dùng null_columns (zero key '-2')")
    return "5 stage có hash key chuẩn, nguồn bản ghi, thời điểm nạp; khách vãng lai có zero key"


def check_V2():
    specs = {
        "hub_customer": ("CUSTOMER_HK", "customer_code", [
            ("CRM", "select upper(trim(customer_code)), _loaded_at from crm.customers"),
            ("SHOP", "select upper(trim(customer_code)), _loaded_at from _lab.shop_orders_history"),
            ("POS", "select nullif(upper(trim(customer_code)), ''), _loaded_at from pos.sales")]),
        "hub_order": ("ORDER_HK", "order_number", [
            ("SHOP", "select upper(trim(order_number)), _loaded_at from _lab.shop_orders_history"),
            ("POS", "select upper(trim(receipt_no)), _loaded_at from pos.sales")]),
        "hub_product": ("PRODUCT_HK", "sku", [
            ("ERP", "select upper(trim(sku)), _loaded_at from _lab.products_history"),
            ("SHOP", "select upper(trim(sku)), _loaded_at from shop.order_lines"),
            ("POS", "select upper(trim(sku)), _loaded_at from pos.sales")]),
        "hub_category": ("CATEGORY_HK", "category_code", [
            ("ERP", "select upper(trim(category_code)), _loaded_at from erp.categories"),
            ("ERP", "select upper(trim(category_code)), _loaded_at from _lab.products_history")]),
        "hub_voucher": ("VOUCHER_HK", "voucher_code", [
            ("SHOP", "select upper(trim(voucher_code)), _loaded_at from shop.order_vouchers")]),
    }
    notes = []
    for hub, (hk, bk, sources) in specs.items():
        rel = find(hub)
        need_cols(rel, [hk, bk, "LOAD_DATETIME", "RECORD_SOURCE"])
        first = {}
        for sysname, sql in sources:
            for key, lt in q(sql):
                if key is None:
                    continue
                if key not in first or lt < first[key][0]:
                    first[key] = (lt, {sysname})
                elif lt == first[key][0]:
                    first[key][1].add(sysname)
        got = {r[0]: (r[1], r[2], r[3]) for r in vault_rows(rel, [bk, hk, "LOAD_DATETIME", "RECORD_SOURCE"])
               if r[0] not in ("-1", "-2")}
        diff_report({k: 1 for k in first}, {k: 1 for k in got}, f"business key trong {hub}")
        for key, (h, lt, src) in got.items():
            if h != dv_hash(key):
                raise Fail(f"{hub}: hash key của {key} sai")
            if lt != first[key][0]:
                raise Fail(f"{hub}: {key} có LOAD_DATETIME {lt}, cần {first[key][0]} (lần ĐẦU TIÊN thấy key ở bất kỳ nguồn nào)")
            if not any(s in (src or "").upper() for s in first[key][1]):
                raise Fail(f"{hub}: {key} có RECORD_SOURCE '{src}', nhưng lần đầu nó xuất hiện ở {sorted(first[key][1])}")
        if q1(f"select count(*) - count(distinct {hk}) from {rel}"):
            raise Fail(f"{hub}: hash key bị trùng")
        notes.append(f"{hub.split('_')[1]} {len(got)}")
    src13 = q(f"select RECORD_SOURCE from {find('hub_customer')} where customer_code = 'C013'")
    return "hub đúng (" + ", ".join(notes) + ")" + (f"; C013 lần đầu thấy ở {src13[0][0]}" if src13 else "")


def check_V3():
    hub = {name: dict(q(f"select {hk}, {bk} from {find(name)}")) for name, hk, bk in [
        ("hub_order", "ORDER_HK", "order_number"), ("hub_customer", "CUSTOMER_HK", "customer_code"),
        ("hub_product", "PRODUCT_HK", "sku"), ("hub_category", "CATEGORY_HK", "category_code"),
        ("hub_voucher", "VOUCHER_HK", "voucher_code")]}
    # link đơn – khách
    rel = find("link_order_customer")
    need_cols(rel, ["LINK_ORDER_CUSTOMER_HK", "ORDER_HK", "CUSTOMER_HK", "LOAD_DATETIME", "RECORD_SOURCE"])
    got = {(hub["hub_order"].get(o), hub["hub_customer"].get(c)) for o, c in vault_rows(rel, ["ORDER_HK", "CUSTOMER_HK"])}
    got = {p for p in got if p[1] not in ("-1", "-2")}
    exp = {tuple(r) for r in q("select upper(trim(order_number)), upper(trim(customer_code)) from shop.orders")}
    exp |= {tuple(r) for r in q("select distinct upper(trim(receipt_no)), upper(trim(customer_code)) from pos.sales "
                                "where trim(customer_code) <> ''")}
    diff_report({k: 1 for k in exp}, {k: 1 for k in got}, "cặp (đơn, khách)")
    # link sản phẩm – danh mục: mọi cặp TỪNG xuất hiện
    rel = find("link_product_category")
    need_cols(rel, ["LINK_PRODUCT_CATEGORY_HK", "PRODUCT_HK", "CATEGORY_HK"])
    got = {(hub["hub_product"].get(p), hub["hub_category"].get(c)) for p, c in vault_rows(rel, ["PRODUCT_HK", "CATEGORY_HK"])}
    exp = {tuple(r) for r in q("select distinct upper(trim(sku)), upper(trim(category_code)) from _lab.products_history")}
    diff_report({k: 1 for k in exp}, {k: 1 for k in got}, "cặp (sku, danh mục)")
    # non-historized link dòng đơn
    rel = find("nh_link_order_line")
    need_cols(rel, ["ORDER_LINE_HK", "ORDER_HK", "PRODUCT_HK", "line_no", "quantity", "unit_price"])
    got = {(hub["hub_order"].get(o), ln): (hub["hub_product"].get(p), qn, norm(pr))
           for o, p, ln, qn, pr in vault_rows(rel, ["ORDER_HK", "PRODUCT_HK", "line_no", "quantity", "unit_price"])}
    exp = {(r[0], r[1]): (r[2], r[3], norm(r[4])) for r in q(
        """select upper(trim(order_number)), line_no, upper(trim(sku)), quantity, unit_price from shop.order_lines
           union all
           select upper(trim(receipt_no)), line_no, upper(trim(sku)), quantity, unit_price from pos.sales""")}
    diff_report(exp, got, "dòng đơn (đơn, line_no)")
    if q1(f"select count(*) - count(distinct ORDER_LINE_HK) from {rel}"):
        raise Fail("nh_link_order_line: ORDER_LINE_HK bị trùng")
    rel = find("nh_link_order_voucher")
    need_cols(rel, ["ORDER_VOUCHER_HK", "ORDER_HK", "VOUCHER_HK", "discount_amount"])
    got = {(hub["hub_order"].get(o), hub["hub_voucher"].get(v)): norm(a)
           for o, v, a in vault_rows(rel, ["ORDER_HK", "VOUCHER_HK", "discount_amount"])}
    exp = {(r[0], r[1]): norm(r[2]) for r in q(
        "select upper(trim(order_number)), upper(trim(voucher_code)), discount_amount from shop.order_vouchers")}
    diff_report(exp, got, "cặp (đơn, voucher)")
    return "link đơn–khách, sản phẩm–danh mục (giữ cả cặp cũ của SKU07), 2 non-historized link đều đúng"


def sat_check(sat, hk, hub, bk, payload_cols, history_sql, label):
    """So satellite với lịch sử thay đổi chuẩn: chỉ có dòng khi payload KHÁC dòng liền trước của cùng key."""
    rel = find(sat)
    need_cols(rel, [hk, "LOAD_DATETIME", "RECORD_SOURCE"] + payload_cols)
    dup = q1(f"select count(*) from (select {hk}, LOAD_DATETIME from {rel} group by 1, 2 having count(*) > 1)")
    if dup:
        raise Fail(f"{sat}: {dup} cặp ({hk}, LOAD_DATETIME) bị lặp → satellite chèn lại lịch sử cũ. Stage chứa nhiều "
                   f"lần nạp thì phải bật apply_source_filter (hoặc stage chỉ giữ lần nạp mới nhất).")
    exp, last = {}, {}
    for key, lt, *payload in q(history_sql):
        p = tuple(norm(x) for x in payload)
        if last.get(key) != p:
            exp[(key, lt)] = p
            last[key] = p
    keys = dict(q(f"select {hk}, {bk} from {find(hub)}"))
    got = {(keys.get(h), lt): tuple(norm(x) for x in payload)
           for h, lt, *payload in vault_rows(rel, [hk, "LOAD_DATETIME"] + payload_cols)}
    try:
        diff_report(exp, got, label, limit=3)
    except Fail as e:
        raise Fail(f"{sat}: {e}. (Nếu bạn vừa sửa model vault, chạy ./scripts/replay.sh — vault không dựng lại được bằng 1 lần build.)")
    return len(exp)


def check_V4():
    n1 = sat_check("sat_customer_crm_status", "CUSTOMER_HK", "hub_customer", "customer_code", ["city", "loyalty_tier"],
                   """select upper(trim(customer_code)), _loaded_at, trim(city), trim(loyalty_tier)
                      from crm.customers order by 1, _extract_date""", "dòng (khách, LOAD_DATETIME)")
    n2 = sat_check("sat_customer_crm_profile", "CUSTOMER_HK", "hub_customer", "customer_code", ["full_name", "email"],
                   """select upper(trim(customer_code)), _loaded_at, trim(full_name), nullif(lower(trim(email)), '')
                      from crm.customers order by 1, _extract_date""", "dòng (khách, LOAD_DATETIME)")
    n3 = sat_check("sat_order_shop", "ORDER_HK", "hub_order", "order_number", ["order_status", "paid_at", "cancelled_at"],
                   """select upper(trim(order_number)), _loaded_at, lower(status), paid_at, cancelled_at
                      from _lab.shop_orders_history order by 1, day""", "dòng (đơn, LOAD_DATETIME)")
    n4 = sat_check("sat_product_erp", "PRODUCT_HK", "hub_product", "sku", ["product_name", "brand", "list_price"],
                   """select upper(trim(sku)), _loaded_at, trim(product_name), trim(brand), list_price
                      from _lab.products_history order by 1, day""", "dòng (sku, LOAD_DATETIME)")
    rel = find("sat_order_pos")
    need_cols(rel, ["ORDER_HK", "store_code", "LOAD_DATETIME"])
    n_pos = q1("select count(distinct receipt_no) from pos.sales")
    if q1(f"select count(*) from {rel}") != n_pos:
        raise Fail(f"sat_order_pos phải có đúng {n_pos} dòng (1 / hoá đơn, hoá đơn không bao giờ đổi)")
    c5 = q1(f"select count(*) from {find('sat_customer_crm_status')} s join {find('hub_customer')} h using (CUSTOMER_HK) "
            f"where h.customer_code = 'C005'")
    return f"satellite đúng: status {n1}, profile {n2}, đơn online {n3}, sản phẩm {n4} dòng; C005 có {c5} dòng (A→B→A)"


def check_V5():
    rel = find("eff_sat_product_category")
    need_cols(rel, ["LINK_PRODUCT_CATEGORY_HK", "PRODUCT_HK", "CATEGORY_HK", "START_DATE", "END_DATE", "LOAD_DATETIME"])
    prods = dict(q(f"select PRODUCT_HK, sku from {find('hub_product')}"))
    cats = dict(q(f"select CATEGORY_HK, category_code from {find('hub_category')}"))
    latest = q(f"""select PRODUCT_HK, CATEGORY_HK, END_DATE from {rel}
                   qualify row_number() over (partition by LINK_PRODUCT_CATEGORY_HK order by LOAD_DATETIME desc) = 1""")
    open_now = defaultdict(set)
    for p, c, end in latest:
        if end.year == 9999:
            open_now[prods.get(p)].add(cats.get(c))
    exp = {sku: {v["category_code"]} for sku, v in products_now().items()}
    diff_report(exp, dict(open_now), "sản phẩm — tập danh mục ĐANG hiệu lực")
    if DAY >= 3:
        closed = q(f"""select e.END_DATE from {rel} e where e.PRODUCT_HK = '{dv_hash('SKU07')}'
                       and e.CATEGORY_HK = '{dv_hash('DT_PK')}' and year(e.END_DATE) <> 9999""")
        if not closed:
            raise Fail("SKU07 đã sang TT_TUI nhưng link SKU07–DT_PK chưa có dòng đóng (END_DATE). Bật is_auto_end_dating.")
        return f"link SKU07–DT_PK đã đóng lúc {closed[0][0]}, mỗi sản phẩm chỉ còn 1 danh mục hiệu lực"
    return "mỗi sản phẩm có đúng 1 link đang hiệu lực (sang ngày 3 chấm lại để xem link bị đóng)"


def check_V6():
    rel = find("ma_sat_customer_crm_phones")
    need_cols(rel, ["CUSTOMER_HK", "phone_type", "phone_number", "LOAD_DATETIME"])
    hist = defaultdict(dict)
    for code, d, lt, ptype, num in q("""select upper(trim(customer_code)), _extract_date, _loaded_at, lower(trim(phone_type)),
                                              trim(phone_number) from crm.customer_phones order by 1, 2"""):
        hist[code].setdefault((d, lt), set()).add((ptype, num))
    exp = {}
    for code, files in hist.items():
        prev = None
        for (_d, lt), s in sorted(files.items()):
            if s != prev:
                exp[(code, lt)] = frozenset(s)
                prev = s
    keys = dict(q(f"select CUSTOMER_HK, customer_code from {find('hub_customer')}"))
    got = defaultdict(set)
    for h, ptype, num, lt in vault_rows(rel, ["CUSTOMER_HK", "phone_type", "phone_number", "LOAD_DATETIME"]):
        got[(keys.get(h), lt)].add((ptype, num))
    got = {k: frozenset(v) for k, v in got.items()}
    diff_report(exp, got, "tập số điện thoại (khách, LOAD_DATETIME)", limit=2)
    return f"{len(exp)} tập số được ghi; C001 có {sum(1 for k in exp if k[0] == 'C001')} tập (đổi di động ngày 4)"


def check_V7():
    rp = find("pit_customer")
    need_cols(rp, ["CUSTOMER_HK", "AS_OF_DATE"])
    if q1(f"select count(*) from (select CUSTOMER_HK, AS_OF_DATE from {rp} group by 1, 2 having count(*) > 1)"):
        raise Fail("pit_customer: cặp (CUSTOMER_HK, AS_OF_DATE) bị lặp")
    rel = find("customer_status_as_of")
    need_cols(rel, ["customer_code", "as_of_date", "city", "loyalty_tier"])
    loads = sorted({r[0] for r in q("select distinct _loaded_at from crm.customers")})
    files = defaultdict(list)
    for code, lt, city, tier in q("select upper(trim(customer_code)), _loaded_at, trim(city), trim(loyalty_tier) "
                                  "from crm.customers order by 2"):
        files[code].append((lt, city, tier))
    exp = {}
    for code, fs in files.items():
        for a in loads:
            known = [f for f in fs if f[0] <= a]
            exp[(code, a)] = (known[-1][1], known[-1][2]) if known else (None, None)
    got = {(r[0], r[1]): (r[2], r[3]) for r in q(f"select customer_code, as_of_date, city, loyalty_tier from {rel}")
           if r[0] in files}
    # mốc as-of trước khi CRM biết khách: có dòng thì phải null, không có dòng cũng được
    for k, v in list(got.items()):
        if exp.get(k) == (None, None):
            if v != (None, None):
                raise Fail(f"{k}: CRM chưa có khách này tại mốc đó nhưng model trả về {v}")
            del got[k]
    exp = {k: v for k, v in exp.items() if v != (None, None)}
    diff_report(exp, got, "(khách, as_of_date) — (city, tier)", limit=3)
    return f"PIT + {len(loads)} mốc as-of: trạng thái kho biết tại mỗi lần nạp đều đúng"


def check_V8():
    truth_c = truth_customers()
    rel = find("dim_customer_dv")
    need_cols(rel, ["customer_key", "customer_code", "full_name", "email", "city", "loyalty_tier", "valid_from",
                    "valid_to", "is_current", "is_inferred"])
    exp = {(c, vf): tuple(norm(x) for x in (v["city"], v["loyalty_tier"], v["valid_to"], v["is_inferred"],
                                            v["full_name"], v["email"])) for (c, vf), v in truth_c.items()}
    got = {(r[0], r[1]): tuple(norm(x) for x in r[2:]) for r in q(
        f"""select customer_code, cast(valid_from as timestamp), city, loyalty_tier, cast(valid_to as timestamp),
                   is_inferred, full_name, email from {rel} where customer_code <> '-1'""")}
    diff_report(exp, got, "phiên bản dim_customer_dv", limit=3)
    check_lines_against_truth(find("fct_sales_dv"), truth_sales_lines(), truth_c)
    same = ""
    if exists("dim_customer") and exists("fct_sales"):
        d1 = q1(f"select count(*) from (select * from {find('dim_customer_dv')} except select * from {find('dim_customer')})")
        d2 = q1(f"select count(*) from (select * from {find('fct_sales_dv')} except select * from {find('fct_sales')})")
        same = "; giống hệt bản Kimball" if d1 == 0 and d2 == 0 else f"; khác bản Kimball {d1}+{d2} dòng (kiểm tra kiểu cột / khoá)"
    return "star schema dựng từ vault ra đúng số liệu" + same


CHECKS = {
    "K2": ("dim_date + dim_month (conformed, role-playing)", check_K2),
    "K3": ("dimension Type 1 + thành viên đặc biệt", check_K3),
    "K4": ("dim_customer SCD2 từ file CRM", check_K4),
    "K5": ("fct_sales: grain, junk dim, phân bổ đầu đơn", check_K5),
    "K6": ("late-arriving dimension (inferred member)", check_K6),
    "K7": ("late-arriving fact (POS về trễ)", check_K7),
    "K8": ("accumulating snapshot fct_order_fulfillment", check_K8),
    "K9": ("periodic snapshot fct_inventory_daily", check_K9),
    "K10": ("factless coverage + 'KM mà không bán được'", check_K10),
    "K11": ("bridge nhiều giá trị: đơn – voucher", check_K11),
    "K12": ("bridge phân cấp không đều: danh mục", check_K12),
    "K13": ("drill-across chỉ tiêu vs thực tế", check_K13),
    "K14": ("bus matrix khớp model thật", check_K14),
    "V1": ("stage + hash key", check_V1),
    "V2": ("hub (gom nhiều nguồn)", check_V2),
    "V3": ("link + non-historized link", check_V3),
    "V4": ("satellite (bẫy apply_source_filter)", check_V4),
    "V5": ("effectivity satellite", check_V5),
    "V6": ("multi-active satellite", check_V6),
    "V7": ("PIT + trạng thái as-of", check_V7),
    "V8": ("information mart từ vault = Kimball", check_V8),
}


def main():
    global con, DAY, BDATE
    if not DB_PATH.exists():
        sys.exit("Chưa có lab.duckdb. Chạy: python scripts/simulate.py reset")
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    except duckdb.IOException as e:
        sys.exit(f"Không mở được lab.duckdb (đang bị tiến trình khác giữ?): {e}")
    DAY = q1("select current_day from _lab.state")
    BDATE = D0 + timedelta(days=DAY)
    wanted = [a.upper() for a in sys.argv[1:]] or list(CHECKS)
    print(f"Chấm bài ở NGÀY {DAY}/6 (ngày nghiệp vụ {BDATE:%d/%m/%Y})\n")
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
            status, msg = FAIL, f"lỗi SQL khi chấm: {str(e).splitlines()[0]}"
        counts[status] += 1
        print(f"{status}  {cid:<4} {title}\n         {msg}")
    print(f"\nTổng: {counts[PASS]} pass · {counts[FAIL]} fail · {counts[SKIP]} skip")
    con.close()


if __name__ == "__main__":
    main()
