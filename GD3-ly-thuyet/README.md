# GĐ3 — Lý thuyết (3/12 → 30/12/2026): Các thành phần platform mức Mid

> Mục tiêu GĐ3: biến các bảng mart thành **một nền tảng dữ liệu đáng tin**. Metric định nghĩa một lần (semantic layer), sự cố được phát hiện trước người dùng (DQ framework), mỗi đội sở hữu và cam kết giao diện của mình (governance), pipeline chạy có lịch, có lineage (orchestration). Cuối giai đoạn: **thi chứng chỉ dbt Analytics Engineering**.
> Mọi hành vi công cụ ghi trong tài liệu đã chạy thật trên lab ngày 07/11/2026. Phiên bản ở cuối file.

## Bản đồ khái niệm

```
                        ┌─────────────── TUẦN 8: "Một định nghĩa cho mỗi con số" ───────────────┐
                        │ semantic model · entity · dimension · time spine                       │
 marts (GĐ1–GĐ2) ──────▶│ simple · ratio · derived (offset) · cumulative (period_agg) · conversion │──▶ BI / API / AI (tuần 14)
                        │ saved query · MetricFlow vs Cube                                        │
                        └──────────────────────────────┬─────────────────────────────────────────┘
                                                       │ số đúng chỉ khi dữ liệu đúng
                        ┌──────────────────────────────▼─────────────── TUẦN 9 ──────────────────┐
                        │ chiều chất lượng · severity · SLA/SLO · source freshness · sync log     │
                        │ Elementary: volume / column / schema anomalies · data contracts        │
                        │ incident runbook · postmortem                                           │
                        └──────────────────────────────┬─────────────────────────────────────────┘
                                                       │ ai sở hữu, ai được dùng, chạy lúc nào
            ┌──────────────── TUẦN 10 ─────────────────▼───────────────────────────────────────┐
            │ Governance: groups · access · contracts · versions · exposures · PII · catalog    │
            │ Orchestration: task vs asset · Airflow 3 + Cosmos · Dagster + dbt · ADR           │
            └──────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
            ┌──────────── TUẦN 11 ─────────▼──────────────┐
            │ Chứng chỉ dbt AE (65 câu) · pytest cho dlt   │──▶ GĐ4: dbt Mesh, package, AI context layer
            └──────────────────────────────────────────────┘
```

## Mục lục

### Tuần 8 (3/12 → 9/12) — Semantic layer
| # | File | Khái niệm chính |
|---|---|---|
| 8.1 | [tuan-8/01-semantic-layer-la-gi.md](tuan-8/01-semantic-layer-la-gi.md) | Metric drift, semantic layer vs bảng tổng hợp, các họ semantic layer, OSI, cách MetricFlow sinh SQL |
| 8.2 | [tuan-8/02-metricflow-semantic-model.md](tuan-8/02-metricflow-semantic-model.md) | YAML spec mới vs cũ, entity và luật join, dimension, `metric_time`, time spine, **2 lỗi đã kiểm chứng của dbt 1.12.6** |
| 8.3 | [tuan-8/03-cac-loai-metric.md](tuan-8/03-cac-loai-metric.md) | simple, ratio, derived (`offset_window`), cumulative (`window`, `grain_to_date`, `period_agg`), conversion, saved query |
| 8.4 | [tuan-8/04-van-hanh-semantic-layer.md](tuan-8/04-van-hanh-semantic-layer.md) | `mf` CLI, API của dbt platform, test metric trong CI, quản trị metric |
| 8.5 | [tuan-8/05-cube-va-so-sanh.md](tuan-8/05-cube-va-so-sanh.md) | Data model của Cube, pre-aggregation, so sánh với MetricFlow, khung quyết định |

### Tuần 9 (10/12 → 16/12) — Data quality framework
| # | File | Khái niệm chính |
|---|---|---|
| 9.1 | [tuan-9/01-khung-data-quality.md](tuan-9/01-khung-data-quality.md) | 8 chiều chất lượng, test ở tầng nào, luật vs anomaly, severity, báo động giả, đo TTD/TTR |
| 9.2 | [tuan-9/02-freshness-va-sla.md](tuan-9/02-freshness-va-sla.md) | SLI/SLO/SLA, `loaded_at_field` vs **`loaded_at_query`** trên nhật ký sync, model freshness |
| 9.3 | [tuan-9/03-elementary-anomaly-detection.md](tuan-9/03-elementary-anomaly-detection.md) | Các test Elementary, z-score, training/detection period, **bẫy seasonality**, đọc kết quả |
| 9.4 | [tuan-9/04-data-contracts.md](tuan-9/04-data-contracts.md) | Model contract vs data contract, constraint theo nền tảng, thay đổi phá vỡ, ODCS |
| 9.5 | [tuan-9/05-incident-runbook.md](tuan-9/05-incident-runbook.md) | Vòng đời sự cố, SEV1–3, mẫu runbook, postmortem không đổ lỗi |

### Tuần 10 (17/12 → 23/12) — Orchestration và governance
| # | File | Khái niệm chính |
|---|---|---|
| 10.1 | [tuan-10/01-orchestration-tong-quan.md](tuan-10/01-orchestration-tong-quan.md) | Orchestrator vs cron, task vs asset, 4 mẫu chạy dbt, retry, backfill, microbatch |
| 10.2 | [tuan-10/02-airflow-cosmos.md](tuan-10/02-airflow-cosmos.md) | Airflow 3 (Assets, Task SDK), Cosmos `DbtDag`/`DbtTaskGroup`, LoadMode, ExecutionMode, TestBehavior |
| 10.3 | [tuan-10/03-dagster-dbt.md](tuan-10/03-dagster-dbt.md) | Asset, asset check, `@dbt_assets`, translator, declarative automation, partition |
| 10.4 | [tuan-10/04-adr-chon-orchestrator.md](tuan-10/04-adr-chon-orchestrator.md) | Tiêu chí thường bị bỏ sót, mẫu ADR 0003 |
| 10.5 | [tuan-10/05-governance-dbt.md](tuan-10/05-governance-dbt.md) | groups, access, contracts, versions, exposures, checklist model public |
| 10.6 | [tuan-10/06-pii-policy-tags-openmetadata.md](tuan-10/06-pii-policy-tags-openmetadata.md) | Phân loại dữ liệu, che PII 3 tầng, Snowflake masking policy, BigQuery policy tag, OpenMetadata |

### Tuần 11 (24/12 → 30/12) — Chứng chỉ dbt + pytest
| # | File | Khái niệm chính |
|---|---|---|
| 11.1 | [tuan-11/01-chung-chi-dbt-ae.md](tuan-11/01-chung-chi-dbt-ae.md) | Thể thức thi, 7 mảng, kế hoạch tuần thi, mẹo làm bài |
| 11.2 | [tuan-11/02-on-thi-theo-chu-de.md](tuan-11/02-on-thi-theo-chu-de.md) | Bảng tra nhanh 7 mảng: microbatch, snapshot YAML, unit test, `clone`, `retry`, state, giá trị mặc định |
| 11.3 | [tuan-11/03-de-thi-thu.md](tuan-11/03-de-thi-thu.md) | Đề thi thử 65 câu (tiếng Anh) |
| 11.4 | [tuan-11/04-dap-an-de-thi-thu.md](tuan-11/04-dap-an-de-thi-thu.md) | Đáp án + giải thích + bảng tự đánh giá theo mảng |
| 11.5 | [tuan-11/05-pytest-cho-pipeline-dlt.md](tuan-11/05-pytest-cho-pipeline-dlt.md) | Kim tự tháp test, fixture, nguồn giả, 8 hành vi phải test, mutation testing |

### Tổng hợp
- [cau-hoi-on-tap.md](cau-hoi-on-tap.md) — câu hỏi tự kiểm tra / phỏng vấn mức Mid → Senior cho cả GĐ3.

### Thực hành
| Tuần | Bài | Chạy ở đâu |
|---|---|---|
| 8, 9, 10 | [../bai-tap-semantic-dq-governance/](../bai-tap-semantic-dq-governance/README.md) — lab có tự chấm: 8 bài semantic layer, 7 bài DQ qua 8 ngày có 6 sự cố, 6 bài governance, 5 bài orchestration (Dagster + Airflow/Cosmos) + kit Cube | Máy bạn (DuckDB, Docker cho Cube) |
| 11 | [../bai-tap-dlt-pytest/](../bai-tap-dlt-pytest/README.md) — viết pytest cho pipeline dlt, chấm bằng 8 mutant | Máy bạn |
| 11 | [tuan-11/03-de-thi-thu.md](tuan-11/03-de-thi-thu.md) — đề thi thử | Giấy + đồng hồ |

## Cách dùng trong lịch ngày

Giữ khung ngày của roadmap: 07:30–11:30 lý thuyết · 13:00–17:00 build · 18:30–20:30 **luyện phỏng vấn** (từ tuần 8) · 20:30–22:30 viết tài liệu, tổng kết.

- **Sáng:** file lý thuyết của ngày + docs gốc ở cuối file.
- **Chiều:** bài lab tương ứng, rồi mục "Áp dụng vào project thật" (`adventure_works` trên Snowflake, `thelook` trên BigQuery).
- **Tối:** luyện phỏng vấn bằng [cau-hoi-on-tap.md](cau-hoi-on-tap.md) (nói thành tiếng, bấm giờ 2 phút/câu); viết bài so sánh / runbook / ADR.

### Lịch theo ngày

Mỗi tuần bắt đầu từ thứ Năm. Chủ nhật học nửa ngày: ôn + tự chấm lại.

**Tuần 8 — Semantic layer**

| Ngày | Sáng | Chiều |
|---|---|---|
| T5 03/12 | 8.1, 8.2 | Lab setup, M1, M2 |
| T6 04/12 | 8.3 (simple, ratio) | M3, M4 |
| T7 05/12 | 8.3 (derived, cumulative) | M5, M6 (gặp 2 bẫy: `fill_nulls_with`, `period_agg`) |
| CN 06/12 | Ôn 8.1–8.3 | M7, M8 → `check.py M` 8/8 |
| T2 07/12 | 8.4 | `thelook`: semantic layer 10 metric trên BigQuery |
| T3 08/12 | 8.5 | Cube: chạy kit, thêm 4 measure, đối chiếu số |
| T4 09/12 | Viết bài so sánh MetricFlow vs Cube | `adventure_works`: metric doanh thu, AOV, luỹ kế năm |

**Tuần 9 — Data quality** 👉 bắt đầu nộp CV vị trí Mid, 5–10 chỗ/tuần

| Ngày | Sáng | Chiều |
|---|---|---|
| T5 10/12 | 9.1, 9.2 | Q1 (đi tay ngày 0 → 2 bằng `next` + `run_day.sh`) |
| T6 11/12 | 9.3 | Q2, Q3 (`replay.sh` sau mỗi thay đổi) |
| T7 12/12 | 9.4 | Q4, Q5, Q6 |
| CN 13/12 | Ôn | Q7 → `replay.sh` 7/7 phần Q |
| T2 14/12 | 9.5 | Runbook 6 sự cố, postmortem cho Q5 |
| T3 15/12 | — | `thelook`/`adventure_works`: SLA freshness mọi source, Elementary cho 2 fact, `edr report` |
| T4 16/12 | Ôn cả tuần | Contract cho mọi mart public của `adventure_works` |

**Tuần 10 — Orchestration + governance**

| Ngày | Sáng | Chiều |
|---|---|---|
| T5 17/12 | 10.5 | G1, G2, G3 |
| T6 18/12 | 10.5 (versions), 10.6 | G4, G5, G6 |
| T7 19/12 | 10.1, 10.3 | O1–O4 (Dagster) |
| CN 20/12 | Ôn | `replay.sh` toàn bộ: 25/26 (O5 còn SKIP) |
| T2 21/12 | 10.2 | O5 (Airflow + Cosmos), đo thời gian |
| T3 22/12 | 10.4 | ADR 0003 orchestrator |
| T4 23/12 | 10.6 (BigQuery, OpenMetadata) | `thelook`: policy tag cho email; OpenMetadata ingest artifact của `adventure_works` |

**Tuần 11 — Chứng chỉ + pytest:** xem lịch chi tiết ở [11.1](tuan-11/01-chung-chi-dbt-ae.md#kế-hoạch-tuần-11-243012). Thi ngày **T4 30/12**.

## Checklist mốc 30/12

**Semantic layer (tuần 8)**
- [ ] Lab: `check.py M` 8/8
- [ ] `thelook`: ≥ 10 metric (đủ 4 loại), `mf validate-configs` trong CI
- [ ] Bài viết MetricFlow vs Cube có bảng đối chiếu số liệu thật

**Data quality (tuần 9)**
- [ ] Lab: Q1–Q7 PASS qua `replay.sh`
- [ ] `adventure_works` / `thelook`: freshness mọi source, Elementary cho ≥ 2 bảng, contract cho mọi mart public
- [ ] `docs/incident-runbook.md` (6 loại cảnh báo) + 1 postmortem

**Governance + orchestration (tuần 10)**
- [ ] Lab: `replay.sh` 26/26 (hoặc 25/26 nếu chưa cài Airflow)
- [ ] `thelook`: policy tag cho cột PII; `adventure_works`: groups + access + 1 model có version
- [ ] ADR 0003 có số đo; ảnh chụp lineage (Dagster hoặc OpenMetadata) trong README

**Tuần 11**
- [ ] Đề thi thử ≥ 52/65 (80%) trước ngày thi
- [ ] ✅ **Đỗ dbt Analytics Engineering Certification**
- [ ] Lab dlt: 8/8 mutant; pytest + CI cho pipeline dlt thật
- [ ] Đã nộp ≥ 15 CV vị trí Mid (từ 10/12)

## Ghi chú phiên bản (kiểm chứng ngày 07/11/2026)

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| dbt-core / dbt-duckdb / duckdb | 1.12.6 / 1.11.1 / 1.5.6 | Ghim `duckdb<2` như GĐ2 |
| dbt-metricflow / metricflow | 0.15.0 / 0.213.0 | Chạy được YAML spec mới và cũ, trộn được trong một project |
| Elementary (dbt package) | 0.26.1 | Có hỗ trợ DuckDB. Biến `custom_run_started_at` dùng làm đồng hồ lab |
| dagster / dagster-dbt | 1.13.29 / 0.29.29 | Cùng venv với dbt |
| apache-airflow / astronomer-cosmos | 3.4.0 / 1.16.0 | Venv riêng (~230 MB) |
| Cube Core | v1.6.77 (Docker) | Driver DuckDB đọc được file của DuckDB 1.5 |
| dlt / pytest | 1.32.0 / 9.2.0 | |

**Hành vi đã đo, cần nhớ:**

| Hành vi | Ở đâu |
|---|---|
| YAML semantic spec mới: `fill_nulls_with` bị bỏ qua khi parse | 8.2, bài M5 |
| `semantic_model:` kiểu mới trên model có `versions:` bị bỏ qua lặng lẽ → dùng `semantic_models:` cũ với `ref(..., v=2)` | 8.2, 10.5, bài G4 |
| Entity tên `order` → SQL lỗi cú pháp khi truy vấn gộp | 8.2, bài M2 |
| Cumulative gom lên tháng: `period_agg` mặc định `first` | 8.3, bài M6 |
| Conversion `window: 1 day` ở grain ngày = cùng ngày | 8.3 |
| Elementary `seasonality: day_of_week` + lịch sử ngắn → trung bình chứa bucket 0, không phát hiện được | 9.3, bài Q2 |
| Test severity error trên **source** làm skip model phía sau trong `dbt build` | 9.1, bài Q3 |
| `loaded_at_query` chạy được (dbt 1.12) | 9.2, bài Q1 |
| `sum(bigint)` trên DuckDB = `HUGEINT` → contract lỗi | 9.4, bài G3 |
| Gõ sai khoá YAML (`colums:`) → dbt 1.12.6 không cảnh báo, test cột lặng lẽ mất | 11.4 câu 29 |
| Airflow 3.4: `DagBag` chuyển sang `airflow.dag_processing.dagbag`, bỏ tham số `include_examples` | 10.2 |
| Cosmos per-model (34 task): ~4,5 phút vs `dbt build` ~15 giây | 10.1, bài O5 |
