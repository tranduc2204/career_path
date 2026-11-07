# 10.5 Governance trong dbt: groups, access, contracts, versions

> Các tính năng này là nền của **dbt Mesh** (tuần 12). Làm tốt ở một project thì tách project mới suôn sẻ.

## Vì sao cần

Khi project có 3 đội, những chuyện sau xảy ra:

- Đội Growth `ref` thẳng staging của Commerce. Commerce đổi tên cột staging, báo cáo của Growth gãy.
- Không ai biết ai là chủ `dim_customers`, nên không biết phải hỏi ai trước khi sửa.
- Một PR xoá cột `phone` khỏi mart. Ba dashboard gãy vào sáng hôm sau.

Governance trong dbt biến các quy ước ngầm thành **luật được dbt kiểm tra lúc parse/build**.

## Groups

```yaml
# models/_groups.yml
groups:
  - name: commerce
    owner: {name: Đội Commerce Analytics, email: commerce-data@mayshop.vn}
```

```yaml
# dbt_project.yml: gán theo folder
models:
  lab:
    staging:
      shop: {+group: commerce}
    marts:
      commerce: {+group: commerce}
```

Một model thuộc tối đa **một** group. Group là đơn vị sở hữu: ai được hỏi, ai phải duyệt PR (kết hợp `CODEOWNERS` của GitHub).

## Access

| `access` | Ai được `ref` | Dùng cho |
|---|---|---|
| `private` | Chỉ model **cùng group** | Staging, intermediate: chi tiết nội bộ |
| `protected` (mặc định) | Mọi model trong **cùng project** (và package cài vào) | Model dùng chung trong project nhưng chưa cam kết với bên ngoài |
| `public` | Mọi nơi, kể cả **project khác** (Mesh) | Giao diện đã cam kết: có contract, có owner, có version |

Vi phạm sẽ bị chặn **lúc parse**, trước khi chạy gì:

```
Node model.lab.growth_campaign_daily attempted to reference node model.lab.stg_shop__orders,
which is not allowed because the referenced node is private to the 'commerce' group.
```

## Contracts

Xem [9.4](../tuan-9/04-data-contracts.md). Quy tắc thực hành: **public ⇒ contract**. Đặt `+contract: {enforced: true}` cho cả folder `marts/`.

## Model versions

```yaml
models:
  - name: dim_customers
    latest_version: 2
    columns:                                  # khai báo một lần, đủ mọi cột của mọi version
      - {name: customer_id, data_type: integer}
      - {name: phone, data_type: varchar}
      - {name: customer_segment, data_type: varchar}
      # ...
    versions:
      - v: 1
        defined_in: dim_customers             # file gốc dim_customers.sql là v1
        deprecation_date: 2027-01-31
        columns:
          - include: all
            exclude: [customer_segment, age_band]
      - v: 2                                  # file dim_customers_v2.sql
        columns:
          - include: all
            exclude: [phone, birth_date, segment]
```

| Hành vi | Chi tiết |
|---|---|
| Tên bảng | `dim_customers_v1`, `dim_customers_v2` (đặt `alias` nếu muốn khác) |
| `ref('dim_customers')` | Trỏ tới **`latest_version`** |
| `ref('dim_customers', v=1)` | Ghim version |
| `deprecation_date` | Sau ngày này dbt cảnh báo mỗi khi có model ref tới v1. Người dùng v1 phải chuyển |
| Chọn | `dbt ls -s dim_customers.v1+` (ai đang dùng v1), `-s version:latest`, `version:old`, `version:prerelease` |
| "Bảng tên cố định" | Mẫu thường dùng: post-hook tạo view `dim_customers` → latest version, cho BI không phải đổi tên |

Khi nào cần version mới: thay đổi **phá vỡ** (xoá/đổi tên cột, đổi kiểu, đổi grain, đổi ngữ nghĩa). Thêm cột thì không cần.

Lưu ý đã kiểm chứng (dbt-core 1.12.6): semantic model kiểu YAML mới đặt trên model có `versions:` bị bỏ qua. Dùng `semantic_models:` kiểu cũ với `ref('dim_customers', v=2)` (bài G4).

## Exposures

```yaml
exposures:
  - name: daily_revenue_dashboard
    type: dashboard            # dashboard | notebook | analysis | ml | application
    maturity: high             # high | medium | low
    url: https://bi.mayshop.vn/dashboards/doanh-thu-ngay
    owner: {name: Phòng Tài chính, email: finance@mayshop.vn}
    depends_on:
      - ref('fct_orders')
      - metric('revenue')
```

Exposure làm 3 việc: hiện "ai dùng model này" trong docs, cho phép chọn `dbt build -s +exposure:daily_revenue_dashboard` (build mọi thứ dashboard cần), và cho bạn biết **ai cần được báo** khi sửa hay khi có sự cố.

## Checklist governance cho model public

- [ ] Thuộc một group có owner email
- [ ] `access: public`, `contract: enforced`, mọi cột có `data_type`, khoá có `not_null` (+ test `unique`)
- [ ] `description` cho model và mọi cột; grain ghi rõ
- [ ] Cột PII gắn `meta: {pii: true}` (10.6)
- [ ] Có ít nhất 1 exposure hoặc ghi rõ người dùng trong `meta.consumers`
- [ ] Thay đổi phá vỡ → version mới + `deprecation_date` cho bản cũ

CI kiểm checklist này bằng script đọc `manifest.json`. Đây là ý tưởng của công cụ tuần 13: CLI đọc manifest báo cáo ownership và test coverage.

## Câu hỏi tự kiểm tra

1. Vì sao staging nên `private` chứ không phải `protected`?
2. Một model `public` không có contract. Rủi ro gì cho đội khác?
3. Bạn cần đổi grain của `fct_orders` (thêm dòng cho từng lần giao hàng). Lên kế hoạch versioning và thông báo.
