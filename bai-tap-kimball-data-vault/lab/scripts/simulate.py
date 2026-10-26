#!/usr/bin/env python3
"""Giả lập 5 hệ thống nguồn của "Mây Shop" thay đổi theo từng NGÀY cho lab Kimball + Data Vault.

Chạy từ thư mục lab/:
  python scripts/simulate.py reset     # XOÁ toàn bộ lab.duckdb (cả model dbt), nạp dữ liệu ngày 0
  python scripts/simulate.py next      # sang ngày kế tiếp (1 → 6)
  python scripts/simulate.py status    # đang ở ngày nào, đã xảy ra những gì
  python scripts/simulate.py goto N    # reset rồi nhảy thẳng tới ngày N
                                       # (cảnh báo: raw vault sẽ không thấy trạng thái các ngày ở giữa)

Ngày N có ngày nghiệp vụ 2026-03-01 + N, được nạp vào kho lúc 06:00 sáng hôm sau.
Toàn bộ kịch bản được công khai trong bai-tap/00-setup.md. Schema _lab chỉ dùng để chấm bài: đừng đọc nó trong model.
"""
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb

LAB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LAB_DIR / "lab.duckdb"

D0 = date(2026, 3, 1)               # ngày nghiệp vụ của ngày 0
HISTORY_START = date(2026, 2, 27)   # dữ liệu lịch sử có sẵn từ ngày này
MAX_DAY = 6


def bdate(day: int) -> date:
    """Ngày nghiệp vụ của ngày lab `day`."""
    return D0 + timedelta(days=day)


def load_ts(day: int) -> datetime:
    """Thời điểm công cụ ingest nạp dữ liệu của ngày `day` vào kho (06:00 sáng hôm sau)."""
    return datetime.combine(bdate(day) + timedelta(days=1), time(6, 0))


def day_of(d: date) -> int:
    """Ngày lab mà dữ liệu phát sinh vào ngày nghiệp vụ `d` được nạp (nếu không bị trễ)."""
    return max(0, (d - D0).days)


def at(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm))


def round_1000(x: float) -> int:
    """Làm tròn tới 1.000đ, nửa lên (không dùng round() của Python vì nó làm tròn kiểu ngân hàng)."""
    return int(x / 1000 + 0.5) * 1000


# =========================================================================== DỮ LIỆU GỐC

# ---- CRM: khách hàng. Tracked cho SCD2: city, loyalty_tier. Sửa lỗi (Type 1): full_name, email.
CUSTOMERS = {
    "C001": ("Nguyễn Văn An", "  An.Nguyen@Mail.vn ", "Ha Noi", "Gold"),
    "C002": ("Trần Thị Bình", "binh.tran@mial.vn", "Ho Chi Minh", "Silver"),
    "C003": ("Lê Văn Cường", "cuong.le@mail.vn", "Ha Noi", "Member"),
    "C004": ("Phạm Thị Dung", "dung.pham@mail.vn", "Da Nang", "Silver"),
    "C005": ("Hoàng Văn Em", "em.hoang@mail.vn", "Hue", "Member"),
    "C006": ("Vũ Thị Phương", "phuong.vu@mail.vn", "Can Tho", "Member"),
    "C007": ("Đặng Văn Giang", "giang.dang@mail.vn", "Ha Noi", "Member"),
    "C008": ("Bùi Thị Hoa", "hoa.bui@mail.vn", "Ho Chi Minh", "Gold"),
    "C009": ("Đỗ Văn Khánh", "khanh.do@mail.vn", "Da Nang", "Member"),
    "C010": ("Ngô Thị Lan", "lan.ngo@mail.vn", "Ha Noi", "Silver"),
    "C011": ("Lý Văn Minh", "minh.ly@mail.vn", "Ho Chi Minh", "Member"),
    "C012": ("Mai Thị Ngọc", "ngoc.mai@mail.vn", "Hai Phong", "Member"),
    "C013": ("Trương Văn Phúc", "phuc.truong@mail.vn", "Ho Chi Minh", "Member"),
}
CRM_JOIN_DAY = {"C013": 3}          # khách C013 chỉ có trong file CRM từ ngày 3 (mua online từ ngày 2)
FIELDS = ("full_name", "email", "city", "loyalty_tier")
CUSTOMER_CHANGES = [  # (ngày, mã khách, cột, giá trị mới)
    (1, "C003", "city", "Da Nang"),
    (2, "C002", "email", "binh.tran@mail.vn"),
    (3, "C005", "loyalty_tier", "Silver"),
    (4, "C005", "loyalty_tier", "Member"),
    (5, "C013", "city", "Binh Duong"),
    (6, "C012", "loyalty_tier", "Silver"),
]

PHONES = {  # mã khách: {loại: số}
    "C001": {"mobile": "0901000001", "home": "0241000001"},
    "C008": {"mobile": "0908000008", "work": "0288000008"},
}
PHONE_CHANGES = [  # (ngày, mã khách, loại, số mới hoặc None = bỏ số)
    (4, "C001", "mobile", "0909000001"),
    (5, "C008", "work", None),
]

# ---- ERP: danh mục (cây không đều: có nhánh 1, 2, 3 cấp)
CATEGORIES = [  # (mã, tên, mã cha)
    ("TT", "Thời trang", None),
    ("TT_AO", "Áo", "TT"),
    ("TT_AO_THUN", "Áo thun", "TT_AO"),
    ("TT_AO_KHOAC", "Áo khoác", "TT_AO"),
    ("TT_GIAY", "Giày dép", "TT"),
    ("TT_TUI", "Túi xách", "TT"),
    ("DT", "Điện tử", None),
    ("DT_PK", "Phụ kiện điện tử", "DT"),
    ("DT_PK_SAC", "Sạc & cáp", "DT_PK"),
    ("DT_TN", "Tai nghe", "DT"),
    ("NC", "Nhà cửa", None),
]

PRODUCTS = {  # sku: (tên, thương hiệu, mã danh mục, giá niêm yết)
    "SKU01": ("Áo thun basic trắng", "May", "TT_AO_THUN", 199000),
    "SKU02": ("Áo thun in hình ", "May", "TT_AO_THUN", 249000),
    "SKU03": ("Áo khoác gió", "May", "TT_AO_KHOAC", 459000),
    "SKU04": ("Giày chạy bộ", "Run+", "TT_GIAY", 899000),
    "SKU05": ("Dép quai ngang", "Run+", "TT_GIAY", 159000),
    "SKU06": ("Cáp sạc USB-C", "Volt", "DT_PK_SAC", 99000),
    "SKU07": ("Túi chống sốc laptop", "Volt", "DT_PK", 279000),
    "SKU08": ("Tai nghe bluetooth", "Volt", "DT_TN", 590000),
    "SKU09": (" Gối tựa lưng", "Home", "NC", 189000),
    "SKU10": ("Bình giữ nhiệt", "Home", "NC", 239000),
}
PRODUCT_CHANGES = [  # (ngày, sku, cột, giá trị mới)
    (3, "SKU07", "category_code", "TT_TUI"),
    (5, "SKU01", "list_price", 179000),
]
PRODUCT_FIELDS = ("product_name", "brand", "category_code", "list_price")

PROMOTIONS = [  # (mã KM, tên, sku, từ ngày, đến ngày, % giảm, ngày lab bắt đầu thấy trong ERP)
    ("KM_TET", "Tết sum vầy", "SKU09", date(2026, 2, 27), date(2026, 2, 28), 20, 0),
    ("KM_THANG3", "Mừng tháng 3", "SKU03", date(2026, 3, 1), date(2026, 3, 4), 10, 0),
    ("KM_THANG3", "Mừng tháng 3", "SKU05", date(2026, 3, 1), date(2026, 3, 4), 10, 0),
    ("KM_TAINGHE", "Tuần lễ tai nghe", "SKU08", date(2026, 3, 3), date(2026, 3, 6), 15, 2),
    ("KM_TAINGHE", "Tuần lễ tai nghe", "SKU06", date(2026, 3, 3), date(2026, 3, 6), 15, 2),
]
PROMO_CHANGES = [(3, "KM_THANG3", "end_date", date(2026, 3, 5))]   # gia hạn thêm 1 ngày

VOUCHERS = [  # (mã, loại, tên)
    ("FREESHIP", "freeship", "Miễn phí vận chuyển 30.000đ"),
    ("GIAM50K", "shop", "Giảm 50.000đ"),
    ("GIAM10", "shop", "Giảm 10% giá trị hàng"),
    ("NEWBIE", "platform", "Khách mới giảm 30.000đ"),
    ("VIP100K", "shop", "Khách VIP giảm 100.000đ"),
]

LOCATIONS = [  # (mã, tên, loại, thành phố)
    ("KHO_HN", "Kho Hà Nội", "warehouse", "Ha Noi"),
    ("KHO_HCM", "Kho TP.HCM", "warehouse", "Ho Chi Minh"),
    ("CH_HN", "Cửa hàng Hoàn Kiếm", "store", "Ha Noi"),
    ("CH_HCM", "Cửa hàng Quận 1", "store", "Ho Chi Minh"),
]

SALES_TARGETS = [  # (tháng, mã danh mục cấp 1, chỉ tiêu VND)
    (date(2026, 3, 1), "TT", 40_000_000),
    (date(2026, 3, 1), "DT", 20_000_000),
    (date(2026, 3, 1), "NC", 6_000_000),
]

SHIPPING_FEE = 30000
NORTH = {"Ha Noi", "Hai Phong", "Hue", "Da Nang"}

# ---- Đơn online (website/app). (ngày, giờ, phút, khách, kênh, thanh toán, quà tặng, [(sku, sl)], [voucher], tag)
D = date
ORDER_SPECS = [
    (D(2026, 2, 27), 9, 15, "C001", "web", "card", False, [("SKU01", 2), ("SKU06", 1)], [], None),
    (D(2026, 2, 27), 14, 40, "C002", "app", "cod", False, [("SKU04", 1)], ["FREESHIP"], "returned"),
    (D(2026, 2, 27), 20, 5, "C008", "web", "card", True, [("SKU08", 1), ("SKU06", 2)], ["VIP100K"], None),
    (D(2026, 2, 28), 10, 20, "C004", "app", "ewallet", False, [("SKU03", 1)], [], None),
    (D(2026, 2, 28), 13, 0, "C010", "web", "cod", False, [("SKU02", 2), ("SKU01", 1)], ["GIAM50K"], None),
    (D(2026, 2, 28), 21, 30, "C011", "app", "card", False, [("SKU10", 1), ("SKU09", 1)], [], "late_shipped_event"),
    (D(2026, 3, 1), 8, 45, "C003", "web", "card", False, [("SKU05", 1), ("SKU03", 1)], [], None),
    (D(2026, 3, 1), 11, 10, "C005", "app", "cod", False, [("SKU07", 1)], [], "failed_delivery"),
    (D(2026, 3, 1), 15, 25, "C009", "web", "card", False, [("SKU04", 1), ("SKU06", 1)], ["FREESHIP"], None),
    (D(2026, 3, 1), 19, 50, "C012", "app", "ewallet", True, [("SKU02", 1)], [], None),
    (D(2026, 3, 2), 9, 5, "C003", "app", "card", False, [("SKU01", 1)], [], None),
    (D(2026, 3, 2), 12, 30, "C006", "web", "card", False, [("SKU04", 1), ("SKU05", 2)], ["GIAM50K", "FREESHIP"], None),
    (D(2026, 3, 2), 16, 45, "C001", "web", "card", False, [("SKU08", 1)], [], "cancel_after_pack"),
    (D(2026, 3, 2), 20, 15, "C007", "app", "cod", False, [("SKU10", 2)], [], None),
    (D(2026, 3, 3), 9, 40, "C013", "app", "card", False, [("SKU08", 1), ("SKU06", 1)], ["GIAM10", "FREESHIP", "NEWBIE"], None),
    (D(2026, 3, 3), 11, 20, "C002", "web", "card", False, [("SKU03", 1)], [], None),
    (D(2026, 3, 3), 15, 0, "C010", "app", "ewallet", False, [("SKU09", 2)], [], None),
    (D(2026, 3, 3), 18, 35, "C004", "web", "cod", False, [("SKU05", 1), ("SKU01", 1)], ["FREESHIP"], None),
    (D(2026, 3, 4), 10, 0, "C005", "web", "card", False, [("SKU02", 1)], [], None),
    (D(2026, 3, 4), 13, 15, "C011", "app", "card", False, [("SKU08", 1)], ["GIAM50K"], None),
    (D(2026, 3, 4), 17, 30, "C008", "web", "ewallet", False, [("SKU04", 1)], ["VIP100K", "FREESHIP"], None),
    (D(2026, 3, 4), 20, 45, "C012", "app", "cod", False, [("SKU07", 1), ("SKU06", 1)], [], None),
    (D(2026, 3, 5), 9, 30, "C005", "app", "card", False, [("SKU10", 1)], [], None),
    (D(2026, 3, 5), 11, 45, "C013", "web", "card", False, [("SKU01", 2)], [], None),
    (D(2026, 3, 5), 14, 10, "C009", "app", "cod", False, [("SKU03", 1), ("SKU05", 1)], [], "cancel_before_pack"),
    (D(2026, 3, 5), 19, 20, "C001", "web", "card", True, [("SKU08", 1)], ["FREESHIP"], None),
    (D(2026, 3, 6), 8, 50, "C006", "web", "card", False, [("SKU01", 1), ("SKU06", 1)], [], None),
    (D(2026, 3, 6), 12, 5, "C013", "app", "ewallet", False, [("SKU04", 1)], ["GIAM50K"], None),
    (D(2026, 3, 6), 16, 40, "C003", "web", "cod", False, [("SKU02", 1)], [], None),
    (D(2026, 3, 6), 21, 10, "C010", "app", "card", False, [("SKU09", 1), ("SKU10", 1)], ["FREESHIP"], None),
    (D(2026, 3, 7), 10, 25, "C002", "app", "card", False, [("SKU05", 2)], [], None),
    (D(2026, 3, 7), 13, 35, "C011", "web", "cod", False, [("SKU04", 1)], ["FREESHIP"], None),
    (D(2026, 3, 7), 17, 55, "C007", "web", "card", False, [("SKU03", 1), ("SKU06", 1)], ["GIAM10"], None),
    (D(2026, 3, 7), 20, 30, "C004", "app", "ewallet", False, [("SKU08", 1)], [], None),
]

# ---- Bán tại cửa hàng (POS). (ngày, giờ, phút, cửa hàng, khách hoặc None = khách vãng lai, thanh toán, [(sku, sl)])
POS_SPECS = [
    (D(2026, 2, 27), 10, 30, "CH_HN", "C007", "cash", [("SKU09", 1)]),
    (D(2026, 2, 27), 16, 0, "CH_HCM", None, "card", [("SKU05", 1)]),
    (D(2026, 2, 28), 11, 0, "CH_HN", None, "cash", [("SKU06", 2)]),
    (D(2026, 2, 28), 18, 20, "CH_HCM", "C011", "card", [("SKU02", 1)]),
    (D(2026, 3, 1), 10, 15, "CH_HN", "C003", "card", [("SKU03", 1)]),
    (D(2026, 3, 1), 15, 40, "CH_HCM", None, "cash", [("SKU10", 1)]),
    (D(2026, 3, 2), 12, 0, "CH_HCM", "C008", "card", [("SKU04", 1)]),
    (D(2026, 3, 2), 17, 30, "CH_HN", "C003", "cash", [("SKU03", 1)]),
    (D(2026, 3, 3), 9, 50, "CH_HN", None, "cash", [("SKU01", 1)]),
    (D(2026, 3, 3), 14, 20, "CH_HCM", "C013", "cash", [("SKU05", 1)]),
    (D(2026, 3, 4), 13, 30, "CH_HN", "C010", "cash", [("SKU02", 1)]),
    (D(2026, 3, 4), 19, 5, "CH_HCM", "C014", "card", [("SKU08", 1), ("SKU06", 1)]),
    (D(2026, 3, 5), 10, 40, "CH_HN", "C005", "card", [("SKU07", 1)]),
    (D(2026, 3, 5), 16, 10, "CH_HCM", None, "cash", [("SKU09", 1)]),
    (D(2026, 3, 6), 11, 25, "CH_HN", "C001", "card", [("SKU04", 1)]),
    (D(2026, 3, 6), 20, 0, "CH_HCM", "C002", "cash", [("SKU01", 1)]),
]


def pos_sync_day(d: date) -> int:
    """POS chỉ đồng bộ 2 ngày một lần: dữ liệu bán ngày d tới kho ở ngày lab này."""
    if d <= date(2026, 2, 28):
        return 0
    if d <= date(2026, 3, 2):
        return 2
    if d <= date(2026, 3, 4):
        return 4
    return 6   # 05/03 và 06/03


STOCK_RECEIPTS = [  # (ngày, kho, sku, số lượng)
    (D(2026, 3, 3), "KHO_HN", "SKU04", 10),
    (D(2026, 3, 5), "KHO_HCM", "SKU08", 15),
]
STOCK_ADJUSTMENTS = [  # (ngày phát sinh, kho, sku, chênh lệch, ngày lab nạp vào kho)
    (D(2026, 3, 2), "KHO_HN", "SKU04", -2, 3),   # kiểm kê ngày 02/03 thiếu 2 đôi giày, 04/03 mới nhập vào hệ thống
]

DAY_NOTES = {
    0: [
        "Nạp ban đầu: CRM 12 khách (file ngày 01/03), ERP 10 sản phẩm / 11 danh mục / 3 chương trình KM / 5 voucher,",
        "đơn online 27/02–01/03, POS 27–28/02, sự kiện kho vận và tồn kho từ 27/02.",
    ],
    1: [
        "CRM: khách C003 chuyển Ha Noi → Da Nang.",
        "Đơn W0012 dùng 2 voucher (GIAM50K + FREESHIP).",
    ],
    2: [
        "POS đồng bộ trễ: hoá đơn ngày 01–02/03 mới về (có C003 mua ở Hà Nội ngày 01/03, trước khi chuyển nhà).",
        "Đơn W0015 của khách C013 — CRM CHƯA có khách này. Đơn này dùng 3 voucher.",
        "CRM: khách C002 sửa lỗi gõ email (không phải thay đổi cần lưu lịch sử).",
        "Kho vận: W0006 có sự kiện delivered nhưng sự kiện shipped chưa về. ERP: thêm KM_TAINGHE (03–06/03).",
    ],
    3: [
        "CRM: C013 xuất hiện. C005 lên hạng Member → Silver.",
        "Kho vận: sự kiện shipped của W0006 về trễ; W0008 giao thất bại lần 1.",
        "Tồn kho: điều chỉnh kiểm kê của NGÀY 02/03 mới được nhập (thiếu 2 SKU04 ở KHO_HN).",
        "ERP: SKU07 chuyển danh mục DT_PK → TT_TUI; KM_THANG3 gia hạn tới 05/03. Shop: W0013 bị huỷ sau khi đã đóng gói.",
    ],
    4: [
        "CRM: C005 xuống hạng lại Silver → Member (A → B → A). C001 đổi số di động.",
        "POS đồng bộ hoá đơn 03–04/03 (có khách C014 mà CRM không hề có).",
        "Kho vận: W0008 giao thành công; W0002 bị trả hàng. Shop: W0025 bị huỷ trước khi đóng gói.",
    ],
    5: [
        "CRM: C013 chuyển Ho Chi Minh → Binh Duong. C008 bỏ số điện thoại công ty.",
        "ERP: SKU01 giảm giá niêm yết 199.000 → 179.000.",
    ],
    6: [
        "CRM: C012 lên hạng Member → Silver. POS đồng bộ hoá đơn 05–06/03.",
        "Hết kịch bản: chạy check.py để chấm toàn bộ.",
    ],
}


# =========================================================================== TRẠNG THÁI THEO NGÀY

def customer_state(code: str, day: int):
    """Thuộc tính của khách trong file CRM ngày `day` (None nếu CRM chưa có khách này)."""
    if day < CRM_JOIN_DAY.get(code, 0) or code not in CUSTOMERS:
        return None
    attrs = dict(zip(FIELDS, CUSTOMERS[code]))
    for d, c, f, v in CUSTOMER_CHANGES:
        if c == code and d <= day:
            attrs[f] = v
    return attrs


def phone_state(code: str, day: int):
    if customer_state(code, day) is None:
        return {}
    phones = dict(PHONES.get(code, {"mobile": "09" + code[1:].rjust(8, "0")}))
    for d, c, t, v in PHONE_CHANGES:
        if c == code and d <= day:
            if v is None:
                phones.pop(t, None)
            else:
                phones[t] = v
    return phones


def product_state(sku: str, day: int):
    attrs = dict(zip(PRODUCT_FIELDS, PRODUCTS[sku]))
    for d, s, f, v in PRODUCT_CHANGES:
        if s == sku and d <= day:
            attrs[f] = v
    return attrs


def promotions_state(day: int):
    rows = []
    for code, name, sku, start, end, pct, from_day in PROMOTIONS:
        if from_day > day:
            continue
        row = {"promo_code": code, "promo_name": name, "sku": sku, "start_date": start, "end_date": end, "discount_pct": pct}
        for d, c, f, v in PROMO_CHANGES:
            if c == code and d <= day:
                row[f] = v
        rows.append(row)
    return rows


def unit_price(sku: str, d: date) -> int:
    day = day_of(d)
    price = product_state(sku, day)["list_price"]
    for p in promotions_state(day):
        if p["sku"] == sku and p["start_date"] <= d <= p["end_date"]:
            return round_1000(price * (100 - p["discount_pct"]) / 100)
    return price


def city_at(code: str, ts: datetime):
    """Thành phố của khách tại thời điểm ts theo file CRM gần nhất (None nếu CRM chưa có)."""
    st = customer_state(code, day_of(ts.date()))
    return st["city"] if st else None


# =========================================================================== KẾ HOẠCH ĐƠN ONLINE

@dataclass
class Order:
    number: str
    customer: str
    channel: str
    payment: str
    is_gift: bool
    order_ts: datetime
    lines: list
    vouchers: list           # [(code, discount)]
    tag: str = None
    warehouse: str = ""
    events: list = field(default_factory=list)   # [(event_type, ts, arrival_day)]
    paid_ts: datetime = None
    cancelled_ts: datetime = None
    returned_ts: datetime = None

    @property
    def gross(self):
        return sum(q * p for _, _, q, p in self.lines)

    @property
    def total(self):
        return self.gross - sum(a for _, a in self.vouchers) + SHIPPING_FEE


def voucher_amount(code: str, gross: int) -> int:
    return {"FREESHIP": 30000, "GIAM50K": 50000, "NEWBIE": 30000, "VIP100K": 100000}.get(code) or round_1000(gross * 0.10)


def build_orders():
    specs = sorted(ORDER_SPECS, key=lambda s: at(s[0], s[1], s[2]))
    orders = []
    for i, (d, hh, mm, cust, ch, pay, gift, items, vcodes, tag) in enumerate(specs, start=1):
        ts = at(d, hh, mm)
        lines = [(n, sku, q, unit_price(sku, d)) for n, (sku, q) in enumerate(items, start=1)]
        o = Order(f"W{i:04d}", cust, ch, pay, gift, ts, lines, [], tag)
        o.vouchers = [(v, voucher_amount(v, o.gross)) for v in vcodes]
        city = city_at(cust, ts)
        o.warehouse = "KHO_HN" if city in NORTH else "KHO_HCM"
        packed, shipped, delivered = at(d + timedelta(days=1), 8, 30), at(d + timedelta(days=1), 16), at(d + timedelta(days=3), 11)
        if pay in ("card", "ewallet"):
            o.paid_ts = ts + timedelta(minutes=3)
        if tag == "cancel_before_pack":
            o.cancelled_ts = at(d, 20)
            orders.append(o)
            continue
        o.events.append(["packed", packed, day_of(packed.date())])
        if tag == "cancel_after_pack":
            o.cancelled_ts = at(d + timedelta(days=2), 8)
            orders.append(o)
            continue
        o.events.append(["shipped", shipped, 3 if tag == "late_shipped_event" else day_of(shipped.date())])
        if tag == "failed_delivery":
            o.events.append(["delivery_failed", delivered, day_of(delivered.date())])
            delivered = delivered + timedelta(days=1)
        o.events.append(["delivered", delivered, day_of(delivered.date())])
        if pay == "cod":
            o.paid_ts = delivered
        if tag == "returned":
            o.returned_ts = at(D(2026, 3, 5), 10)
            o.events.append(["returned", o.returned_ts, day_of(o.returned_ts.date())])
        # chỉ giữ sự kiện đã xảy ra trong khoảng thời gian của lab
        o.events = [e for e in o.events if e[1].date() <= bdate(MAX_DAY)]
        if o.paid_ts and o.paid_ts.date() > bdate(MAX_DAY):
            o.paid_ts = None
        orders.append(o)
    return orders


ORDERS = build_orders()


def visible(ts, day):
    """Sự kiện có thời điểm ts đã xảy ra trước khi kho nạp dữ liệu ngày `day`?"""
    return ts is not None and ts < datetime.combine(bdate(day) + timedelta(days=1), time(0))


def order_state(o: Order, day: int):
    """Dòng của shop.orders (hệ thống nguồn ghi đè) nhìn thấy ở ngày `day`, hoặc None nếu đơn chưa tồn tại."""
    if day_of(o.order_ts.date()) > day:
        return None
    changes = [("placed", o.order_ts)]
    if visible(o.paid_ts, day):
        changes.append(("paid", o.paid_ts))
    if visible(o.cancelled_ts, day):
        changes.append(("cancelled", o.cancelled_ts))
    if visible(o.returned_ts, day):
        changes.append(("returned", o.returned_ts))
    status, updated_at = max(changes, key=lambda c: c[1])
    return {
        "order_number": o.number, "customer_code": o.customer, "channel": o.channel, "payment_method": o.payment,
        "is_gift": o.is_gift, "shipping_fee": SHIPPING_FEE, "total_amount": o.total, "status": status,
        "order_ts": o.order_ts, "paid_at": o.paid_ts if visible(o.paid_ts, day) else None,
        "cancelled_at": o.cancelled_ts if visible(o.cancelled_ts, day) else None, "updated_at": updated_at,
    }


def build_events():
    rows = []
    for o in ORDERS:
        for etype, ts, arrival in o.events:
            rows.append((arrival, ts, o.number, etype, o.warehouse))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return [(f"EV{i:05d}",) + r for i, r in enumerate(rows, start=1)]   # (event_id, arrival, ts, order, type, wh)


EVENTS = build_events()


def build_pos():
    rows, seq = [], {"CH_HN": 0, "CH_HCM": 0}
    for d, hh, mm, store, cust, pay, items in sorted(POS_SPECS, key=lambda s: at(s[0], s[1], s[2])):
        seq[store] += 1
        receipt = ("HN" if store == "CH_HN" else "HCM") + f"-{seq[store]:04d}"
        for n, (sku, q) in enumerate(items, start=1):
            rows.append({
                "receipt_no": receipt, "store_code": store, "customer_code": cust or "", "payment_method": pay,
                "sale_ts": at(d, hh, mm), "line_no": n, "sku": sku.lower(), "quantity": q,
                "unit_price": unit_price(sku, d), "arrival": pos_sync_day(d),
            })
    return rows


POS_ROWS = build_pos()


def build_movements():
    rows = []
    for i, sku in enumerate(PRODUCTS, start=1):
        rows.append((HISTORY_START, "KHO_HN", sku, 20 + i, "opening", 0))
        rows.append((HISTORY_START, "KHO_HCM", sku, 25 + i, "opening", 0))
    for o in ORDERS:
        for etype, ts, _arrival in o.events:
            if etype == "shipped":     # hệ thống tồn kho trừ hàng đúng ngày, kể cả khi sự kiện vận chuyển về trễ
                for _n, sku, q, _p in o.lines:
                    rows.append((ts.date(), o.warehouse, sku, -q, "ship", day_of(ts.date())))
            if etype == "returned":
                for _n, sku, q, _p in o.lines:
                    rows.append((ts.date(), o.warehouse, sku, q, "return", day_of(ts.date())))
    for d, wh, sku, q in STOCK_RECEIPTS:
        rows.append((d, wh, sku, q, "receipt", day_of(d)))
    for d, wh, sku, q, arrival in STOCK_ADJUSTMENTS:
        rows.append((d, wh, sku, q, "adjustment", arrival))
    rows = [r for r in rows if r[0] <= bdate(MAX_DAY)]
    rows.sort(key=lambda r: (r[5], r[0], r[1], r[2], r[4]))
    return [(f"MV{i:05d}",) + r for i, r in enumerate(rows, start=1)]   # (id, date, wh, sku, qty, reason, arrival)


MOVEMENTS = build_movements()


# =========================================================================== DATABASE

DDL = """
create schema crm; create schema shop; create schema pos; create schema wms; create schema erp; create schema _lab;

create table crm.customers (customer_code varchar, full_name varchar, email varchar, city varchar, loyalty_tier varchar,
    _extract_date date, _loaded_at timestamp);
create table crm.customer_phones (customer_code varchar, phone_type varchar, phone_number varchar,
    _extract_date date, _loaded_at timestamp);

create table shop.orders (order_number varchar, customer_code varchar, channel varchar, payment_method varchar,
    is_gift boolean, shipping_fee integer, total_amount integer, status varchar, order_ts timestamp,
    paid_at timestamp, cancelled_at timestamp, updated_at timestamp, _loaded_at timestamp);
create table shop.order_lines (order_number varchar, line_no integer, sku varchar, quantity integer,
    unit_price integer, _loaded_at timestamp);
create table shop.order_vouchers (order_number varchar, voucher_code varchar, discount_amount integer, _loaded_at timestamp);

create table pos.sales (receipt_no varchar, store_code varchar, customer_code varchar, payment_method varchar,
    sale_ts timestamp, line_no integer, sku varchar, quantity integer, unit_price integer, _loaded_at timestamp);

create table wms.shipment_events (event_id varchar, order_number varchar, event_type varchar, event_ts timestamp,
    warehouse_code varchar, _loaded_at timestamp);
create table wms.stock_movements (movement_id varchar, sku varchar, warehouse_code varchar, movement_date date,
    qty_change integer, reason varchar, _loaded_at timestamp);

create table erp.products (sku varchar, product_name varchar, brand varchar, category_code varchar,
    list_price integer, _loaded_at timestamp);
create table erp.categories (category_code varchar, category_name varchar, parent_code varchar, _loaded_at timestamp);
create table erp.promotions (promo_code varchar, promo_name varchar, sku varchar, start_date date, end_date date,
    discount_pct integer, _loaded_at timestamp);
create table erp.vouchers (voucher_code varchar, voucher_type varchar, voucher_name varchar, _loaded_at timestamp);
create table erp.locations (location_code varchar, location_name varchar, location_type varchar, city varchar,
    _loaded_at timestamp);
create table erp.sales_targets (target_month date, category_code varchar, target_amount bigint, _loaded_at timestamp);

-- chỉ để chấm bài / điều khiển giả lập (đừng dùng trong model)
create table _lab.state (current_day int, changed_at timestamp);
create table _lab.log (day int, seq int, message varchar);
create table _lab.shop_orders_history as select *, 0 as day from shop.orders where false;
create table _lab.products_history as select *, 0 as day from erp.products where false;
"""


def upsert(con, table, key_cols, row: dict):
    where = " and ".join(f"{k} = ?" for k in key_cols)
    con.execute(f"delete from {table} where {where}", [row[k] for k in key_cols])
    cols = list(row)
    con.execute(f"insert into {table} ({', '.join(cols)}) values ({', '.join('?' * len(cols))})", [row[c] for c in cols])


def apply_day(con, day: int):
    lt = load_ts(day)
    con.execute("begin")

    # ---- CRM: file full mỗi ngày, nối thêm vào bảng (append-only)
    for code in CUSTOMERS:
        st = customer_state(code, day)
        if st:
            con.execute("insert into crm.customers values (?, ?, ?, ?, ?, ?, ?)",
                        [code, st["full_name"], st["email"], st["city"], st["loyalty_tier"], bdate(day), lt])
            for ptype, num in phone_state(code, day).items():
                con.execute("insert into crm.customer_phones values (?, ?, ?, ?, ?)", [code, ptype, num, bdate(day), lt])

    # ---- ERP: bảng trạng thái hiện tại (ghi đè), chỉ dòng thay đổi mới có _loaded_at mới
    if day == 0:
        for c, n, p in CATEGORIES:
            con.execute("insert into erp.categories values (?, ?, ?, ?)", [c, n, p, lt])
        for v in VOUCHERS:
            con.execute("insert into erp.vouchers values (?, ?, ?, ?)", [*v, lt])
        for loc in LOCATIONS:
            con.execute("insert into erp.locations values (?, ?, ?, ?, ?)", [*loc, lt])
        for m, c, amt in SALES_TARGETS:
            con.execute("insert into erp.sales_targets values (?, ?, ?, ?)", [m, c, amt, lt])
    for sku in PRODUCTS:
        st = product_state(sku, day)
        if day == 0 or st != product_state(sku, day - 1):
            upsert(con, "erp.products", ["sku"], {"sku": sku, **st, "_loaded_at": lt})
    prev = {(p["promo_code"], p["sku"]): p for p in promotions_state(day - 1)} if day else {}
    for p in promotions_state(day):
        if prev.get((p["promo_code"], p["sku"])) != p:
            upsert(con, "erp.promotions", ["promo_code", "sku"], {**p, "_loaded_at": lt})

    # ---- Shop: đơn hàng (ghi đè trạng thái), dòng đơn và voucher (chỉ thêm)
    for o in ORDERS:
        st = order_state(o, day)
        if st is None:
            continue
        old = order_state(o, day - 1) if day else None
        if old != st:
            upsert(con, "shop.orders", ["order_number"], {**st, "_loaded_at": lt})
        if old is None:
            for n, sku, q, p in o.lines:
                con.execute("insert into shop.order_lines values (?, ?, ?, ?, ?, ?)", [o.number, n, sku, q, p, lt])
            for v, amt in o.vouchers:
                con.execute("insert into shop.order_vouchers values (?, ?, ?, ?)", [o.number, v, amt, lt])

    # ---- POS: đồng bộ theo đợt (dữ liệu về trễ)
    for r in POS_ROWS:
        if r["arrival"] == day:
            con.execute("insert into pos.sales values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [r["receipt_no"], r["store_code"], r["customer_code"], r["payment_method"], r["sale_ts"],
                         r["line_no"], r["sku"], r["quantity"], r["unit_price"], lt])

    # ---- WMS: log sự kiện và biến động tồn kho (chỉ thêm, có dòng về trễ)
    for ev_id, arrival, ts, order_no, etype, wh in EVENTS:
        if arrival == day:
            con.execute("insert into wms.shipment_events values (?, ?, ?, ?, ?, ?)", [ev_id, order_no, etype, ts, wh, lt])
    for mv_id, d, wh, sku, q, reason, arrival in MOVEMENTS:
        if arrival == day:
            con.execute("insert into wms.stock_movements values (?, ?, ?, ?, ?, ?, ?)", [mv_id, sku, wh, d, q, reason, lt])

    # ---- lịch sử ẩn để chấm bài
    con.execute(f"insert into _lab.shop_orders_history select *, {day} from shop.orders")
    con.execute(f"insert into _lab.products_history select *, {day} from erp.products")
    for i, msg in enumerate(DAY_NOTES.get(day, []), start=1):
        con.execute("insert into _lab.log values (?, ?, ?)", [day, i, msg])
    con.execute("delete from _lab.state")
    con.execute("insert into _lab.state values (?, ?)", [day, datetime.now()])
    con.execute("commit")

    print(f"=== Đã chuyển sang NGÀY {day}: ngày nghiệp vụ {bdate(day):%d/%m/%Y}, nạp lúc {lt:%d/%m %H:%M} ===")
    for msg in DAY_NOTES.get(day, []):
        print(f"  • {msg}")
    if day == MAX_DAY:
        print("\n✅ Đây là ngày cuối của kịch bản.")


# =========================================================================== CLI

def connect():
    try:
        return duckdb.connect(str(DB_PATH))
    except duckdb.IOException as e:
        sys.exit(f"Không mở được {DB_PATH}: {e}\n→ Đóng DBeaver / duckdb CLI / tiến trình dbt khác đang giữ file rồi thử lại.")


def current_day(con):
    try:
        row = con.execute("select current_day from _lab.state").fetchone()
        return row[0] if row else None
    except duckdb.CatalogException:
        return None


def wipe_database():
    for f in (DB_PATH, DB_PATH.with_name(DB_PATH.name + ".wal")):
        f.unlink(missing_ok=True)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"reset", "next", "status", "goto"}:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd in {"reset", "goto"}:
        wipe_database()
    con = connect()
    try:
        if cmd == "reset":
            con.execute(DDL)
            apply_day(con, 0)
            print("\n(Đã xoá toàn bộ lab.duckdb: mọi model/vault dbt cũ cũng mất, build lại từ đầu.)")
        elif cmd == "next":
            day = current_day(con)
            if day is None:
                sys.exit("Chưa có dữ liệu. Chạy: python scripts/simulate.py reset")
            if day >= MAX_DAY:
                sys.exit(f"Đã ở ngày cuối ({MAX_DAY}). Muốn làm lại: python scripts/simulate.py reset")
            apply_day(con, day + 1)
        elif cmd == "goto":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else -1
            if not 0 <= target <= MAX_DAY:
                sys.exit(f"Cú pháp: simulate.py goto N, với N trong khoảng 0..{MAX_DAY}")
            con.execute(DDL)
            for d in range(0, target + 1):
                apply_day(con, d)
            print("\n⚠️  Đã nhảy nhiều ngày một lúc: raw vault chạy sau lệnh này sẽ KHÔNG thấy trạng thái các ngày ở giữa.")
        elif cmd == "status":
            day = current_day(con)
            if day is None:
                print("Chưa có dữ liệu. Chạy: python scripts/simulate.py reset")
                return
            print(f"Đang ở NGÀY {day}/{MAX_DAY} (ngày nghiệp vụ {bdate(day):%d/%m/%Y}). Các sự kiện đã xảy ra:")
            for d, msg in con.execute("select day, message from _lab.log order by day, seq").fetchall():
                print(f"  [ngày {d}] {msg}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
