# 3.5 Exposures

## Khái niệm

**Exposure** khai báo **ai/cái gì dùng dữ liệu của bạn ở downstream**: dashboard, notebook, ứng dụng, mô hình ML. Nó không chạy gì cả — chỉ là metadata, nhưng xuất hiện trong lineage graph như một node cuối.

```
stg_* ──▶ int_* ──▶ fct_sales ──┐
                   dim_customers ┼──▶ 📊 [exposure] Sales Dashboard (Metabase)
                   dim_products ─┘
```

## Tại sao cần

1. **Impact analysis:** trước khi sửa `dim_customers`, biết ngay dashboard nào bị ảnh hưởng và ai là owner để báo.
2. **Chạy đúng phần cần:** `dbt build -s +exposure:sales_dashboard` build mọi thứ dashboard đó cần.
3. **Lineage hoàn chỉnh:** docs cho thấy dữ liệu đi tới đâu, không dừng ở bảng mart.
4. Gắn chủ sở hữu (ownership) — nền tảng cho governance sau này.

## Cú pháp

```yaml
# models/marts/sales/_sales__exposures.yml
exposures:
  - name: sales_performance_dashboard
    label: Sales Performance Dashboard
    type: dashboard               # dashboard | notebook | analysis | ml | application
    maturity: high                # high | medium | low
    url: https://metabase.example.com/dashboard/1
    description: >
      Dashboard doanh thu theo tháng, territory, nhóm sản phẩm. Ban giám đốc xem hằng tuần.
    depends_on:
      - ref('fct_sales')
      - ref('dim_customers')
      - ref('dim_products')
    owner:
      name: Tran Duc
      email: you@example.com        # docs public trên GitHub Pages sẽ hiện email này
```

| Trường | Bắt buộc | Ghi chú |
|---|---|---|
| `name` | ✅ | snake_case |
| `type` | ✅ | 5 loại ở trên |
| `owner` | ✅ | cần `name` hoặc `email` |
| `depends_on` | Nên có | `ref()`, `source()`, `metric()` |
| `maturity`, `url`, `description`, `label` | Không | Nên điền để docs có ích |

## Lệnh dùng với exposure

```bash
dbt ls --select +exposure:sales_performance_dashboard          # liệt kê mọi node cần cho dashboard
dbt build --select +exposure:sales_performance_dashboard       # build đúng phần đó
dbt build --select +exposure:*                                  # mọi thứ phục vụ mọi exposure
```

Kết hợp slim CI: thấy ngay PR có chạm tới model nằm trong lineage của exposure nào.

## Lỗi hay gặp

- Khai báo exposure "cho có", `url` giả, không có owner thật.
- `depends_on` thiếu model → impact analysis sai.
- Không cập nhật khi dashboard đổi nguồn.

## Áp dụng vào adventure_works

- [ ] Dựng 1 dashboard thật (Metabase/Superset/Looker Studio/Power BI — tuỳ bạn đã có gì) trên `fct_sales`
- [ ] ≥ 1 exposure trỏ tới dashboard đó, `url` thật
- [ ] (Thêm) 1 exposure `type: notebook` cho notebook phân tích
- [ ] Ảnh lineage có node exposure trong README

## Câu hỏi tự kiểm tra

1. Exposure có chạy/tạo bảng gì không?
2. Lệnh nào build mọi thứ một dashboard cần?
3. Exposure giúp gì khi bạn chuẩn bị sửa một dimension?

## Tài liệu

- https://docs.getdbt.com/docs/build/exposures
- https://docs.getdbt.com/reference/exposure-properties
