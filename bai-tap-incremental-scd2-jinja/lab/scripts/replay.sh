#!/usr/bin/env bash
# Làm lại từ đầu và "sống lại" từng ngày: reset → (build + snapshot) mỗi ngày → chấm điểm.
# Dùng khi bạn sửa snapshot / SCD2 / incremental và muốn kiểm tra lại cả chuỗi ngày.
#
#   ./scripts/replay.sh          # chạy tới ngày 5
#   ./scripts/replay.sh 3        # chỉ chạy tới ngày 3
#   ./scripts/replay.sh 5 -s fct_orders+   # chỉ build một phần (tham số sau N truyền thẳng cho dbt build)
#
# Model microbatch (fct_events_microbatch) bị loại khỏi build hằng ngày; chạy riêng theo hướng dẫn bài I8.
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR=.

UNTIL="${1:-5}"
shift || true
EXTRA=("$@")

PY="${PYTHON:-python}"
DBT="${DBT:-dbt}"

for day in $(seq 0 "$UNTIL"); do
  if [ "$day" -eq 0 ]; then
    "$PY" scripts/simulate.py reset
  else
    "$PY" scripts/simulate.py next
  fi
  echo "--- dbt build (ngày $day) ---"
  "$DBT" build --exclude fct_events_microbatch "${EXTRA[@]}" --quiet || echo "⚠️  dbt build có lỗi ở ngày $day (xem log phía trên)"
done

echo
"$PY" scripts/check.py
