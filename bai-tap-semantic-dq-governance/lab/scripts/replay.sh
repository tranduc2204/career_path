#!/usr/bin/env bash
# Làm lại từ đầu và "sống lại" từng ngày: reset → mỗi ngày chạy scripts/run_day.sh → chấm điểm.
# BẮT BUỘC dùng để chấm phần DQ (Q*): Elementary học từ lịch sử các lần chạy trước, và check.py
# cần kết quả freshness/test của TỪNG ngày trong .replay/.
#
#   ./scripts/replay.sh            # ngày 0 → 7
#   ./scripts/replay.sh 3          # dừng ở ngày 3
#   ./scripts/replay.sh 7 -s +fct_orders   # tham số sau N truyền thẳng cho dbt build
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR=.

UNTIL="${1:-7}"
shift || true
PY="${PYTHON:-python}"

rm -rf .replay
for day in $(seq 0 "$UNTIL"); do
  if [ "$day" -eq 0 ]; then
    "$PY" scripts/simulate.py reset
  else
    "$PY" scripts/simulate.py next
  fi
  ./scripts/run_day.sh "$@"
done

echo
"$PY" scripts/check.py
