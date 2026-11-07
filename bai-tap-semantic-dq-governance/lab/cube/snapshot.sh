#!/usr/bin/env bash
# Chép lab.duckdb (đã dbt build) thành bản sao cho Cube đọc.
set -euo pipefail
cd "$(dirname "$0")"
cp ../lab.duckdb data/mayshop.duckdb
echo "✅ data/mayshop.duckdb ← lab.duckdb ($(du -h data/mayshop.duckdb | cut -f1))"
