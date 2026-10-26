# Bước 2 — Khởi tạo dbt project trên máy (target dev)

> Lý thuyết: [5.3 Ba môi trường](../../GD2-ly-thuyet/tuan-5/03-ba-moi-truong-dev-staging-prod.md)

## 1. Repo và môi trường Python

```bash
mkdir -p ~/Desktop/thelook-analytics && cd ~/Desktop/thelook-analytics
git init -b main

# copy file mẫu
cp -r ~/Desktop/target_ae/bai-tap-bigquery-thelook/templates/. .
ls -la        # thấy: dbt_project.yml profiles.yml packages.yml requirements.txt .sqlfluff .gitignore macros/ models/ .github/ scripts/

uv venv && source .venv/bin/activate          # hoặc python -m venv .venv
uv pip install -r requirements.txt            # dbt-core, dbt-bigquery, sqlfluff
dbt --version
```

## 2. Biến môi trường cho dev

Thêm vào `~/.bashrc` (hoặc file `.env` bạn tự `source`, **không commit**):

```bash
export DBT_PROFILES_DIR=.            # profiles.yml nằm trong repo
export GCP_PROJECT_NONPROD=thelook-ae-dev
export DBT_USER=duc                  # → dataset dbt_duc, dbt_duc_staging, dbt_duc_marts
```

## 3. Kiểm tra kết nối

```bash
dbt deps
dbt debug            # "All checks passed!"
```

Lỗi hay gặp:

| Lỗi | Sửa |
|---|---|
| `Env var required but not provided: 'GCP_PROJECT_NONPROD'` | Chưa `export` biến |
| `Could not find default credentials` / `Reauthentication is needed` | `gcloud auth application-default login` |
| `Access Denied: Project ...: User does not have bigquery.jobs.create` | Sai project id, hoặc tài khoản chưa có quyền trên project |

## 4. Model staging đầu tiên

`models/staging/thelook/stg_thelook__orders.sql`:

```sql
with source as (
    select * from {{ source('thelook', 'orders') }}
),

renamed as (
    select
        order_id,
        user_id                         as customer_id,
        lower(status)                   as order_status,
        num_of_item                     as item_count,
        created_at                      as order_created_at,
        shipped_at,
        delivered_at,
        returned_at
    from source
)

select * from renamed
{{ limit_in_dev('order_created_at') }}
```

(Kiểm tra tên cột bằng query ở bước 1 trước khi viết.)

```bash
dbt build -s stg_thelook__orders
dbt show -s stg_thelook__orders --limit 5
```

Mở console BigQuery: thấy dataset **`dbt_duc_staging`** trong project dev, location `US`. Thử `DBT_TARGET=prod dbt ls -s stg_thelook__orders --output json --output-keys "name schema"` để xem tên dataset ở prod (chỉ liệt kê, không build).

## 5. Commit đầu tiên

```bash
git add . && git commit -m "init thelook dbt project"
# tạo repo trên GitHub (public), rồi:
git remote add origin git@github.com:<you>/thelook-analytics.git
git push -u origin main
```

Kiểm tra `git status` trước khi commit: không có `target/`, `dbt_packages/`, `.venv/`, file key nào.

## ✅ Xong bước 2 khi

- [ ] `dbt debug` xanh
- [ ] `stg_thelook__orders` build được vào `dbt_<ten>_staging`
- [ ] `limit_in_dev` hoạt động (đếm dòng ở dev nhỏ hơn bảng gốc)
- [ ] Repo đã push lên GitHub
