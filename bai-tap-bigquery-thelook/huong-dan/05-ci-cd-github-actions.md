# Bước 5 — CI/CD với GitHub Actions

> Lý thuyết: [5.4 CI/CD](../../GD2-ly-thuyet/tuan-5/04-cd-github-actions.md)

Ba workflow đã nằm sẵn trong `.github/workflows/` (copy từ `templates/` ở bước 2):

| File | Chạy khi | Làm gì |
|---|---|---|
| `ci.yml` | Mở / cập nhật PR vào `main` | Lint SQL đã đổi, `dbt build -s state:modified+ --defer` vào `ci_pr_<N>_*` |
| `cd.yml` | Push vào `main`, 06:00 hằng ngày, chạy tay | Deploy prod, lưu `manifest.json` lên GCS |
| `cleanup.yml` | PR đóng | Xoá dataset `ci_pr_<N>_*` |

## 1. Deploy prod lần đầu (tạo trạng thái prod)

CI cần `manifest.json` của prod để so sánh. Lần đầu chưa có:

1. Push code lên `main` (hoặc **Actions → CD → Run workflow**).
2. CD không tìm thấy manifest cũ → `dbt build` toàn bộ vào project prod → upload `gs://<bucket>/prod/manifest.json`.
3. Kiểm tra: console BigQuery project prod có dataset `staging`, `marts`; `gcloud storage ls gs://<bucket>/prod/`.

## 2. Demo một vòng PR (chụp ảnh cho README)

```bash
git checkout -b feat/add-gross-margin
# sửa 1 model, ví dụ thêm cột gross_margin vào fct_order_items
git commit -am "fct_order_items: add gross_margin" && git push -u origin feat/add-gross-margin
```

Mở PR trên GitHub và quan sát:

| Kiểm tra | Mong đợi |
|---|---|
| Job `dbt-ci` | Xanh. Log chỉ build `fct_order_items` + model phía sau, **không** build lại staging |
| BigQuery project dev | Có dataset `ci_pr_<N>_marts` chứa `fct_order_items` |
| Model upstream không đổi | Đọc từ project prod (xem SQL compile trong log: tên bảng `thelook-ae-prod.staging...`) |
| Đẩy thêm commit vào PR | Lần chạy cũ bị huỷ (`concurrency`) |

Merge PR:

| Kiểm tra | Mong đợi |
|---|---|
| Workflow `CD` | Chạy trong environment `production`, chỉ build `state:modified+` |
| GCS | `manifest.json` có thời gian mới |
| Workflow `Cleanup CI datasets` | Xoá `ci_pr_<N>_*` |

## 3. Thử phá để hiểu (nên làm)

1. Tạo PR sửa `cd.yml` bỏ `environment: production` → (đừng merge) chạy tay workflow đó trên nhánh của PR: bước auth **phải** lỗi vì token không có `environment:production`. Đây là bằng chứng nhánh feature không ghi được prod. Đóng PR.
2. Tạo PR có test đỏ (vd `accepted_values` sai) → CI đỏ → nút Merge bị khoá bởi branch protection.
3. Tạm hạ `maximum_bytes_billed` của target `ci` xuống `10000` (10 KB) → CI đỏ với lỗi *Query exceeded limit for bytes billed* → hiểu rào chắn chi phí. Trả lại giá trị cũ.

## 4. Theo dõi chi phí của CI/CD

Mỗi job có label `dbt_invocation_id`, `target_name`, `dbt_node` (từ `query_comment`). Query ở [7.5](../../GD2-ly-thuyet/tuan-7/05-bigquery-do-chi-phi-information-schema.md) cho biết CI tốn bao nhiêu so với prod.

## Lỗi hay gặp

| Lỗi | Sửa |
|---|---|
| CI build **toàn bộ** dù đã có manifest | Bước "Lấy manifest prod" lỗi quyền đọc bucket → kiểm tra `roles/storage.objectViewer` của `sa-dbt-ci` |
| `Not found: Table thelook-ae-prod:staging...` trong CI | Chưa deploy prod lần đầu, hoặc model mới chưa có ở prod mà không được chọn → kiểm tra selector |
| CD báo `state:modified` chọn 0 node | Đúng nếu commit chỉ sửa README; không có gì để deploy |
| Lint lỗi `Unable to load dbt project` | Thiếu biến môi trường cho target `ci` ở bước lint, hoặc chưa `dbt deps` |

## ✅ Xong bước 5 khi

- [ ] Lần deploy đầu tạo được prod + manifest
- [ ] 1 PR demo đi trọn vòng CI → merge → CD → cleanup, có ảnh chụp
- [ ] Đã thử ít nhất 1 thí nghiệm "phá để hiểu"
