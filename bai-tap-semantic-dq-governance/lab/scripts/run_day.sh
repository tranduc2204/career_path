#!/usr/bin/env bash
# Chạy pipeline của "sáng nay" giống production, và LƯU KẾT QUẢ CỦA NGÀY để check.py chấm phần DQ:
#   1. dbt source freshness   → .replay/day_N/sources.json
#   2. dbt build              → .replay/day_N/run_results.json  (+ manifest.json)
#   3. runbook scripts/hooks/after_day_N.sh nếu có
#
#   ./scripts/run_day.sh             # chạy cho ngày hiện tại
#   ./scripts/run_day.sh -s marts    # tham số truyền thẳng cho dbt build
#
# Pipeline vẫn chạy tiếp khi freshness/test lỗi (để bạn thấy hết vấn đề trong ngày), giống "dbt build"
# trong một orchestrator có bước cảnh báo riêng.
set -uo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR=.
PY="${PYTHON:-python}"
DBT="${DBT:-dbt}"

DAY=$("$PY" - <<'PY'
import duckdb
con = duckdb.connect("lab.duckdb", read_only=True)
print(con.execute("select day from _lab.state").fetchone()[0])
PY
)
OUT=".replay/day_${DAY}"
rm -rf "$OUT" && mkdir -p "$OUT"

echo "--- [ngày $DAY] dbt source freshness ---"
"$DBT" source freshness --quiet
cp target/sources.json "$OUT/sources.json" 2>/dev/null || echo "⚠️  không có target/sources.json"

echo "--- [ngày $DAY] dbt build $* ---"
"$DBT" build --quiet "$@"
BUILD_RC=$?
cp target/run_results.json "$OUT/run_results.json" 2>/dev/null || true
cp target/manifest.json "$OUT/manifest.json" 2>/dev/null || true
[ "$BUILD_RC" -ne 0 ] && echo "⚠️  dbt build có lỗi/test fail ở ngày $DAY (xem log phía trên)"

hook="scripts/hooks/after_day_${DAY}.sh"
if [ -x "$hook" ]; then
  echo "--- [ngày $DAY] runbook $hook ---"
  DBT_PROFILES_DIR=. PATH="$(dirname "$(command -v "$DBT")"):$PATH" "$hook" || echo "⚠️  runbook ngày $DAY lỗi"
fi
"$PY" scripts/check.py --summary-day "$DAY" 2>/dev/null || true
exit 0
