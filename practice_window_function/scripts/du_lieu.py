"""Sinh dữ liệu cho bài tập window function (Mây Shop).

    python scripts/du_lieu.py          # tạo lab.duckdb (bộ dữ liệu bạn nhìn thấy)

check.py dùng hàm `tao()` để dựng 2 bộ trong bộ nhớ:
  - bộ lab  (SEED_LAB)  — giống hệt lab.duckdb
  - bộ ẩn   (SEED_AN)   — cùng kiểu bẫy (trùng thời điểm, ngày nghỉ, NULL) nhưng khác giá trị,
                          để bắt query "đúng nhờ may mắn" hoặc hard-code.
"""

import datetime as dt
import random
import sys
from pathlib import Path

import duckdb

SEED_LAB = 42
SEED_AN = 2027
GOC = Path(__file__).resolve().parent.parent


def tao(con: duckdb.DuckDBPyConnection, seed: int) -> None:
    rng = random.Random(seed)
    _bang_t(con)
    _doanh_thu_ngay(con, rng)
    _giao_dich(con, rng)
    _su_kien_don(con, rng)
    _gia_niem_yet(con, rng)


def _bang_t(con):
    # Bảng nhỏ cố định cho phần A (đoán kết quả). Không phụ thuộc seed.
    con.execute("""
        create or replace table t (id integer, nhom varchar, x integer, v integer);
        insert into t values
            (1, 'a', 1, 10), (2, 'a', 2, 20), (3, 'a', 2, 30), (4, 'a', 4, null),
            (5, 'a', 5, 50), (6, 'b', 1, 5),  (7, 'b', 1, 15), (8, 'b', 3, 25);
    """)


def _doanh_thu_ngay(con, rng):
    # CH01 mở mọi ngày, CH02 nghỉ chủ nhật, CH03 nghỉ ngẫu nhiên + 1 đợt nghỉ 5 ngày liền,
    # CH04 khai trương 30/09 (tháng 9 chỉ có 1 dòng) rồi nghỉ ngẫu nhiên.
    bat_dau, ket_thuc = dt.date(2026, 9, 1), dt.date(2026, 10, 31)
    ngay_list = [bat_dau + dt.timedelta(d) for d in range((ket_thuc - bat_dau).days + 1)]
    dot_nghi = rng.randint(5, 45)
    nghi_ch03 = set(ngay_list[dot_nghi:dot_nghi + 5])

    rows = []
    for ngay in ngay_list:
        for ch in ("CH01", "CH02", "CH03", "CH04"):
            if ch == "CH02" and ngay.weekday() == 6:
                continue
            if ch == "CH03" and (ngay in nghi_ch03 or rng.random() < 0.2):
                continue
            if ch == "CH04" and (ngay < dt.date(2026, 9, 30) or (ngay > dt.date(2026, 9, 30) and rng.random() < 0.25)):
                continue
            rows.append([ch, ngay, round(rng.uniform(8, 45), 2)])

    # Cài 1 ngày của CH01 có doanh thu BẰNG đúng kỷ lục trước đó (bẫy > hay >=)
    ch01 = [r for r in rows if r[0] == "CH01"]
    i = rng.randint(12, 40)
    ch01[i][2] = max(r[2] for r in ch01[:i])

    con.execute("create or replace table doanh_thu_ngay (cua_hang varchar, ngay date, doanh_thu decimal(12, 2))")
    con.executemany("insert into doanh_thu_ngay values (?, ?, ?)", rows)


def _giao_dich(con, rng):
    # Giao dịch ví của khách. ~25% giao dịch trùng thời điểm với giao dịch trước (bẫy ties),
    # có khoảng cách đúng 30 phút (bẫy biên phiên), có hoàn tiền (số âm).
    # giao_dich_id được xáo trộn: KHÔNG tăng theo thời gian.
    rows = []
    for k in range(1, 7):
        ts = dt.datetime(2026, 10, 20, 8, 0) + dt.timedelta(minutes=rng.randint(0, 600))
        for j in range(rng.randint(14, 22)):
            if j > 0:
                p = rng.random()
                if p < 0.25:
                    gap = 0
                elif p < 0.65:
                    gap = rng.randint(1, 20)
                elif p < 0.88:
                    gap = rng.randint(31, 240)
                else:
                    gap = 30
                ts += dt.timedelta(minutes=gap)
            so_tien = rng.randint(5, 200) * 10
            if rng.random() < 0.15:
                so_tien = -rng.randint(5, 50) * 10
            rows.append([f"KH0{k}", ts, so_tien])
    ids = rng.sample(range(1001, 1001 + len(rows) * 3), len(rows))
    con.execute("create or replace table giao_dich (giao_dich_id integer, khach_hang_id varchar, thoi_diem timestamp, so_tien integer)")
    con.executemany("insert into giao_dich values (?, ?, ?, ?)", [[i, *r] for i, r in zip(ids, rows)])


def _su_kien_don(con, rng):
    luong = ["tao", "thanh_toan", "dong_goi", "dang_giao", "hoan_thanh"]
    rows = []
    for don in range(1, 26):
        ts = dt.datetime(2026, 10, 1) + dt.timedelta(minutes=rng.randint(0, 20 * 24 * 60))
        buoc = luong[: rng.randint(1, 5)]
        if len(buoc) < 5 and rng.random() < 0.3:
            buoc.append("huy")
        for tt in buoc:
            rows.append([don, ts, tt])
            ts += dt.timedelta(minutes=rng.randint(10, 2 * 24 * 60))
    rng.shuffle(rows)
    ids = rng.sample(range(1, len(rows) * 4), len(rows))
    con.execute("create or replace table su_kien_don (su_kien_id integer, don_id integer, thoi_diem timestamp, trang_thai varchar)")
    con.executemany("insert into su_kien_don values (?, ?, ?, ?)", [[i, *r] for i, r in zip(ids, rows)])


def _gia_niem_yet(con, rng):
    # Bảng giá chỉ ghi khi có thay đổi, ngày không đổi giá = NULL.
    # SP02 NULL ở đầu, SP03 NULL toàn bộ, SP04 NULL ở cuối, SP05 chỉ có 1 giá ở giữa.
    ngay_list = [dt.date(2026, 10, 1) + dt.timedelta(d) for d in range(21)]
    rows = []
    for sp in ("SP01", "SP02", "SP03", "SP04", "SP05"):
        mot_gia = rng.randint(6, 14)
        dau_null = rng.randint(3, 6)
        for i, ngay in enumerate(ngay_list):
            gia = rng.randint(50, 300) * 1000 if (i == 0 or rng.random() < 0.35) else None
            if sp == "SP02" and i < dau_null:
                gia = None
            if sp == "SP03":
                gia = None
            if sp == "SP04" and i >= 15:
                gia = None
            if sp == "SP05":
                gia = rng.randint(50, 300) * 1000 if i == mot_gia else None
            rows.append([sp, ngay, gia])
    con.execute("create or replace table gia_niem_yet (san_pham_id varchar, ngay date, gia integer)")
    con.executemany("insert into gia_niem_yet values (?, ?, ?)", rows)


if __name__ == "__main__":
    duong_dan = GOC / "lab.duckdb"
    duong_dan.unlink(missing_ok=True)
    with duckdb.connect(str(duong_dan)) as con:
        tao(con, SEED_LAB)
        for bang in ("t", "doanh_thu_ngay", "giao_dich", "su_kien_don", "gia_niem_yet"):
            n = con.execute(f"select count(*) from {bang}").fetchone()[0]
            print(f"  {bang:<16} {n:>4} dòng")
    print(f"Đã tạo {duong_dan.relative_to(GOC)}")
    sys.exit(0)
