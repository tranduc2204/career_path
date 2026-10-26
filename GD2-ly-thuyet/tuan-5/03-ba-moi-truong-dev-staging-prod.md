# 5.3 Ba môi trường: dev, staging, prod

## Vì sao cần tách môi trường

| Không tách | Hậu quả |
|---|---|
| Dev build thẳng vào bảng prod | Dashboard của sếp hiện số đang sửa dở |
| CI của 2 PR cùng ghi 1 dataset | PR này ghi đè bảng của PR kia, test xanh/đỏ ngẫu nhiên |
| Một service account làm mọi thứ | Lộ key = lộ quyền ghi prod; không biết ai/cái gì tiêu tiền |
| Không có prod "chuẩn" | Slim CI không có `manifest.json` để so (`state:modified`) |

## Ba môi trường và vai trò

| | **dev** | **staging** (CI) | **prod** |
|---|---|---|---|
| Ai chạy | Bạn, trên máy | GitHub Actions khi mở/cập nhật PR | GitHub Actions khi merge vào `main` + lịch hằng ngày |
| Ghi vào | Dataset riêng của bạn: `dbt_<ten>_*` | Dataset riêng **mỗi PR**: `ci_pr_<số PR>_*` | Dataset chuẩn: `staging`, `marts` |
| Build gì | Model đang sửa (`-s my_model+`) | `state:modified+` (+ `--defer` tới prod) | Toàn bộ (hằng ngày) / phần thay đổi (khi merge) |
| Dữ liệu | Có thể giới hạn (vd 30 ngày gần nhất) | Như dev | Đầy đủ |
| Xác thực | Tài khoản Google của bạn (`gcloud auth application-default login`) | Service account CI, qua Workload Identity Federation | Service account prod, qua WIF |
| Dọn dẹp | Tự xoá khi cần | Xoá dataset khi PR đóng (5.4) | Không bao giờ xoá |

Nhiều công ty có thêm một môi trường **staging dài hạn** (build đầy đủ từ nhánh `develop` hoặc ngay sau khi merge, chạy test nặng, rồi mới lên prod). Với project cá nhân, "staging = CI theo PR" là đủ và là cách dbt Labs khuyên dùng. Ghi lựa chọn của bạn vào **ADR 0002**.

## 1 GCP project hay nhiều project?

| Cách | Mô tả | Ưu | Nhược |
|---|---|---|---|
| **A. 1 project**, tách bằng tên dataset | `thelook-ae`: `dbt_duc_*`, `ci_pr_12_*`, `staging`, `marts` | Đơn giản, 1 chỗ cấu hình | Phân quyền phải làm tới từng dataset; khó tách chi phí; nhầm target là ghi vào prod |
| **B. 2 project**: non-prod và prod | `thelook-ae-dev` (dev + CI), `thelook-ae-prod` | Ranh giới quyền rõ ở cấp project; CI không có quyền ghi prod | Thêm 1 project |
| **C. 3 project**: dev, staging, prod | Giống mô hình ở công ty lớn | Tách bạch nhất, xem chi phí từng môi trường | Nhiều cấu hình nhất |

Gợi ý cho portfolio: **B** (hoặc C nếu muốn luyện). Điều nhà tuyển dụng muốn thấy: CI **không thể** ghi vào prod, prod **chỉ** được ghi bởi pipeline.

Mọi dataset phải ở **location `US`** (cùng chỗ với `bigquery-public-data.thelook_ecommerce`).

## Phân quyền tối thiểu (least privilege)

| Danh tính | Quyền | Ở đâu |
|---|---|---|
| Bạn (dev) | Owner hoặc `roles/bigquery.admin` | project non-prod |
| `sa-dbt-ci` (CI) | `roles/bigquery.jobUser` + `roles/bigquery.dataOwner` | project non-prod (chạy job, tạo **và xoá** dataset `ci_pr_*`; `dataEditor` tạo được nhưng không xoá được dataset) |
| | `roles/bigquery.dataViewer` | project prod (chỉ **đọc**, cho `--defer`) |
| | `roles/storage.objectViewer` | bucket chứa manifest prod |
| `sa-dbt-prod` (CD) | `roles/bigquery.jobUser` + `roles/bigquery.dataEditor` | project prod |
| | `roles/storage.objectAdmin` | bucket chứa manifest prod (ghi) |
| Người xem dashboard | `roles/bigquery.dataViewer` trên dataset `marts` | prod |

Đọc dữ liệu public (`bigquery-public-data`) không cần cấp quyền gì thêm; job chạy (và tính tiền) ở project của bạn.

## `profiles.yml`: một file, nhiều target, không chứa bí mật

```yaml
thelook:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth                       # dùng Application Default Credentials của gcloud
      project: "{{ env_var('GCP_PROJECT_NONPROD') }}"
      dataset: "dbt_{{ env_var('DBT_USER') }}"
      location: US
      threads: 8
      priority: interactive
      job_execution_timeout_seconds: 300
      maximum_bytes_billed: 5000000000    # 5 GB: query vượt ngưỡng bị BigQuery TỪ CHỐI
    ci:
      type: bigquery
      method: oauth                       # trên GitHub Actions: credential do google-github-actions/auth cung cấp
      project: "{{ env_var('GCP_PROJECT_NONPROD') }}"
      dataset: "ci_pr_{{ env_var('PR_NUMBER') }}"
      location: US
      threads: 8
      job_execution_timeout_seconds: 600
      maximum_bytes_billed: 5000000000
    prod:
      type: bigquery
      method: oauth
      project: "{{ env_var('GCP_PROJECT_PROD') }}"
      dataset: prod                       # schema mặc định; model có +schema sẽ vào dataset riêng (xem macro)
      location: US
      threads: 8
      job_execution_timeout_seconds: 1200
      maximum_bytes_billed: 50000000000
```

`method: oauth` dùng **Application Default Credentials (ADC)**:
- Trên máy: `gcloud auth application-default login`.
- Trên GitHub Actions: action `google-github-actions/auth` tạo file credential tạm và đặt biến `GOOGLE_APPLICATION_CREDENTIALS`; thư viện Google (mà dbt-bigquery dùng) tự đọc. Không cần key JSON.

## Đặt tên dataset theo môi trường: `generate_schema_name`

Mặc định dbt ghép `<schema của target>_<custom schema>`. Ta muốn prod có tên gọn:

| Model có `+schema` | dev (`dataset: dbt_duc`) | ci (`ci_pr_12`) | prod (`dataset: prod`) |
|---|---|---|---|
| `staging` | `dbt_duc_staging` | `ci_pr_12_staging` | `staging` |
| `marts` | `dbt_duc_marts` | `ci_pr_12_marts` | `marts` |
| (không có) | `dbt_duc` | `ci_pr_12` | `prod` |

```sql
-- macros/generate_schema_name.sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

(GĐ1, 1.3 đã gặp macro này. dbt cũng có sẵn macro `generate_schema_name_for_env` với ý tưởng tương tự.)

## Giới hạn dữ liệu ở dev

Hai cách:

**1. Macro theo target** (chạy được với mọi phiên bản dbt):

```sql
-- macros/limit_in_dev.sql
{% macro limit_in_dev(column, days=30) -%}
    {%- if target.name in ['dev', 'ci'] -%}
        where {{ column }} >= timestamp_sub(current_timestamp(), interval {{ days }} day)
    {%- endif -%}
{%- endmacro %}

-- models/staging/thelook/stg_thelook__events.sql
select ... from {{ source('thelook', 'events') }}
{{ limit_in_dev('created_at') }}
```

**2. `--sample` của dbt** (sample mode, dbt ≥ 1.10): khai báo `event_time` cho model/source, rồi `dbt build --sample="30 days"`. dbt tự lọc các `ref`/`source` có `event_time`. Không phải sửa SQL.

Lưu ý: dữ liệu dev bị giới hạn → test như "mỗi đơn có ít nhất 1 món" có thể đỏ ở dev mà xanh ở prod (món của đơn cũ bị cắt). Ghi chú điều đó trong README.

## Bảo vệ prod

| Biện pháp | Cách làm |
|---|---|
| CI không có quyền ghi prod | IAM như bảng trên |
| Chỉ pipeline được deploy prod | Không ai (kể cả bạn) dùng target `prod` trên máy; không cấp role ghi prod cho tài khoản cá nhân hằng ngày |
| GitHub Environment `production` | Workflow CD chạy trong environment có **protection rule** (chỉ nhánh `main`, có thể bắt duyệt tay) |
| Branch protection | `main` bắt buộc PR + CI xanh |
| Rào chắn chi phí | `maximum_bytes_billed`, budget alert của Cloud Billing |

## Lỗi hay gặp

- Dataset tạo ở location khác `US` → lỗi khi đọc dữ liệu public.
- `profiles.yml` chứa đường dẫn key JSON hoặc commit nhầm key lên GitHub.
- CI dùng chung dataset cho mọi PR.
- Dùng sandbox BigQuery: **không có DML** → model incremental (`MERGE`), snapshot không chạy được. Cần bật billing (dùng free trial).
- `generate_schema_name` viết sai → dev ghi đè dataset prod.
- Quên `maximum_bytes_billed` ở dev → một `select *` trên bảng lớn lặp trong vòng lặp Jinja.

## Áp dụng vào project thelook

Hướng dẫn từng bước + lệnh `gcloud`: [bai-tap-bigquery-thelook](../../bai-tap-bigquery-thelook/README.md).

- [ ] Chọn cách A/B/C, viết **ADR 0002** (bối cảnh: 1 người, ngân sách free trial, muốn CI không ghi được prod)
- [ ] Tạo project, dataset (location US), 2 service account, cấp quyền như bảng
- [ ] `profiles.yml` 3 target đọc biến môi trường, `generate_schema_name`, `maximum_bytes_billed`
- [ ] Giới hạn dữ liệu dev bằng macro hoặc `--sample`
- [ ] `dbt debug --target dev`, `dbt build --target dev` chạy được trên máy

## Câu hỏi tự kiểm tra

1. Vì sao CI mỗi PR cần dataset riêng?
2. So sánh 1 project / 2 project / 3 project. Bạn chọn gì, vì sao?
3. CI cần những quyền gì trên prod? Vì sao chỉ đọc?
4. `method: oauth` lấy credential ở đâu trên máy và trên GitHub Actions?
5. Viết `generate_schema_name` để prod dùng tên dataset gọn.
6. Kể 4 biện pháp bảo vệ prod.

## Tài liệu

- dbt — BigQuery setup: https://docs.getdbt.com/docs/core/connect-data-platform/bigquery-setup
- dbt — Custom schemas (`generate_schema_name`): https://docs.getdbt.com/docs/build/custom-schemas
- dbt — Sample mode `--sample`: https://docs.getdbt.com/docs/build/sample-flag
- BigQuery — IAM roles: https://docs.cloud.google.com/bigquery/docs/access-control
- BigQuery sandbox (giới hạn): https://docs.cloud.google.com/bigquery/docs/sandbox
