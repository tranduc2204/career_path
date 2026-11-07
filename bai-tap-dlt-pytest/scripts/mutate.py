#!/usr/bin/env python3
"""Chấm bộ test của bạn bằng MUTATION TESTING.

  python scripts/mutate.py            # chấm tất cả
  python scripts/mutate.py P3 P5      # chỉ vài mutant

Cách chấm:
  1. Chạy test của bạn trên pipeline GỐC → phải xanh hết (nếu đỏ: test của bạn sai, hoặc flaky).
  2. Với mỗi "mutant" (một bản pipeline bị cài đúng 1 lỗi hay gặp ngoài đời), chép project ra thư mục tạm,
     cài lỗi, chạy lại test của bạn. Test phải ĐỎ ("giết" được mutant). Mutant sống sót = test của bạn
     không bắt được loại lỗi đó.
Không mutant nào đọc test của bạn: chỉ có pipeline/mayshop_api.py bị sửa.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = "pipeline/mayshop_api.py"

MUTANTS = [
    ("P1", "Chỉ lấy trang đầu tiên (quên phân trang)",
     '        if not body.get("next_page"):\n            break',
     '        break'),
    ("P2", "Quên gửi updated_since: lần nào cũng kéo lại toàn bộ API (dlt vẫn lọc bớt ở client)",
     '{"updated_since": since.isoformat()}',
     '{}'),
    ("P3", "write_disposition append thay vì merge: đơn đổi trạng thái bị nhân đôi",
     '@dlt.resource(primary_key="order_id", write_disposition="merge")',
     '@dlt.resource(primary_key="order_id", write_disposition="append")'),
    ("P4", "Khoá chính sai (order_id + updated_at): merge không gộp được bản cũ và bản mới",
     '@dlt.resource(primary_key="order_id", write_disposition="merge")',
     '@dlt.resource(primary_key=["order_id", "updated_at"], write_disposition="merge")'),
    ("P5", "Bỏ múi giờ của updated_at (+07:00) → lệch 7 tiếng khi lưu UTC",
     'o["updated_at"] = pendulum.parse(o["updated_at"])',
     'o["updated_at"] = pendulum.parse(o["updated_at"][:19])'),
    ("P6", "Đọc '1.290.000' như số thập phân → 1.29",
     'return int(str(value).replace(".", "").replace(",", "").strip())',
     'return int(float(str(value).replace(",", "").strip().split(".")[0]))'),
    ("P7", "Dùng requests thường thay vì requests của dlt: không retry khi API trả 429",
     'from dlt.sources.helpers import requests   # requests của dlt: tự retry 429 / 5xx / lỗi mạng',
     'import requests'),
    ("P8", "max_table_nesting=0: items bị nhét thành cột JSON, mất bảng con orders__items",
     '@dlt.source(name="mayshop", max_table_nesting=1)',
     '@dlt.source(name="mayshop", max_table_nesting=0)'),
]


def run_pytest(project: Path) -> tuple[bool, str]:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests"],
                          cwd=project, capture_output=True, text=True, timeout=600)
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return proc.returncode == 0, tail


def copy_project(dst: Path):
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".venv", ".mutants", "dap-an", "__pycache__",
                                                             "*.duckdb", ".dlt_pipelines", ".git"))


def main(argv):
    wanted = set(a.upper() for a in argv[1:])
    tests = list((ROOT / "tests").glob("test_*.py"))
    n_tests = sum(f.read_text(encoding="utf-8").count("\ndef test_") for f in tests)
    if n_tests == 0:
        sys.exit("Chưa có test nào (def test_... trong tests/test_*.py)")

    print(f"🧪 Chạy {n_tests} test của bạn trên pipeline gốc...")
    ok, tail = run_pytest(ROOT)
    if not ok:
        print("❌ Test của bạn ĐỎ ngay trên pipeline gốc → sửa test trước đã.\n" + tail)
        sys.exit(1)
    print("✅ Xanh trên pipeline gốc\n")

    src = (ROOT / TARGET).read_text(encoding="utf-8")
    killed = 0
    chosen = [m for m in MUTANTS if not wanted or m[0] in wanted]
    for mid, desc, old, new in chosen:
        if old not in src:
            print(f"⚠️  {mid}: không tìm thấy đoạn code cần cài lỗi (bạn đã sửa {TARGET}?) → bỏ qua")
            continue
        with tempfile.TemporaryDirectory(prefix=f"mutant_{mid}_") as tmp:
            proj = Path(tmp) / "proj"
            copy_project(proj)
            (proj / TARGET).write_text(src.replace(old, new, 1), encoding="utf-8")
            survived, tail = run_pytest(proj)
        if survived:
            print(f"❌ {mid} SỐNG SÓT — {desc}")
        else:
            killed += 1
            print(f"✅ {mid} bị giết  — {desc}")
    print(f"\nĐiểm: {killed}/{len(chosen)} mutant bị giết")
    sys.exit(0 if killed == len(chosen) else 1)


if __name__ == "__main__":
    main(sys.argv)
