#!/usr/bin/env bash
# Làm lại từ đầu và "sống lại" từng ngày: reset → mỗi ngày (dbt build + runbook) → chấm điểm.
# BẮT BUỘC dùng khi bạn tạo/sửa model raw vault (insert-only): lịch sử đã bỏ lỡ không lấy lại được.
#
#   ./scripts/replay.sh            # ngày 0 → 6
#   ./scripts/replay.sh 3          # dừng ở ngày 3
#   ./scripts/replay.sh 6 -s marts # tham số sau N truyền thẳng cho dbt build
#
# Runbook: nếu có file scripts/hooks/after_day_<N>.sh thì nó được chạy ngay sau dbt build của ngày N.
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR=.

UNTIL="${1:-6}"
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
  "$DBT" build "${EXTRA[@]}" --quiet || echo "⚠️  dbt build có lỗi ở ngày $day (xem log phía trên)"
  hook="scripts/hooks/after_day_${day}.sh"
  if [ -x "$hook" ]; then
    echo "--- runbook $hook ---"
    DBT_PROFILES_DIR=. PATH="$(dirname "$(command -v "$DBT")"):$PATH" "$hook" || echo "⚠️  runbook ngày $day lỗi"
  fi
done

echo
"$PY" scripts/check.py
