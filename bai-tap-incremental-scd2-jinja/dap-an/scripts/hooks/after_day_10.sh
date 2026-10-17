#!/usr/bin/env bash
# RUNBOOK P5 — sự kiện mobile đến trễ 8 ngày, vượt lookback 3 ngày của fct_events_by_ts.
# Chạy một lần với lookback dài hơn để vớt lại, không đổi lookback mặc định (tránh tăng chi phí mọi ngày).
set -euo pipefail
dbt build -s fct_events_by_ts+ --vars '{lookback_days: 10}' --quiet
