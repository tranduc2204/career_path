# 3.3 dbt docs lên GitHub Pages

## Khái niệm

`dbt docs` tạo một **website tĩnh** mô tả project: danh sách model, cột, description, test, SQL, và **lineage graph** (DAG).

```bash
dbt docs generate   # sinh file vào target/
dbt docs serve      # chạy web local tại localhost:8080
```

## Các file artifact

| File | Nội dung | Cần warehouse? |
|---|---|---|
| `manifest.json` | Định nghĩa project: model, config, description, dependency | Không |
| `catalog.json` | Metadata **thực tế** từ warehouse: kiểu cột, số dòng, kích thước | **Có** (query information_schema) |
| `index.html` | Giao diện web, đọc 2 file trên | — |
| `run_results.json` | Kết quả lần chạy gần nhất | — |

Từ dbt 1.7: `dbt docs generate --static` sinh thêm `target/static_index.html` — **1 file duy nhất** đã nhúng sẵn manifest + catalog, mở trực tiếp không cần server.

## Viết docs tốt

```yaml
models:
  - name: fct_sales
    description: >
      Fact bán hàng. **Grain: 1 dòng = 1 order line.**
      Nguồn: Sales.SalesOrderHeader + Sales.SalesOrderDetail.
    columns:
      - name: sales_key
        description: Surrogate key = hash(order_id, order_line_id)
      - name: line_total_amount
        description: "{{ doc('line_total_amount') }}"
```

Doc block dùng lại cho description dài hoặc dùng nhiều nơi:

```markdown
<!-- models/docs/_docs.md -->
{% docs line_total_amount %}
Thành tiền của dòng đơn = unit_price × quantity × (1 − discount). Đơn vị USD.
{% enddocs %}
```

Trang chủ của site docs: tạo doc block tên `__overview__`.

Thêm `persist_docs` để đẩy description vào comment của bảng/cột trong warehouse:

```yaml
# dbt_project.yml
models:
  +persist_docs:
    relation: true
    columns: true
```

## Deploy lên GitHub Pages bằng GitHub Actions

Settings → Pages → Source: **GitHub Actions**.

```yaml
# .github/workflows/deploy_docs.yml
name: Deploy dbt docs
on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
      SNOWFLAKE_USER: ${{ secrets.SNOWFLAKE_USER }}
      SNOWFLAKE_PASSWORD: ${{ secrets.SNOWFLAKE_PASSWORD }}
      DBT_PROFILES_DIR: ./ci
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install dbt-snowflake
      - run: dbt deps
      - run: dbt docs generate --target prod
      - name: Prepare site
        run: |
          mkdir -p site
          cp target/index.html target/manifest.json target/catalog.json site/
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

`manifest.json` nằm trên Pages → CI ở 3.2 tải được làm state prod.

## Lỗi hay gặp

- Chỉ copy `index.html` → trang trắng (thiếu manifest/catalog).
- Không có quyền kết nối warehouse khi generate → không có `catalog.json`, thiếu kiểu cột.
- Description để trống hoặc lặp lại tên cột ("order_id: the order id") → docs vô giá trị.
- Repo private thì GitHub Pages có giới hạn theo gói tài khoản; với portfolio nên để repo public.
- Lộ thông tin nhạy cảm trong docs public (tên server, dữ liệu mẫu). AdventureWorks là dữ liệu mẫu nên không sao.

## Áp dụng vào adventure_works

- [ ] Description cho mọi model ở marts + mọi cột ở fact/dim
- [ ] Doc block `__overview__` giới thiệu project, kiến trúc, grain từng fact
- [ ] Workflow deploy docs khi merge vào `main`
- [ ] Link docs ở đầu README và trong CV/portfolio
- [ ] Chụp lineage graph đưa vào README

## Câu hỏi tự kiểm tra

1. `manifest.json` và `catalog.json` khác nhau thế nào? File nào cần kết nối warehouse?
2. `--static` khác gì cách thông thường?
3. Doc block dùng khi nào?
4. `persist_docs` làm gì?

## Tài liệu

- https://docs.getdbt.com/docs/build/documentation
- https://docs.getdbt.com/reference/commands/cmd-docs
- https://docs.getdbt.com/reference/resource-configs/persist_docs
- https://docs.github.com/en/pages
