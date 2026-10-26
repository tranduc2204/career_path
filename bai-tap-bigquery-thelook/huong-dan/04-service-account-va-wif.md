# Bước 4 — Service account và Workload Identity Federation

> Lý thuyết: [5.3 phân quyền](../../GD2-ly-thuyet/tuan-5/03-ba-moi-truong-dev-staging-prod.md), [5.4 WIF](../../GD2-ly-thuyet/tuan-5/04-cd-github-actions.md)

## 1. Chạy script thiết lập

Mở `scripts/setup_gcp.sh`, sửa 5 biến đầu file (project, tài khoản GitHub, tên repo, tên bucket). Đọc **từng lệnh** trước khi chạy: script tạo tài nguyên và cấp quyền trên tài khoản của bạn.

```bash
gcloud auth login
bash scripts/setup_gcp.sh
```

Script làm:

| # | Việc | Kết quả |
|---|---|---|
| 0 | Bật API BigQuery, Storage, IAM, IAM Credentials, STS | |
| 1 | Tạo `sa-dbt-ci` (project dev) và `sa-dbt-prod` (project prod) | |
| 2 | Cấp quyền BigQuery | CI: chạy job + tạo/xoá dataset ở dev, **chỉ đọc** prod. Prod: chạy job + ghi prod |
| 3 | Tạo bucket `<project-prod>-dbt-state` | Nơi lưu `manifest.json` của prod |
| 4 | Pool + provider WIF, chỉ nhận token của repo bạn | |
| 4 | Cho `sa-dbt-ci` nhận token của **mọi workflow** trong repo | |
| 4 | Cho `sa-dbt-prod` **chỉ** nhận token của job trong environment `production` | Nhánh feature không thể ghi prod |

Cuối script in ra 6 giá trị để đưa vào GitHub.

## 2. Cấu hình GitHub

**Settings → Secrets and variables → Actions → tab Variables** (không phải Secrets): tạo `GCP_PROJECT_NONPROD`, `GCP_PROJECT_PROD`, `WIF_PROVIDER`, `SA_CI`, `SA_PROD`, `STATE_BUCKET`.

**Settings → Environments → New environment** tên `production`:
- *Deployment branches and tags* → **Selected branches and tags** → thêm `main`.
- (Tuỳ chọn) *Required reviewers*: bắt chính bạn bấm duyệt trước mỗi lần deploy prod. Hay để demo, nhưng sẽ làm job lịch hằng ngày chờ duyệt.

**Settings → Branches → Add branch ruleset** (hoặc branch protection) cho `main`:
- Require a pull request before merging.
- Require status checks to pass: chọn job `dbt-ci` (xuất hiện sau khi CI chạy lần đầu).

## 3. Kiểm tra quyền bằng tay (tuỳ chọn nhưng nên làm)

Impersonate service account CI từ máy bạn để chắc quyền đúng trước khi debug trên GitHub:

```bash
gcloud projects add-iam-policy-binding "$GCP_PROJECT_NONPROD" \
  --member="user:$(gcloud config get-value account)" --role="roles/iam.serviceAccountTokenCreator"

bq ls --project_id="$GCP_PROJECT_PROD" \
  --impersonate_service_account="sa-dbt-ci@${GCP_PROJECT_NONPROD}.iam.gserviceaccount.com"   # đọc prod: được
```

Hoặc dùng `impersonate_service_account` trong `profiles.yml` (target dev) để chạy dbt với đúng quyền của CI.

## Lỗi hay gặp

| Lỗi trên GitHub Actions | Nguyên nhân |
|---|---|
| `Unable to get ACTIONS_ID_TOKEN_REQUEST_URL` | Thiếu `permissions: id-token: write` |
| `The given credential is rejected by the attribute condition` | `attribute-condition` sai owner/repo (phân biệt hoa thường) |
| `Permission 'iam.serviceAccounts.getAccessToken' denied` | Thiếu binding `workloadIdentityUser`, hoặc job CD **không** khai báo `environment: production`, hoặc mới tạo < 5 phút |
| `Access Denied: ... bigquery.datasets.delete` (cleanup) | CI thiếu `roles/bigquery.dataOwner` ở project dev |

Tài liệu xử lý lỗi của action: https://github.com/google-github-actions/auth/blob/main/docs/TROUBLESHOOTING.md

## ✅ Xong bước 4 khi

- [ ] Script chạy hết, 6 biến đã nằm trong GitHub Variables
- [ ] Environment `production` chỉ cho nhánh `main`
- [ ] Branch protection cho `main`
