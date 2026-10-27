"""Chấm bài window function.

    python scripts/check.py                 # chấm tất cả
    python scripts/check.py B02 B07 A       # chấm vài bài (A = cả phần A, B = cả phần B)
    python scripts/check.py --thu-muc dap-an   # chấm folder đáp án (để kiểm chứng)

Đáp án chuẩn được tính bằng Python thuần từ dữ liệu nguồn (không dùng SQL), rồi so với
kết quả query của bạn trên 2 bộ dữ liệu: bộ lab (giống lab.duckdb) và bộ ẩn.
"""

import argparse
import bisect
import datetime as dt
import math
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from du_lieu import SEED_AN, SEED_LAB, tao  # noqa: E402

GOC = Path(__file__).resolve().parent.parent
XANH, DO, VANG, XAM, HET = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"


# ---------------------------------------------------------------------------
# Phần A — đoán kết quả. Query được chạy thật trên bảng t, kết quả theo id 1..8.
# ---------------------------------------------------------------------------
CAU_A = {
    "A1": "sum(v) over (partition by nhom order by x)",
    "A2": "sum(v) over (partition by nhom order by x, id rows between unbounded preceding and current row)",
    "A3": "sum(v) over (partition by nhom)",
    "A4": "last_value(v) over (partition by nhom order by x, id)",
    "A5": "last_value(v) over (partition by nhom order by x, id rows between unbounded preceding and unbounded following)",
    "A6": "last_value(v ignore nulls) over (partition by nhom order by x, id rows between unbounded preceding and current row)",
    "A7": "sum(v) over (partition by nhom order by x range between 1 preceding and 1 following)",
    "A8": "count(*) over (partition by nhom order by x groups between 1 preceding and current row)",
    "A9": "sum(v) over (partition by nhom order by x, id rows between 1 following and unbounded following)",
    "A10": "count(v) over (partition by nhom order by x, id rows between 2 preceding and current row)",
    "A11": "avg(v) over (partition by nhom rows between unbounded preceding and unbounded following exclude current row)",
    "A12": "sum(v) over (partition by nhom order by x range between current row and current row)",
}


def cham_a(con, thu_muc, chon):
    file = thu_muc / "A-du-doan.txt"
    tra_loi = {}
    if file.exists():
        for dong in file.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*(A\d+)\s*:(.*)$", dong)
            if m:
                tra_loi[m.group(1)] = m.group(2).split("#")[0].split()
    ket_qua = []
    for ma, bieu_thuc in CAU_A.items():
        if chon and ma not in chon and "A" not in chon:
            continue
        dung = [r[0] for r in con.execute(f"select {bieu_thuc} from t order by id").fetchall()]
        tl = tra_loi.get(ma, [])
        if not tl:
            ket_qua.append((ma, "SKIP", "chưa điền"))
            continue
        try:
            doan = [None if x.upper() == "NULL" else float(x) for x in tl]
        except ValueError:
            ket_qua.append((ma, "FAIL", f"không đọc được: {' '.join(tl)}"))
            continue
        if len(doan) != 8:
            ket_qua.append((ma, "FAIL", f"cần đúng 8 giá trị (id 1..8), bạn ghi {len(doan)}"))
            continue
        sai = [i + 1 for i, (a, b) in enumerate(zip(doan, dung)) if not _bang_nhau(a, b, tol=0.01)]
        if sai:
            ket_qua.append((ma, "FAIL", f"sai ở id {', '.join(map(str, sai))}"))
        else:
            ket_qua.append((ma, "PASS", ""))
    return ket_qua


# ---------------------------------------------------------------------------
# Phần B — đáp án chuẩn tính bằng Python
# ---------------------------------------------------------------------------
def _nhom(rows, *cot):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[c] for c in cot)].append(r)
    return g


def _thang(d):
    return (d.year, d.month)


def b01(D):
    out = {}
    for _, rs in _nhom(D["doanh_thu_ngay"], "cua_hang").items():
        s = 0
        for r in sorted(rs, key=lambda r: r["ngay"]):
            s += r["doanh_thu"]
            out[(r["cua_hang"], r["ngay"])] = {"doanh_thu": r["doanh_thu"], "luy_ke": s}
    return out


def b02(D):
    out = {}
    for _, rs in _nhom(D["giao_dich"], "khach_hang_id").items():
        s = 0
        for r in sorted(rs, key=lambda r: (r["thoi_diem"], r["giao_dich_id"])):
            s += r["so_tien"]
            out[(r["giao_dich_id"],)] = {"luy_ke": s}
    return out


def b03(D):
    out = {}
    for _, rs in _nhom(D["giao_dich"], "khach_hang_id").items():
        for r in rs:
            out[(r["giao_dich_id"],)] = {"so_du": sum(x["so_tien"] for x in rs if x["thoi_diem"] <= r["thoi_diem"])}
    return out


def b04(D):
    out = {}
    for _, rs in _nhom([{**r, "th": _thang(r["ngay"])} for r in D["doanh_thu_ngay"]], "cua_hang", "th").items():
        tong = sum(r["doanh_thu"] for r in rs)
        s = 0
        for r in sorted(rs, key=lambda r: r["ngay"]):
            s += r["doanh_thu"]
            out[(r["cua_hang"], r["ngay"])] = {"ty_trong_thang": r["doanh_thu"] / tong, "ty_trong_luy_ke": s / tong}
    return out


def b05(D):
    out = {}
    for _, rs in _nhom(D["su_kien_don"], "don_id").items():
        rs = sorted(rs, key=lambda r: r["thoi_diem"])
        for r in rs:
            out[(r["su_kien_id"],)] = {"trang_thai_dau": rs[0]["trang_thai"], "trang_thai_cuoi": rs[-1]["trang_thai"]}
    return out


def b06(D):
    out = {}
    for _, rs in _nhom(D["doanh_thu_ngay"], "cua_hang").items():
        rs = sorted(rs, key=lambda r: r["ngay"])
        for i, r in enumerate(rs):
            khung = rs[max(0, i - 6): i + 1]
            out[(r["cua_hang"], r["ngay"])] = {
                "tb_7_dong": sum(x["doanh_thu"] for x in khung) / len(khung),
                "so_dong": len(khung),
            }
    return out


def b07(D):
    out = {}
    for _, rs in _nhom(D["doanh_thu_ngay"], "cua_hang").items():
        for r in rs:
            khung = [x for x in rs if r["ngay"] - dt.timedelta(6) <= x["ngay"] <= r["ngay"]]
            out[(r["cua_hang"], r["ngay"])] = {
                "tong_7_ngay": sum(x["doanh_thu"] for x in khung),
                "so_ngay_co_ban": len(khung),
            }
    return out


def b08(D):
    out = {}
    for _, rs in _nhom(D["doanh_thu_ngay"], "cua_hang").items():
        for r in rs:
            khung = [x for x in rs if r["ngay"] + dt.timedelta(1) <= x["ngay"] <= r["ngay"] + dt.timedelta(7)]
            out[(r["cua_hang"], r["ngay"])] = {"tong_7_ngay_toi": sum(x["doanh_thu"] for x in khung)}
    return out


def b09(D):
    out = {}
    for _, rs in _nhom(D["doanh_thu_ngay"], "cua_hang").items():
        rs = sorted(rs, key=lambda r: r["ngay"])
        mx = None
        for r in rs:
            out[(r["cua_hang"], r["ngay"])] = {
                "max_truoc_do": mx,
                "la_ky_luc": mx is None or r["doanh_thu"] > mx,
            }
            mx = r["doanh_thu"] if mx is None else max(mx, r["doanh_thu"])
    return out


def b10(D):
    out = {}
    for _, rs in _nhom(D["gia_niem_yet"], "san_pham_id").items():
        rs = sorted(rs, key=lambda r: r["ngay"])
        for i, r in enumerate(rs):
            truoc = [x["gia"] for x in rs[: i + 1] if x["gia"] is not None]
            sau = [x["gia"] for x in rs[i:] if x["gia"] is not None]
            out[(r["san_pham_id"], r["ngay"])] = {"gia_da_dien": truoc[-1] if truoc else (sau[0] if sau else None)}
    return out


def b11(D):
    out = {}
    for _, rs in _nhom([{**r, "th": _thang(r["ngay"])} for r in D["doanh_thu_ngay"]], "cua_hang", "th").items():
        for r in rs:
            out[(r["cua_hang"], r["ngay"])] = {
                "con_lai_trong_thang": sum(x["doanh_thu"] for x in rs if x["ngay"] > r["ngay"])
            }
    return out


def b12(D):
    out = {}
    for _, rs in _nhom(D["giao_dich"], "khach_hang_id").items():
        moc = sorted({r["thoi_diem"] for r in rs})
        for r in rs:
            i = bisect.bisect_left(moc, r["thoi_diem"])
            chon = set(moc[max(0, i - 2): i + 1])
            out[(r["giao_dich_id"],)] = {"tong_3_moc": sum(x["so_tien"] for x in rs if x["thoi_diem"] in chon)}
    return out


def b14(D):
    out = {}
    for _, rs in _nhom([{**r, "th": _thang(r["ngay"])} for r in D["doanh_thu_ngay"]], "cua_hang", "th").items():
        for r in rs:
            khac = [x["doanh_thu"] for x in rs if x["ngay"] != r["ngay"]]
            out[(r["cua_hang"], r["ngay"])] = {
                "chenh_lech": (r["doanh_thu"] - sum(khac) / len(khac)) if khac else None
            }
    return out


def b15(D):
    out = {}
    for _, rs in _nhom(D["giao_dich"], "khach_hang_id").items():
        phien, truoc = 0, None
        for r in sorted(rs, key=lambda r: (r["thoi_diem"], r["giao_dich_id"])):
            if truoc is None or r["thoi_diem"] - truoc > dt.timedelta(minutes=30):
                phien += 1
            truoc = r["thoi_diem"]
            out[(r["giao_dich_id"],)] = {"phien_so": phien}
    return out


def _khong_dung_groups(sql):
    return "bài này phải viết KHÔNG dùng GROUPS (để chạy được trên BigQuery/Snowflake)" if re.search(r"\bgroups\b", sql, re.I) else None


# ma: (file, cột khoá, hàm đáp án, kiểm tra thêm)
BAI_B = {
    "B01": ("B01_luy_ke_doanh_thu.sql", ["cua_hang", "ngay"], b01, None),
    "B02": ("B02_sua_bug_luy_ke_giao_dich.sql", ["giao_dich_id"], b02, None),
    "B03": ("B03_so_du_theo_moc_thoi_diem.sql", ["giao_dich_id"], b03, None),
    "B04": ("B04_ty_trong_trong_thang.sql", ["cua_hang", "ngay"], b04, None),
    "B05": ("B05_sua_bug_trang_thai_cuoi.sql", ["su_kien_id"], b05, None),
    "B06": ("B06_trung_binh_7_dong.sql", ["cua_hang", "ngay"], b06, None),
    "B07": ("B07_tong_7_ngay_lich.sql", ["cua_hang", "ngay"], b07, None),
    "B08": ("B08_tong_7_ngay_toi.sql", ["cua_hang", "ngay"], b08, None),
    "B09": ("B09_ky_luc_doanh_thu.sql", ["cua_hang", "ngay"], b09, None),
    "B10": ("B10_dien_gia_bi_thieu.sql", ["san_pham_id", "ngay"], b10, None),
    "B11": ("B11_con_lai_trong_thang.sql", ["cua_hang", "ngay"], b11, None),
    "B12": ("B12_tong_3_moc_groups.sql", ["giao_dich_id"], b12, None),
    "B13": ("B13_tong_3_moc_khong_groups.sql", ["giao_dich_id"], b12, _khong_dung_groups),
    "B14": ("B14_so_voi_ngay_khac.sql", ["cua_hang", "ngay"], b14, None),
    "B15": ("B15_chia_phien.sql", ["giao_dich_id"], b15, None),
}


# ---------------------------------------------------------------------------
def _chuan(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.date):
        return v
    return v


def _bang_nhau(a, b, tol=1e-4):
    a, b = _chuan(a), _chuan(b)
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or (isinstance(a, bool) and isinstance(b, bool) and a == b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=tol)
    return a == b


def _bo_comment(sql):
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return "\n".join(d.split("--")[0] for d in sql.splitlines()).strip()


def _doc_bang(con):
    D = {}
    for bang in ("doanh_thu_ngay", "giao_dich", "su_kien_don", "gia_niem_yet"):
        cur = con.execute(f"select * from {bang}")
        cot = [c[0] for c in cur.description]
        D[bang] = [{k: _chuan(v) for k, v in zip(cot, r)} for r in cur.fetchall()]
    return D


def _so_sanh(con, sql, khoa, dap_an):
    cur = con.execute(sql)
    cot = [c[0].lower() for c in cur.description]
    rows = cur.fetchall()
    can = khoa + list(next(iter(dap_an.values())).keys())
    thieu = [c for c in can if c not in cot]
    if thieu:
        return f"thiếu cột: {', '.join(thieu)} (đang có: {', '.join(cot)})"
    idx = {c: cot.index(c) for c in can}
    cua_ban = {}
    for r in rows:
        k = tuple(_chuan(r[idx[c]]) for c in khoa)
        if k in cua_ban:
            return f"khoá {dict(zip(khoa, k))} xuất hiện nhiều lần — mỗi dòng nguồn chỉ được ra 1 dòng"
        cua_ban[k] = {c: r[idx[c]] for c in can if c not in khoa}
    if len(cua_ban) != len(dap_an):
        return f"ra {len(cua_ban)} dòng, cần {len(dap_an)} (không lọc bớt dòng nào)"
    sai = []
    for k, dung in dap_an.items():
        ban = cua_ban.get(k)
        if ban is None:
            return f"thiếu dòng {dict(zip(khoa, k))}"
        lech = {c: (ban[c], v) for c, v in dung.items() if not _bang_nhau(ban[c], v)}
        if lech:
            sai.append((k, lech))
    if not sai:
        return None
    k, lech = sai[0]
    vi_du = ", ".join(f"{c}: bạn={_in(b)} đúng={_in(d)}" for c, (b, d) in lech.items())
    return f"{len(sai)}/{len(dap_an)} dòng sai. Ví dụ {_in_khoa(khoa, k)} → {vi_du}"


def _in(v):
    v = _chuan(v)
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return "NULL" if v is None else str(v)


def _in_khoa(khoa, k):
    return ", ".join(f"{c}={_in(v)}" for c, v in zip(khoa, k))


def cham_b(bo, thu_muc, chon):
    ket_qua = []
    for ma, (file, khoa, ham, them) in BAI_B.items():
        if chon and ma not in chon and "B" not in chon:
            continue
        duong = thu_muc / file
        if not duong.exists():
            ket_qua.append((ma, "SKIP", f"không thấy {duong.relative_to(GOC)}"))
            continue
        sql = _bo_comment(duong.read_text(encoding="utf-8")).rstrip(";").strip()
        if not sql:
            ket_qua.append((ma, "SKIP", "chưa viết query"))
            continue
        if them and (loi := them(sql)):
            ket_qua.append((ma, "FAIL", loi))
            continue
        loi = None
        for ten, con, D in bo:
            try:
                loi_bo = _so_sanh(con, sql, khoa, ham(D))
            except duckdb.Error as e:
                loi_bo = f"lỗi SQL: {str(e).splitlines()[0]}"
            if loi_bo:
                loi = f"[bộ {ten}] {loi_bo}"
                if ten == "ẩn":
                    loi += " — đúng trên lab.duckdb nhưng sai trên dữ liệu khác: query đang dựa vào đặc điểm riêng của dữ liệu"
                break
        ket_qua.append((ma, "FAIL", loi) if loi else (ma, "PASS", ""))
    return ket_qua


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bai", nargs="*", help="mã bài, ví dụ B02 A3 (A = cả phần A)")
    ap.add_argument("--thu-muc", default="bai-tap", help="folder chứa bài làm (mặc định bai-tap)")
    args = ap.parse_args()
    chon = {b.upper() for b in args.bai}
    thu_muc = (GOC / args.thu_muc).resolve()

    bo = []
    for ten, seed in (("lab", SEED_LAB), ("ẩn", SEED_AN)):
        con = duckdb.connect()
        tao(con, seed)
        bo.append((ten, con, _doc_bang(con)))

    ket_qua = []
    if not chon or any(c.startswith("A") for c in chon):
        ket_qua += cham_a(bo[0][1], thu_muc, chon)
    if not chon or any(c.startswith("B") for c in chon):
        ket_qua += cham_b(bo, thu_muc, chon)

    mau = {"PASS": XANH, "FAIL": DO, "SKIP": XAM}
    for ma, tt, ghi_chu in ket_qua:
        print(f"{ma:<4} {mau[tt]}{tt}{HET}  {ghi_chu}")
    dem = {k: sum(1 for _, t, _ in ket_qua if t == k) for k in ("PASS", "FAIL", "SKIP")}
    print(f"\n{XANH}{dem['PASS']} PASS{HET} · {DO}{dem['FAIL']} FAIL{HET} · {XAM}{dem['SKIP']} SKIP{HET}  / {len(ket_qua)} bài")
    sys.exit(1 if dem["FAIL"] else 0)


if __name__ == "__main__":
    main()
