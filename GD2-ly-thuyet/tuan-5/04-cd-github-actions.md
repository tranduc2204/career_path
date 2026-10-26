# 5.4 CI/CD với GitHub Actions: merge vào `main` là tự deploy prod

> GĐ1 (3.2) đã làm CI (lint + slim CI) cho adventure_works. Tuần này hoàn thiện vòng đời: **CI theo PR → CD khi merge → dọn dẹp khi PR đóng**, xác thực **không dùng key** (Workload Identity Federation).

## Toàn cảnh

```
            mở / cập nhật PR                          merge vào main                    PR đóng
                  │                                         │                               │
                  ▼                                         ▼                               ▼
   ┌─────────── ci.yml ───────────┐        ┌──────────── cd.yml ────────────┐   ┌── cleanup.yml ──┐
   │ 1. sqlfluff lint             │        │ environment: production        │   │ xoá mọi dataset │
   │ 2. auth = sa-dbt-ci (WIF)    │        │ 1. auth = sa-dbt-prod (WIF)    │   │ ci_pr_<số PR>_* │
   │ 3. tải manifest PROD từ GCS  │──so───▶│ 2. tải manifest prod lần trước │   └─────────────────┘
   │ 4. dbt build --target ci     │        │ 3. dbt build --target prod     │
   │    -s state:modified+        │        │    -s state:modified+          │
   │    --defer --state prod-state│        │ 4. OK → ghi manifest MỚI lên   │
   │    vào dataset ci_pr_<N>_*   │        │    GCS (chuẩn so sánh cho CI)  │
   └──────────────────────────────┘        │ (+ lịch hằng ngày: build đủ)   │
                                           └────────────────────────────────┘
```

Manifest prod nằm ở **GCS** (`gs://<bucket>/prod/manifest.json`). Đó là "trạng thái prod" mà CI so sánh để biết model nào đổi, và để `--defer` tới bảng prod.

## Xác thực: Workload Identity Federation (WIF)

| Cách | Mô tả | Rủi ro |
|---|---|---|
| Key JSON của service account lưu trong GitHub Secret | Đơn giản | Key sống lâu, lộ là mất. Phải xoay vòng (rotate) tay |
| **WIF** (khuyên dùng) | GitHub Actions đưa token OIDC ngắn hạn, Google đổi lấy credential tạm của service account | Không có bí mật dài hạn nào để lộ |

Thiết lập một lần bằng `gcloud` (đầy đủ ở [bai-tap-bigquery-thelook](../../bai-tap-bigquery-thelook/README.md)):

```sh
# 1. Pool
gcloud iam workload-identity-pools create "github" \
  --project="${PROJECT_ID}" --location="global" --display-name="GitHub Actions Pool"

# 2. Provider, CHỈ nhận token từ tài khoản GitHub của bạn
gcloud iam workload-identity-pools providers create-oidc "thelook-repo" \
  --project="${PROJECT_ID}" --location="global" --workload-identity-pool="github" \
  --display-name="thelook repo" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 3a. CI: mọi workflow của repo được "đóng vai" service account CI
gcloud iam service-accounts add-iam-policy-binding "sa-dbt-ci@${PROJECT_NONPROD}.iam.gserviceaccount.com" \
  --project="${PROJECT_NONPROD}" --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${REPO}"

# 3b. Prod: CHỈ job chạy trong GitHub Environment "production"
gcloud iam service-accounts add-iam-policy-binding "sa-dbt-prod@${PROJECT_PROD}.iam.gserviceaccount.com" \
  --project="${PROJECT_PROD}" --role="roles/iam.workloadIdentityUser" \
  --member="principal://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/subject/repo:${REPO}:environment:production"
```

Vì sao 3b chặt hơn: khi job khai báo `environment: production`, token OIDC của GitHub có `sub = repo:<owner>/<repo>:environment:production`. Đặt environment `production` chỉ cho nhánh `main` → một nhánh feature dù sửa workflow cũng **không** đổi được token sang service account prod. Nếu dùng `attribute.repository` cho cả prod (như 3a), bất kỳ workflow nào của repo, kể cả từ nhánh PR, cũng xin được quyền ghi prod.

Trong workflow:

```yaml
permissions:
  contents: read
  id-token: write          # BẮT BUỘC để GitHub cấp token OIDC

steps:
  - uses: google-github-actions/auth@v3
    with:
      workload_identity_provider: ${{ vars.WIF_PROVIDER }}   # projects/<SỐ>/locations/global/workloadIdentityPools/github/providers/thelook-repo
      service_account: ${{ vars.SA_CI }}                      # sa-dbt-ci@<project>.iam.gserviceaccount.com
```

Action đặt biến `GOOGLE_APPLICATION_CREDENTIALS` → dbt-bigquery `method: oauth` tự dùng (5.3).

Quyền và lan truyền: IAM của WIF có thể mất **tới 5 phút** mới có hiệu lực. Lỗi xác thực ngay sau khi tạo: chờ rồi chạy lại.

## Biến và bí mật trên GitHub

Với WIF, gần như không còn **secret**. Các giá trị cấu hình để ở **Variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Ví dụ |
|---|---|
| `GCP_PROJECT_NONPROD` | `thelook-ae-dev` |
| `GCP_PROJECT_PROD` | `thelook-ae-prod` |
| `WIF_PROVIDER` | `projects/123456789/locations/global/workloadIdentityPools/github/providers/thelook-repo` |
| `SA_CI`, `SA_PROD` | email 2 service account |
| `STATE_BUCKET` | `thelook-ae-dbt-state` |

## CI (pull request)

Điểm chính:

```yaml
on:
  pull_request:
    branches: [main]

concurrency:                                   # PR có commit mới → huỷ lần chạy cũ
  group: ci-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

```bash
# tải manifest prod; lần đầu chưa có thì build toàn bộ
if gcloud storage cp "gs://${STATE_BUCKET}/prod/manifest.json" prod-state/manifest.json; then
  dbt build --target ci --select state:modified+ --defer --state prod-state
else
  dbt build --target ci
fi
```

- `state:modified+`: model đổi + mọi model phía sau.
- `--defer`: model không được chọn → đọc **bảng prod** (CI SA cần quyền đọc prod).
- Dataset `ci_pr_<N>_*` riêng cho PR (target `ci`, biến `PR_NUMBER`).

Bật **branch protection** cho `main`: bắt buộc PR, bắt buộc job CI xanh.

## CD (merge vào main + lịch hằng ngày)

```yaml
on:
  push:
    branches: [main]
  schedule:
    - cron: "0 23 * * *"                       # 23:00 UTC = 06:00 giờ Việt Nam
  workflow_dispatch:                            # chạy tay khi cần

concurrency:
  group: deploy-prod
  cancel-in-progress: false                     # KHÔNG huỷ một lần deploy đang chạy

jobs:
  deploy:
    environment: production                     # protection rule: chỉ nhánh main, có thể bắt duyệt tay
```

| Sự kiện | Lệnh | Lý do |
|---|---|---|
| `push` vào `main` (có manifest cũ) | `dbt build --target prod -s state:modified+ --state prod-state` | Deploy nhanh đúng phần thay đổi. Không cần `--defer`: model không đổi đã nằm sẵn ở prod |
| `schedule`, `workflow_dispatch`, lần đầu | `dbt build --target prod` | Làm mới toàn bộ dữ liệu hằng ngày |

Sau khi build **thành công**:

```bash
gcloud storage cp target/manifest.json "gs://${STATE_BUCKET}/prod/manifest.json"
```

Build lỗi thì **không** ghi manifest: lần sau vẫn so với trạng thái prod cuối cùng còn đúng.

Tuỳ chọn: `dbt docs generate` rồi đẩy lên GitHub Pages (như GĐ1, 3.3); `dbt source freshness` trong job hằng ngày.

## Dọn dẹp khi PR đóng

```yaml
on:
  pull_request:
    types: [closed]
```

```bash
for ds in $(bq ls --project_id="${GCP_PROJECT_NONPROD}" --max_results=10000 --format=json \
            | jq -r '.[].datasetReference.datasetId' | grep -E "^ci_pr_${PR_NUMBER}(_|$)"); do
  bq rm -r -f -d "${GCP_PROJECT_NONPROD}:${ds}"
done
```

Không dọn → mỗi PR để lại vài dataset, tháng sau có hàng trăm dataset rác (tốn storage, khó nhìn).

## Rollback

| Tình huống | Cách |
|---|---|
| Deploy làm sai số liệu | `git revert` commit lỗi → merge → CD tự build lại model bị ảnh hưởng |
| Cần quay về bảng cũ ngay | BigQuery **time travel**: `create or replace table marts.fct_x as select * from marts.fct_x for system_time as of timestamp_sub(current_timestamp(), interval 2 hour)` (trong cửa sổ time travel, mặc định 7 ngày) |
| Deploy không gián đoạn (nâng cao) | **Blue/green**: build vào dataset mới, kiểm tra xong mới đổi view/consumer sang; `dbt clone` hỗ trợ trên BigQuery, Snowflake, Databricks |

## Lỗi hay gặp

- Quên `permissions: id-token: write` → `auth` báo không lấy được token OIDC.
- Provider WIF không có `attribute-condition` → repo bất kỳ cũng có thể xin token vào pool.
- Ghi manifest kể cả khi build lỗi → CI sau so với trạng thái sai.
- CD huỷ ngang (`cancel-in-progress: true`) → bảng prod nửa vời.
- CI dùng target `prod` "cho tiện".
- Không có job dọn dataset PR.
- Lịch cron hiểu nhầm múi giờ (GitHub dùng UTC).

## Áp dụng vào project thelook

File mẫu đầy đủ (đã kiểm tra bằng `actionlint`): [bai-tap-bigquery-thelook/templates](../../bai-tap-bigquery-thelook/templates/).

- [ ] Thiết lập WIF + 2 service account + bucket state
- [ ] `ci.yml`, `cd.yml`, `cleanup.yml` chạy xanh
- [ ] Branch protection cho `main`; environment `production` chỉ cho nhánh `main`
- [ ] Demo trong README: ảnh chụp 1 PR (CI xanh, chỉ build model đổi) → merge → CD deploy → dataset PR bị xoá
- [ ] Viết ADR 0002: môi trường + chiến lược deploy

## Câu hỏi tự kiểm tra

1. Vẽ lại vòng đời PR → CI → merge → CD → dọn dẹp.
2. Vì sao WIF an toàn hơn key JSON? Thiết lập WIF gồm những bước nào?
3. Manifest prod lưu ở đâu, ai ghi, ai đọc, ghi khi nào?
4. Vì sao CD khi merge không cần `--defer`?
5. `concurrency` của CI và CD khác nhau thế nào? Vì sao?
6. Deploy làm sai số liệu: bạn rollback thế nào?

## Tài liệu

- google-github-actions/auth (WIF, ví dụ, xử lý lỗi): https://github.com/google-github-actions/auth
- GitHub Actions — Using environments for deployment: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment
- dbt — Defer: https://docs.getdbt.com/reference/node-selection/defer
- dbt — `dbt clone`: https://docs.getdbt.com/reference/commands/clone
- BigQuery — Time travel: https://docs.cloud.google.com/bigquery/docs/time-travel
- GĐ1: [3.2 GitHub Actions & slim CI](../../GD1-ly-thuyet/tuan-3/02-github-actions-slim-ci.md)
