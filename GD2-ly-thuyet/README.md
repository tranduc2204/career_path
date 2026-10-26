# GĐ2 — Lý thuyết (5/11 → 2/12/2026): Modeling và Warehouse mức Mid

> Mục tiêu GĐ2: thiết kế mô hình dữ liệu như một AE Mid (Kimball chuyên sâu, Data Vault 2.0), vận hành project thứ 2 trên BigQuery với 3 môi trường + CD, và tối ưu hiệu năng/chi phí trên cả Snowflake lẫn BigQuery.
> Giả định: dbt Core 1.10+ (dùng `data_tests:` và `arguments:` cho tham số test). Các phiên bản đã kiểm chứng ghi ở cuối file.

## Bản đồ khái niệm

```
            ┌──────────────────── TUẦN 4: "Thiết kế như Kimball" ─────────────────────┐
            │ 4 bước · grain · bus matrix · conformed / shrunken dimension            │
            │ role-playing · junk · degenerate · mini-dimension · SCD 0–7             │
            │ transaction · periodic snapshot · accumulating snapshot · factless      │
            │ bridge (nhiều giá trị, phân cấp) · late-arriving fact / dimension       │
            └───────────────┬───────────────────────────────────────┬─────────────────┘
                            │ cùng dữ liệu, cách khác                │ áp dụng trên dữ liệu thật
                            ▼                                        ▼
┌──────── TUẦN 6: "Tích hợp như Data Vault" ────────┐   ┌──── TUẦN 5: "Vận hành như công ty" ─────┐
│ hub · link · satellite · hash key · hashdiff       │   │ BigQuery · thelook_ecommerce            │
│ eff_sat · multi-active sat · non-historized link   │   │ dev / staging(CI) / prod                │
│ business vault · PIT · bridge (DV)                 │   │ GitHub Actions: CI + CD + cleanup       │
│ information mart = star schema từ vault            │   │ Workload Identity Federation            │
│ ADR: Data Vault hay Kimball?                       │   └──────────────────┬──────────────────────┘
└────────────────────────────────────────────────────┘                      │ đo và tối ưu
                                                         ┌──────────────────▼──────────────────────┐
                                                         │ TUẦN 7: "Performance playbook"           │
                                                         │ Snowflake: query profile, pruning,       │
                                                         │   clustering, cỡ warehouse, resource mon.│
                                                         │ BigQuery: partition, cluster, JOBS, label│
                                                         └──────────────────────────────────────────┘
```

## Mục lục

### Tuần 4 (5–11/11) — Kimball chuyên sâu
| # | File | Khái niệm chính |
|---|---|---|
| 4.1 | [tuan-4/01-quy-trinh-4-buoc-va-grain.md](tuan-4/01-quy-trinh-4-buoc-va-grain.md) | Quy trình 4 bước, grain, các loại fact, additive/semi/non-additive, phân bổ đầu đơn |
| 4.2 | [tuan-4/02-bus-matrix-va-conformed-dimension.md](tuan-4/02-bus-matrix-va-conformed-dimension.md) | Bus architecture, bus matrix, conformed & shrunken dimension, drill-across |
| 4.3 | [tuan-4/03-ky-thuat-dimension.md](tuan-4/03-ky-thuat-dimension.md) | Surrogate/durable key, `-1`/`-2`, role-playing, junk, degenerate, mini-dimension, SCD 0–7 |
| 4.4 | [tuan-4/04-bridge-table.md](tuan-4/04-bridge-table.md) | Bridge nhiều giá trị (weighting factor, weighted vs impact), closure table cho cây không đều |
| 4.5 | [tuan-4/05-factless-fact.md](tuan-4/05-factless-fact.md) | Event tracking, coverage, "cái gì không xảy ra" |
| 4.6 | [tuan-4/06-accumulating-va-periodic-snapshot.md](tuan-4/06-accumulating-va-periodic-snapshot.md) | Mốc, lag, sự kiện sai thứ tự, snapshot dày đặc, semi-additive, incremental cho snapshot |
| 4.7 | [tuan-4/07-late-arriving-facts-va-dimensions.md](tuan-4/07-late-arriving-facts-va-dimensions.md) | Late-arriving fact, inferred member, khoá ổn định, khoá sổ |

### Tuần 5 (12–18/11) — Project 2 trên BigQuery, 3 môi trường, CD
| # | File | Khái niệm chính |
|---|---|---|
| 5.1 | [tuan-5/01-bigquery-cho-nguoi-dung-dbt.md](tuan-5/01-bigquery-cho-nguoi-dung-dbt.md) | Project/dataset/location, sandbox vs billing, profile dbt-bigquery, khác biệt SQL |
| 5.2 | [tuan-5/02-thelook-ecommerce.md](tuan-5/02-thelook-ecommerce.md) | Dataset thelook, bus matrix cho thelook, cấu trúc repo |
| 5.3 | [tuan-5/03-ba-moi-truong-dev-staging-prod.md](tuan-5/03-ba-moi-truong-dev-staging-prod.md) | dev / CI / prod, 1–3 GCP project, IAM tối thiểu, `generate_schema_name`, `--sample` |
| 5.4 | [tuan-5/04-cd-github-actions.md](tuan-5/04-cd-github-actions.md) | CI theo PR, CD khi merge, cleanup, manifest trên GCS, WIF, rollback |

### Tuần 6 (19–25/11) — Data Vault 2.0
| # | File | Khái niệm chính |
|---|---|---|
| 6.1 | [tuan-6/01-data-vault-tong-quan.md](tuan-6/01-data-vault-tong-quan.md) | Vì sao Data Vault, kiến trúc 4 tầng, hard/soft rule, điểm yếu |
| 6.2 | [tuan-6/02-hub-link-satellite.md](tuan-6/02-hub-link-satellite.md) | Hash key, hub, link (NH, same-as, hierarchical), satellite, hashdiff, eff/multi-active sat, ghost/zero key |
| 6.3 | [tuan-6/03-automate-dv.md](tuan-6/03-automate-dv.md) | Macro `stage`/`hub`/`link`/`sat`..., `apply_source_filter`, `is_auto_end_dating`, biến, materialization |
| 6.4 | [tuan-6/04-business-vault-pit-bridge.md](tuan-6/04-business-vault-pit-bridge.md) | Computed satellite, PIT, as-of dates, bridge của Data Vault |
| 6.5 | [tuan-6/05-information-mart-tu-vault.md](tuan-6/05-information-mart-tu-vault.md) | Dựng dim/fact từ vault, load date vs effective date, view hay table, đối soát |
| 6.6 | [tuan-6/06-adr-data-vault-vs-kimball.md](tuan-6/06-adr-data-vault-vs-kimball.md) | ADR, mẫu ADR, bảng so sánh, kiến trúc lai |

### Tuần 7 (26/11–2/12) — Performance playbook
| # | File | Khái niệm chính |
|---|---|---|
| 7.1 | [tuan-7/01-tu-duy-performance-va-chi-phi.md](tuan-7/01-tu-duy-performance-va-chi-phi.md) | Mô hình tính tiền, phương pháp đo, đòn bẩy dbt, phản mẫu SQL, rào chắn |
| 7.2 | [tuan-7/02-snowflake-query-profile-va-clustering.md](tuan-7/02-snowflake-query-profile-va-clustering.md) | Micro-partition, pruning, cache, Query Profile, clustering key |
| 7.3 | [tuan-7/03-snowflake-warehouse-va-resource-monitor.md](tuan-7/03-snowflake-warehouse-va-resource-monitor.md) | Cỡ warehouse, scale up/out, `query_tag`, ACCOUNT_USAGE, resource monitor |
| 7.4 | [tuan-7/04-bigquery-partition-va-cluster.md](tuan-7/04-bigquery-partition-va-cluster.md) | Partition, điều kiện pruning, cluster, `insert_overwrite`, `_dbt_max_partition` |
| 7.5 | [tuan-7/05-bigquery-do-chi-phi-information-schema.md](tuan-7/05-bigquery-do-chi-phi-information-schema.md) | Dry run, `INFORMATION_SCHEMA.JOBS`, job label theo model, rào chắn chi phí |
| 7.6 | [tuan-7/06-viet-performance-playbook.md](tuan-7/06-viet-performance-playbook.md) | Cấu trúc playbook, cây quyết định, nhật ký thí nghiệm, runbook |

### Tổng hợp
- [cau-hoi-on-tap.md](cau-hoi-on-tap.md) — câu hỏi tự kiểm tra / phỏng vấn mức Mid cho cả GĐ2.

### Thực hành
| Tuần | Bài | Chạy ở đâu |
|---|---|---|
| 4, 6 | [../bai-tap-kimball-data-vault/](../bai-tap-kimball-data-vault/README.md) — lab có tự chấm: 14 bài Kimball + 8 bài Data Vault trên cùng dữ liệu 5 hệ thống nguồn, 7 "ngày" | Máy bạn (DuckDB) |
| 5 | [../bai-tap-bigquery-thelook/](../bai-tap-bigquery-thelook/README.md) — hướng dẫn từng bước + file mẫu (profiles, macro, 3 workflow, script `gcloud`) cho project 2 | BigQuery + GitHub thật |
| 7 | [../bai-tap-performance/](../bai-tap-performance/README.md) — script thí nghiệm Snowflake (TPC-H) và BigQuery (thelook) + mẫu playbook | Snowflake + BigQuery thật |

## Cách dùng trong lịch ngày

Giữ khung ngày của roadmap: 07:30–11:30 lý thuyết · 13:00–17:00 build · 18:30–20:30 luyện SQL · 20:30–22:30 viết tài liệu, tổng kết.

- **Sáng:** đọc file lý thuyết của ngày + link tài liệu gốc ở cuối file.
- **Chiều:** bài lab tương ứng (tuần 4, 6) hoặc bước hướng dẫn (tuần 5, 7), rồi mục "Áp dụng vào adventure_works / thelook".
- **Tối:** trả lời "Câu hỏi tự kiểm tra" không nhìn tài liệu; viết README / ADR / playbook của ngày.

### Lịch theo ngày

Mỗi tuần của roadmap bắt đầu từ thứ Năm. Chủ nhật học nửa ngày: ôn + tự chấm lại.

**Tuần 4 — Kimball**

| Ngày | Sáng (lý thuyết) | Chiều (build) |
|---|---|---|
| T5 05/11 | 4.1, 4.2 | Lab setup, K1 (thiết kế trên giấy), K2 |
| T6 06/11 | 4.3 | K3, K4 |
| T7 07/11 | 4.7 | K5, rồi `next` tới ngày 2–3: K6, K7 |
| CN 08/11 | Ôn 4.1–4.3, 4.7 | `replay.sh 3`, sửa bài đỏ |
| T2 09/11 | 4.6 | K8, K9 |
| T3 10/11 | 4.4, 4.5 | K10, K11, K12 |
| T4 11/11 | Ôn cả tuần | K13, K14 → `replay.sh` 13/13 bài K. Bus matrix + 1 accumulating snapshot cho adventure_works |

**Tuần 5 — BigQuery + 3 môi trường + CD** (hướng dẫn: [bai-tap-bigquery-thelook](../bai-tap-bigquery-thelook/README.md))

| Ngày | Sáng | Chiều |
|---|---|---|
| T5 12/11 | 5.1 | Bước 1: GCP, billing, budget, quota |
| T6 13/11 | 5.2 | Bước 2: dbt project, target dev |
| T7 14/11 | Ôn tuần 4 | Bước 3: staging 7 bảng |
| CN 15/11 | — | Bước 3: dimension |
| T2 16/11 | 5.3 | Bước 3: fact; Bước 4: service account + WIF |
| T3 17/11 | 5.4 | Bước 5: CI/CD, PR demo |
| T4 18/11 | Viết ADR 0002 | Bước 6: kiểm tra, README, ảnh chụp |

**Tuần 6 — Data Vault 2.0**

| Ngày | Sáng | Chiều |
|---|---|---|
| T5 19/11 | 6.1, 6.2 | V1, V2 |
| T6 20/11 | 6.3 | V3, V4 (gặp bẫy, sửa, replay) |
| T7 21/11 | 6.2 (đọc lại phần satellite đặc biệt) | V5, V6 |
| CN 22/11 | Ôn | `replay.sh`, sửa bài đỏ |
| T2 23/11 | 6.4, 6.5 | V7, V8 → 21/21 |
| T3 24/11 | — | adventure_works: raw vault 3–4 thực thể bằng automate_dv trên Snowflake |
| T4 25/11 | 6.6 | Thí nghiệm ADR (file 05 của lab), viết ADR 0001 |

**Tuần 7 — Performance playbook** (thí nghiệm: [bai-tap-performance](../bai-tap-performance/README.md))

| Ngày | Sáng | Chiều |
|---|---|---|
| T5 26/11 | 7.1, 7.2 | Đăng ký Snowflake trial nếu cần; S0 setup, S1 |
| T6 27/11 | 7.3 | S2, S3 |
| T7 28/11 | 7.4 | B1 |
| CN 29/11 | Ôn | S4 (ACCOUNT_USAGE có độ trễ, chạy sau 1 ngày) |
| T2 30/11 | 7.5 | B2, B3 |
| T3 01/12 | 7.6 | Viết playbook |
| T4 02/12 | Ôn cả GĐ2 bằng [cau-hoi-on-tap.md](cau-hoi-on-tap.md) | Hoàn thiện README 2 project, checklist mốc |

## Checklist mốc 2/12

**Kimball (tuần 4)**
- [ ] Lab: 13/13 bài K PASS qua `replay.sh`
- [ ] adventure_works: bus matrix (README + `bus_matrix.yml`), grain trong description mọi fact
- [ ] adventure_works: ≥ 1 accumulating snapshot, ≥ 1 bridge (`SalesOrderHeaderSalesReason`), ≥ 1 factless (`SpecialOfferProduct`), drill-across chỉ tiêu vs thực tế

**BigQuery + CD (tuần 5)**
- [ ] Repo `thelook-analytics` public: 3 môi trường, CI + CD + cleanup xanh, WIF (không key)
- [ ] ADR 0002: môi trường và chiến lược deploy

**Data Vault (tuần 6)**
- [ ] Lab: 21/21 PASS qua `replay.sh`
- [ ] adventure_works: raw vault 3–4 thực thể bằng automate_dv, test unique `(HK, LOAD_DATETIME)`
- [ ] ADR 0001: Data Vault hay Kimball, có số đo

**Performance (tuần 7)**
- [ ] `docs/performance-playbook.md` có ≥ 8 dòng nhật ký thí nghiệm thật (Snowflake + BigQuery)
- [ ] Resource monitor (Snowflake), `maximum_bytes_billed` + quota (BigQuery) đang bật
- [ ] Job label / query_tag để biết chi phí theo model

## Ghi chú phiên bản (kiểm chứng ngày 26/10/2026)

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| dbt-core / dbt-duckdb / duckdb (lab) | 1.12.6 / 1.11.0 / 1.5.6 | Ghim `duckdb<2`: DuckDB 2.0 vừa ra 21/10/2026, dbt-duckdb chưa kiểm thử với bản này |
| automate_dv | 0.11.5 | Lab chạy trên DuckDB nhờ shim; trên Snowflake/BigQuery dùng trực tiếp |
| dbt-bigquery | 1.12.1 | Project mẫu thelook đã `dbt parse` được |
| sqlfluff | 4.x | |
| GitHub Actions | `actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v7`, `google-github-actions/auth@v3`, `setup-gcloud@v3` | 3 workflow mẫu qua `actionlint` 1.7.12 |
| dbt-snowflake (adventure_works) | ≥ 1.10.6 | Snowflake tăng kích thước mặc định của cột chuỗi/binary; bản dbt-snowflake cũ hơn có thể lỗi với incremental + `on_schema_change='sync_all_columns'` trên cột có collation |
