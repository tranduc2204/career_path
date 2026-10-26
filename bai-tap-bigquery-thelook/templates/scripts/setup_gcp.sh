#!/usr/bin/env bash
# =====================================================================================================
# Thiết lập Google Cloud cho project thelook: service account, phân quyền, bucket trạng thái,
# Workload Identity Federation (GitHub Actions xác thực không cần key).
#
# Chạy MỘT LẦN trên máy đã cài gcloud và đăng nhập bằng tài khoản có quyền Owner trên cả 2 project:
#     gcloud auth login
#     bash scripts/setup_gcp.sh
#
# Trước khi chạy: 2 project đã được tạo và gắn billing (xem huong-dan/01).
# Lệnh "create" chạy lần 2 sẽ báo "already exists": bình thường, đọc lỗi rồi chạy tiếp các lệnh sau bằng tay.
# =====================================================================================================
set -euo pipefail

# ---------- SỬA CÁC GIÁ TRỊ NÀY ----------
PROJECT_NONPROD="thelook-ae-dev"             # project cho dev + CI
PROJECT_PROD="thelook-ae-prod"               # project cho prod
GITHUB_OWNER="tranduc2204"                  # tài khoản GitHub chứa repo (đúng chữ hoa/thường)
REPO="${GITHUB_OWNER}/thelook-analytics"     # owner/repo
STATE_BUCKET="${PROJECT_PROD}-dbt-state"     # tên bucket phải duy nhất trên toàn GCS
# -----------------------------------------

SA_CI="sa-dbt-ci@${PROJECT_NONPROD}.iam.gserviceaccount.com"
SA_PROD="sa-dbt-prod@${PROJECT_PROD}.iam.gserviceaccount.com"

echo "== 0. Bật các API cần dùng"
for p in "${PROJECT_NONPROD}" "${PROJECT_PROD}"; do
  gcloud services enable bigquery.googleapis.com storage.googleapis.com iam.googleapis.com \
    iamcredentials.googleapis.com sts.googleapis.com --project="${p}"
done

echo "== 1. Service account"
gcloud iam service-accounts create sa-dbt-ci --project="${PROJECT_NONPROD}" --display-name="dbt CI (GitHub Actions)"
gcloud iam service-accounts create sa-dbt-prod --project="${PROJECT_PROD}" --display-name="dbt prod deploy (GitHub Actions)"

echo "== 2. Quyền BigQuery (least privilege)"
# CI: chạy job + tạo/xoá dataset ci_pr_* ở non-prod; chỉ ĐỌC prod (cho --defer)
gcloud projects add-iam-policy-binding "${PROJECT_NONPROD}" --member="serviceAccount:${SA_CI}" --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding "${PROJECT_NONPROD}" --member="serviceAccount:${SA_CI}" --role="roles/bigquery.dataOwner"
gcloud projects add-iam-policy-binding "${PROJECT_PROD}" --member="serviceAccount:${SA_CI}" --role="roles/bigquery.dataViewer"
# Prod: chạy job + ghi dữ liệu ở prod
gcloud projects add-iam-policy-binding "${PROJECT_PROD}" --member="serviceAccount:${SA_PROD}" --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding "${PROJECT_PROD}" --member="serviceAccount:${SA_PROD}" --role="roles/bigquery.dataEditor"

echo "== 3. Bucket lưu manifest prod"
gcloud storage buckets create "gs://${STATE_BUCKET}" --project="${PROJECT_PROD}" --location=US --uniform-bucket-level-access
gcloud storage buckets add-iam-policy-binding "gs://${STATE_BUCKET}" --member="serviceAccount:${SA_PROD}" --role="roles/storage.objectAdmin"
gcloud storage buckets add-iam-policy-binding "gs://${STATE_BUCKET}" --member="serviceAccount:${SA_CI}" --role="roles/storage.objectViewer"

echo "== 4. Workload Identity Federation (đặt ở project prod)"
gcloud iam workload-identity-pools create "github" \
  --project="${PROJECT_PROD}" --location="global" --display-name="GitHub Actions Pool"

WIP_ID=$(gcloud iam workload-identity-pools describe "github" \
  --project="${PROJECT_PROD}" --location="global" --format="value(name)")

# Attribute condition: chỉ token phát cho repo của bạn mới được vào pool
gcloud iam workload-identity-pools providers create-oidc "thelook-repo" \
  --project="${PROJECT_PROD}" --location="global" --workload-identity-pool="github" \
  --display-name="thelook repo" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_OWNER}' && assertion.repository == '${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# CI: mọi workflow của repo được đóng vai sa-dbt-ci
gcloud iam service-accounts add-iam-policy-binding "${SA_CI}" --project="${PROJECT_NONPROD}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WIP_ID}/attribute.repository/${REPO}"

# Prod: CHỈ job chạy trong GitHub Environment "production" (sub = repo:<owner>/<repo>:environment:production).
# Kết hợp với rule "chỉ nhánh main" của environment → nhánh feature / PR không bao giờ lấy được quyền ghi prod.
gcloud iam service-accounts add-iam-policy-binding "${SA_PROD}" --project="${PROJECT_PROD}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principal://iam.googleapis.com/${WIP_ID}/subject/repo:${REPO}:environment:production"

WIF_PROVIDER=$(gcloud iam workload-identity-pools providers describe "thelook-repo" \
  --project="${PROJECT_PROD}" --location="global" --workload-identity-pool="github" --format="value(name)")

cat <<EOF

=====================================================================================
XONG. Vào GitHub repo → Settings → Secrets and variables → Actions → tab "Variables",
tạo các biến sau (không có secret nào cả):

  GCP_PROJECT_NONPROD = ${PROJECT_NONPROD}
  GCP_PROJECT_PROD    = ${PROJECT_PROD}
  WIF_PROVIDER        = ${WIF_PROVIDER}
  SA_CI               = ${SA_CI}
  SA_PROD             = ${SA_PROD}
  STATE_BUCKET        = ${STATE_BUCKET}

Rồi Settings → Environments → New environment "production"
  → Deployment branches and tags: Selected branches → thêm "main".

Quyền IAM của WIF có thể mất tới 5 phút mới có hiệu lực.
=====================================================================================
EOF
