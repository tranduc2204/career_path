#!/usr/bin/env bash
# Làm lại từ đầu và "sống lại" từng ngày: reset → mỗi ngày (build + snapshot + runbook) → chấm điểm.
# Dùng khi bạn sửa snapshot / SCD2 / incremental và muốn kiểm tra lại cả chuỗi ngày.
#
#   ./scripts/replay.sh            # ngày 0 → 5 (giai đoạn xây dựng)
#   ./scripts/replay.sh 11         # chạy luôn giai đoạn sự cố (ngày 6 → 11)
#   ./scripts/replay.sh 5 -s fct_orders+   # tham số sau N truyền thẳng cho dbt build
#
# Runbook: nếu có file scripts/hooks/after_day_<N>.sh thì nó được chạy ngay sau dbt build của ngày N.
# Dùng để ghi lại thao tác vận hành bạn đã làm khi xử lý sự cố (backfill, chạy lại với tham số khác...).
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
  hook="scripts/hooks/after_day_${day}.sh"
  if [ -x "$hook" ]; then
    echo "--- runbook $hook ---"
    DBT_PROFILES_DIR=. PATH="$(dirname "$(command -v "$DBT")"):$PATH" "$hook" || echo "⚠️  runbook ngày $day lỗi"
  fi
done

echo
"$PY" scripts/check.py
