#!/usr/bin/env bash
# RUNBOOK P4 — nguồn sửa amount của các đơn ngày 2025-12-27 mà không đổi updated_at/_loaded_at.
# Watermark không thấy thay đổi → backfill có chủ đích đúng khoảng ngày bị ảnh hưởng, rồi build lại phía sau.
set -euo pipefail
dbt build -s fct_orders+ fct_daily_revenue+ --exclude fct_events_microbatch \
  --vars '{backfill_start: "2025-12-27", backfill_end: "2025-12-27"}' --quiet
