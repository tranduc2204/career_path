# GĐ1 — Lý thuyết (15/10 → 4/11/2026)

> Mục tiêu GĐ1: xong Phase 2, đạt mức **Junior AE** trên project `adventure_works`.
> Giả định: dbt Core ≥ 1.8 (dùng key `data_tests:`). Chỗ nào khác giữa các phiên bản có ghi chú riêng.

## Bản đồ khái niệm

```
                         ┌─────────────── TUẦN 3: "Vận hành như production" ───────────────┐
                         │  sqlfluff · pre-commit/dbt-checkpoint · GitHub Actions slim CI  │
                         │  docs → GitHub Pages · contracts · exposures · freshness        │
                         └───────────────────────────────┬─────────────────────────────────┘
                                                         │ bảo vệ & công bố
┌──────── TUẦN 1: "Cấu trúc" ────────┐      ┌────────── TUẦN 2: "Dữ liệu thay đổi theo thời gian" ─────────┐
│ staging → intermediate → marts      │ ───▶ │ incremental (append / merge / delete+insert)                  │
│ packages: dbt-utils, codegen,       │      │ late-arriving data · backfill                                 │
│           dbt-expectations          │      │ snapshot (timestamp / check) = SCD Type 2                     │
│ Jinja + thư viện 5 macro            │      │ custom generic test                                           │
└─────────────────────────────────────┘      └───────────────────────────────────────────────────────────────┘
```

## Mục lục

### Tuần 1 (15–21/10) — Cấu trúc project
| # | File | Khái niệm chính |
|---|---|---|
| 1.1 | [tuan-1/01-phan-tang-staging-intermediate-marts.md](tuan-1/01-phan-tang-staging-intermediate-marts.md) | Layering, naming convention, materialization theo tầng |
| 1.2 | [tuan-1/02-dbt-packages.md](tuan-1/02-dbt-packages.md) | `packages.yml`, dbt-utils, codegen, dbt-expectations |
| 1.2+ | [tuan-1/packages/](tuan-1/packages/README.md) | Học sâu: [dbt-utils](tuan-1/packages/01-dbt-utils.md) · [codegen](tuan-1/packages/02-codegen.md) · [dbt-expectations](tuan-1/packages/03-dbt-expectations.md) |
| 1.3 | [tuan-1/03-jinja-va-macro.md](tuan-1/03-jinja-va-macro.md) | Jinja, macro, `run-operation`, `generate_schema_name`, gợi ý 5 macro |

### Tuần 2 (22–28/10) — Dữ liệu theo thời gian
| # | File | Khái niệm chính |
|---|---|---|
| 2.1 | [tuan-2/01-incremental-models.md](tuan-2/01-incremental-models.md) | `is_incremental()`, `unique_key`, append / merge / delete+insert, microbatch |
| 2.2 | [tuan-2/02-late-arriving-data-va-backfill.md](tuan-2/02-late-arriving-data-va-backfill.md) | Lookback window, late-arriving fact/dimension, backfill, `--full-refresh` |
| 2.3 | [tuan-2/03-snapshots-scd2.md](tuan-2/03-snapshots-scd2.md) | SCD Type 2, timestamp vs check strategy, hard deletes |
| 2.4 | [tuan-2/04-custom-generic-tests.md](tuan-2/04-custom-generic-tests.md) | Singular vs generic test, viết test có tham số, severity |

### Tuần 3 (29/10–4/11) — Chất lượng & CI/CD
| # | File | Khái niệm chính |
|---|---|---|
| 3.1 | [tuan-3/01-sqlfluff.md](tuan-3/01-sqlfluff.md) | Linter, templater dbt vs jinja, `.sqlfluff` |
| 3.2 | [tuan-3/02-github-actions-slim-ci.md](tuan-3/02-github-actions-slim-ci.md) | CI, `manifest.json`, `state:modified+`, `--defer` |
| 3.3 | [tuan-3/03-dbt-docs-github-pages.md](tuan-3/03-dbt-docs-github-pages.md) | `dbt docs generate`, artifacts, deploy Pages |
| 3.4 | [tuan-3/04-model-contracts.md](tuan-3/04-model-contracts.md) | Contract, constraints, khác gì với test |
| 3.5 | [tuan-3/05-exposures.md](tuan-3/05-exposures.md) | Downstream consumers trong lineage |
| 3.6 | [tuan-3/06-source-freshness.md](tuan-3/06-source-freshness.md) | `loaded_at_field`, warn/error, `source_status:fresher+` |
| 3.7 | [tuan-3/07-pre-commit-dbt-checkpoint.md](tuan-3/07-pre-commit-dbt-checkpoint.md) | Git hooks, quy chuẩn tự động trước khi commit |

### Tổng hợp
- [cau-hoi-on-tap.md](cau-hoi-on-tap.md) — câu hỏi tự kiểm tra / phỏng vấn Junior cho cả GĐ1.

### Thực hành
- [../bai-tap-incremental-scd2-jinja/](../bai-tap-incremental-scd2-jinja/README.md) — lab dbt + DuckDB có tự chấm: 38 bài từ cơ bản (tự dựng staging) → Jinja, incremental, snapshot, SCD2 → 6 sự cố production thật, dữ liệu thay đổi qua 12 "ngày".

## Cách dùng trong lịch ngày

- **07:30–11:30 (lý thuyết):** đọc file của khái niệm hôm đó + link docs chính thức ở cuối file.
- **13:00–17:00 (build):** làm phần "Áp dụng vào adventure_works" ở mỗi file.
- **20:30–22:30 (tổng kết):** trả lời phần "Câu hỏi tự kiểm tra" không nhìn tài liệu; câu nào sai thì ghi lại.

## Checklist mốc 4/11

- [ ] Project có 3 tầng rõ ràng, materialization cấu hình theo folder
- [ ] 3 package cài và có dùng thật (không chỉ cài)
- [ ] 5 macro có docs + được gọi ở ít nhất 1 model
- [ ] Mỗi chiến lược incremental có ít nhất 1 model minh hoạ + README giải thích lý do chọn
- [ ] 2 snapshot: 1 timestamp, 1 check
- [ ] ≥ 2 custom generic test
- [ ] CI chạy sqlfluff + slim CI trên mỗi PR, xanh
- [ ] Docs public trên GitHub Pages
- [ ] Contracts cho các mart quan trọng, ≥ 1 exposure, freshness cho sources
- [ ] pre-commit chạy được local
- [ ] CV: sửa lỗi lệch ngày Estuary, đưa adventure_works lên đầu portfolio
