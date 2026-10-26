# Thực hành tuần 5: Project 2 trên BigQuery (`thelook_ecommerce`) với 3 môi trường và CD

Đây là **project portfolio thứ 2** của bạn, chạy trên BigQuery thật (không phải lab giả lập). Folder này không phải là project: nó là **bộ hướng dẫn + file mẫu** để bạn dựng project trong **một repo GitHub mới** (vd `thelook-analytics`).

Lý thuyết: GĐ2 tuần 5 — [5.1](../GD2-ly-thuyet/tuan-5/01-bigquery-cho-nguoi-dung-dbt.md) · [5.2](../GD2-ly-thuyet/tuan-5/02-thelook-ecommerce.md) · [5.3](../GD2-ly-thuyet/tuan-5/03-ba-moi-truong-dev-staging-prod.md) · [5.4](../GD2-ly-thuyet/tuan-5/04-cd-github-actions.md).

## Kết quả cuối tuần

```
Máy bạn (dev)            GitHub                                  Google Cloud
─────────────            ──────                                  ────────────
dbt build --target dev ─────────────────────────────────────────▶ project NON-PROD: dataset dbt_<ten>_*
git push nhánh feature ─▶ PR ─▶ ci.yml (lint + slim CI) ────────▶ project NON-PROD: dataset ci_pr_<N>_*
                          merge ─▶ cd.yml (deploy) ─────────────▶ project PROD: dataset staging, marts
                                    └──▶ manifest.json ─────────▶ GCS bucket (trạng thái prod)
                          PR đóng ─▶ cleanup.yml ───────────────▶ xoá dataset ci_pr_<N>_*
```

- [ ] Repo `thelook-analytics` public, README có kiến trúc, bus matrix, cách chạy, chi phí
- [ ] Staging cho 7 bảng thelook, marts theo bus matrix (ít nhất `fct_order_items`, `fct_order_fulfillment`, `fct_events`, 3–4 dimension)
- [ ] 3 target `dev` / `ci` / `prod`, đặt tên dataset theo môi trường
- [ ] CI xanh trên PR, CD tự deploy prod khi merge, dataset PR tự xoá khi PR đóng
- [ ] Xác thực bằng Workload Identity Federation (không có key JSON nào)
- [ ] ADR 0002: môi trường và chiến lược deploy

## Các bước

| Bước | File | Thời gian gợi ý |
|---|---|---|
| 1 | [huong-dan/01-gcp-billing-va-an-toan-chi-phi.md](huong-dan/01-gcp-billing-va-an-toan-chi-phi.md) | 2h |
| 2 | [huong-dan/02-khoi-tao-dbt-project.md](huong-dan/02-khoi-tao-dbt-project.md) | 4h |
| 3 | [huong-dan/03-mo-hinh-thelook.md](huong-dan/03-mo-hinh-thelook.md) | 8–12h |
| 4 | [huong-dan/04-service-account-va-wif.md](huong-dan/04-service-account-va-wif.md) | 2h |
| 5 | [huong-dan/05-ci-cd-github-actions.md](huong-dan/05-ci-cd-github-actions.md) | 4h |
| 6 | [huong-dan/06-kiem-tra-va-dua-vao-portfolio.md](huong-dan/06-kiem-tra-va-dua-vao-portfolio.md) | 2h |

## File mẫu (`templates/`)

| File | Copy vào repo mới tại | Ghi chú |
|---|---|---|
| `requirements.txt` | `requirements.txt` | dbt-core, dbt-bigquery, sqlfluff |
| `profiles.yml` | `profiles.yml` | 3 target, đọc biến môi trường, không có bí mật |
| `dbt_project.yml` | `dbt_project.yml` | Cấu hình theo folder, job label |
| `packages.yml` | `packages.yml` | |
| `.sqlfluff` | `.sqlfluff` | dialect bigquery, templater dbt |
| `macros/*.sql` | `macros/` | `generate_schema_name`, `limit_in_dev`, `query_comment` |
| `models/staging/thelook/_thelook__sources.yml` | cùng đường dẫn | Khai báo 7 bảng |
| `.github/workflows/*.yml` | `.github/workflows/` | `ci.yml`, `cd.yml`, `cleanup.yml` |
| `scripts/setup_gcp.sh` | `scripts/` | Lệnh `gcloud` tạo service account, WIF, bucket, phân quyền |
| `.gitignore` | `.gitignore` | |

Đã kiểm tra trước khi giao: các workflow qua `actionlint`; project mẫu `dbt parse` được với dbt-bigquery 1.12. **Chưa** chạy được trên một tài khoản GCP thật (không có tài khoản để thử): khi gặp lỗi, đọc kỹ thông báo, đối chiếu tài liệu ở cuối mỗi bước.

## An toàn chi phí (đọc trước khi làm)

- Bật billing bằng **free trial**, tạo **budget alert** ngay (bước 1).
- `maximum_bytes_billed` có sẵn trong `profiles.yml` mẫu cho cả 3 target.
- Dataset public thelook nhỏ; cả tuần làm thường nằm trong 1 TiB miễn phí của tháng. Kiểm tra chi phí bằng query ở [7.5](../GD2-ly-thuyet/tuan-7/05-bigquery-do-chi-phi-information-schema.md).
