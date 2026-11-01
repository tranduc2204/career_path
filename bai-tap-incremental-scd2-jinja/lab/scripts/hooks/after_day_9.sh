#!/usr/bin/env bash
# P4 — Ngày 9: backend UPDATE thẳng 6 đơn ngày 2025-12-27 (+$5 phí ship) mà không đổi
# updated_at / _loaded_at → watermark của fct_orders và fct_daily_revenue không thấy.
# Backfill có chủ đích ngày 27/12 cho cả 2 bảng incremental đọc orders (anh em, không phải cha con),
# kèm `+` để build lại bảng con (fct_orders_pit). Dùng `build` để audit_fct_orders_vs_full chạy lại ngay:
# backfill sót thì test đỏ → hook lỗi → replay.sh in ⚠️.
# Chạy lại nhiều lần vẫn ra cùng kết quả (merge / delete+insert tính lại từ nguồn).
set -euo pipefail

BACKFILL_START=2025-12-27
BACKFILL_END=2025-12-27

dbt build -s fct_orders+ fct_daily_revenue+ \
  --vars "{backfill_start: ${BACKFILL_START}, backfill_end: ${BACKFILL_END}}" \
  --quiet

echo "after_day_9: đã backfill ${BACKFILL_START} → ${BACKFILL_END} cho fct_orders, fct_daily_revenue"
