# Bước 1 — Tài khoản Google Cloud, billing và an toàn chi phí

> Lý thuyết: [5.1 BigQuery cho người dùng dbt](../../GD2-ly-thuyet/tuan-5/01-bigquery-cho-nguoi-dung-dbt.md)

## 1. Vì sao không dùng sandbox

BigQuery sandbox (không cần thẻ) **không hỗ trợ DML**: không `INSERT`, `UPDATE`, `DELETE`, `MERGE`. dbt-bigquery dùng `MERGE` cho model incremental và snapshot → không chạy được. Bảng trong sandbox cũng tự xoá sau 60 ngày. Project portfolio cần billing thật.

## 2. Tạo tài khoản và billing

1. Vào Google Cloud console bằng tài khoản Google cá nhân, đăng ký **Free Trial** (tài khoản mới: 300 USD dùng trong 90 ngày; cần thẻ để xác minh).
2. **Billing → Budgets & alerts → Create budget**: phạm vi toàn billing account, số tiền 5 USD, cảnh báo ở 50%, 90%, 100%. Budget chỉ **gửi email**, không tự chặn chi tiêu; chặn bằng `maximum_bytes_billed` (bước 2) và quota.
3. Tạo 2 project (hoặc 3, theo ADR của bạn — [5.3](../../GD2-ly-thuyet/tuan-5/03-ba-moi-truong-dev-staging-prod.md)):

| Project | Dùng cho |
|---|---|
| `thelook-ae-dev` (tên tuỳ bạn, phải duy nhất toàn cầu) | dev + CI |
| `thelook-ae-prod` | prod |

Gắn cả 2 project vào billing account vừa tạo.

## 3. (Khuyên làm) Giới hạn quota query theo ngày

IAM & Admin → **Quotas** → lọc "BigQuery API" → **Query usage per day** của project dev → đặt 200 GiB. Vượt ngưỡng thì query bị từ chối cho tới hôm sau. Đây là rào chắn **chặn được** chi tiêu (khác budget alert).

## 4. Cài gcloud và đăng nhập

```bash
# Ubuntu: theo hướng dẫn chính thức (apt hoặc tarball): https://cloud.google.com/sdk/docs/install
gcloud init                                   # chọn project dev
gcloud auth login                             # đăng nhập cho lệnh gcloud
gcloud auth application-default login        # đăng nhập cho THƯ VIỆN (dbt-bigquery dùng cái này)
```

## 5. Làm quen dữ liệu (console BigQuery)

Chạy trong project dev, ghi kết quả vào nháp README:

```sql
select table_id, row_count, round(size_bytes / pow(1024, 2), 1) as size_mb
from `bigquery-public-data.thelook_ecommerce.__TABLES__`
order by size_bytes desc;

select table_name, column_name, data_type
from `bigquery-public-data.thelook_ecommerce.INFORMATION_SCHEMA.COLUMNS`
order by table_name, ordinal_position;
```

Trước khi chạy query lớn, nhìn góc phải trình soạn thảo: BigQuery hiện "This query will process X MB when run" (dry run, miễn phí).

## ✅ Xong bước 1 khi

- [ ] 2 project có billing, budget alert đã tạo
- [ ] `gcloud auth application-default login` thành công
- [ ] Đã ghi số dòng / dung lượng 7 bảng thelook
