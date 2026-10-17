# 3.2 GitHub Actions và Slim CI (`state:modified+`)

## CI là gì

**Continuous Integration**: mỗi khi mở/cập nhật Pull Request, một máy tự động chạy kiểm tra (lint, build, test). PR chỉ được merge khi CI xanh.

Với dbt, CI trả lời câu hỏi: *"Thay đổi này có làm gãy model nào hoặc làm sai dữ liệu không?"*

## GitHub Actions — khái niệm cơ bản

| Thuật ngữ | Ý nghĩa |
|---|---|
| **Workflow** | File YAML trong `.github/workflows/` |
| **Trigger (`on`)** | Sự kiện kích hoạt: `pull_request`, `push`, `schedule`, `workflow_dispatch` |
| **Job** | Nhóm bước chạy trên 1 máy (runner) |
| **Step** | 1 lệnh shell hoặc 1 action dùng sẵn (`uses:`) |
| **Secret** | Biến bí mật (mật khẩu warehouse) lưu ở Settings → Secrets |
| **Artifact** | File lưu lại giữa các lần chạy/job |

## Vấn đề: CI build toàn bộ project thì chậm và tốn

Project 200 model, PR chỉ sửa 1 model → build lại 200 model là lãng phí.

## Slim CI: chỉ build cái thay đổi

### Bước 1: hiểu `manifest.json`

Mỗi lệnh `dbt` (parse/compile/run...) sinh `target/manifest.json` — **bản đồ toàn bộ project**: mọi model, SQL đã compile, config, dependency.

### Bước 2: so sánh state

Lấy `manifest.json` của **production** (lần deploy gần nhất), so với code PR:

```bash
dbt build --select state:modified+ --state ./prod-artifacts
```

| Selector | Chọn |
|---|---|
| `state:modified` | Node có SQL/config/YAML khác so với prod |
| `state:modified+` | + mọi node **downstream** của chúng |
| `+state:modified` | + mọi node upstream |
| `state:new` | Node mới thêm |

Vì sao cần `+` (downstream)? Sửa `stg_sales__orders` có thể làm gãy `fct_sales` phía sau.

### Bước 3: `--defer` — không build upstream

Model đã đổi `ref()` tới model upstream **không đổi**. Trong schema CI chưa có upstream đó. `--defer` bảo dbt: *"node nào không được chọn thì dùng bảng ở prod"*.

```bash
dbt build --select state:modified+ --defer --state ./prod-artifacts
```

```
upstream (không đổi) ── dùng bảng prod (defer)
        │
   stg_x (đã sửa) ──▶ int_y ──▶ fct_z      ← chỉ build 3 model này trong schema CI
```

Thêm `--favor-state` nếu muốn luôn ưu tiên bảng prod kể cả khi bảng đó có trong schema CI.

### Lấy manifest prod ở đâu?

| Cách | Mô tả |
|---|---|
| Artifact của workflow deploy | Job chạy trên `main` upload `manifest.json`; job PR tải về |
| Branch `gh-pages` | Docs deploy kèm `manifest.json` → CI đọc từ đó (tiện vì tuần 3 cũng làm docs) |
| Object storage (S3/GCS) | Cách dùng phổ biến ở công ty |

## Schema riêng cho mỗi PR

Tránh các PR ghi đè nhau: build vào `dbt_ci_pr_<số PR>`.

```yaml
# profiles.yml dùng trong CI (đọc từ env, không hard-code mật khẩu)
adventure_works:
  target: ci
  outputs:
    ci:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: TRANSFORMER
      warehouse: COMPUTE_WH
      database: ANALYTICS_CI
      schema: "{{ env_var('DBT_CI_SCHEMA') }}"
      threads: 8
```

Khi PR đóng → workflow khác chạy macro drop schema đó.

## Workflow mẫu

```yaml
# .github/workflows/ci.yml
name: dbt CI
on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install sqlfluff sqlfluff-templater-dbt dbt-snowflake
      - run: dbt deps
      - name: Lint changed models
        run: |
          git diff --name-only --diff-filter=d origin/main... -- 'models/**/*.sql' \
            | xargs -r sqlfluff lint

  slim-ci:
    runs-on: ubuntu-latest
    needs: lint
    env:
      SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
      SNOWFLAKE_USER: ${{ secrets.SNOWFLAKE_USER }}
      SNOWFLAKE_PASSWORD: ${{ secrets.SNOWFLAKE_PASSWORD }}
      DBT_CI_SCHEMA: dbt_ci_pr_${{ github.event.pull_request.number }}
      DBT_PROFILES_DIR: ./ci
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install dbt-snowflake
      - run: dbt deps
      - name: Download prod manifest
        run: |
          mkdir -p prod-artifacts
          curl -sfL https://<user>.github.io/adventure_works/manifest.json \
            -o prod-artifacts/manifest.json || echo "no prod manifest, full build"
      - name: Slim CI build
        run: |
          if [ -f prod-artifacts/manifest.json ]; then
            dbt build --select state:modified+ --defer --state prod-artifacts
          else
            dbt build
          fi
```

(Thay `snowflake` bằng adapter bạn dùng. Lần đầu chưa có manifest prod thì build toàn bộ.)

## Lỗi hay gặp

- Không có manifest prod → `state:modified` báo lỗi hoặc chọn sai. Cần fallback build toàn bộ.
- Quên `--defer` → lỗi "relation does not exist" ở upstream.
- Manifest prod cũ (deploy lâu không chạy) → so sánh sai.
- Hard-code mật khẩu trong `profiles.yml` commit lên git.
- Tất cả PR dùng chung 1 schema CI → ghi đè nhau.
- Macro `generate_schema_name` không tính đến target `ci`.

## Áp dụng vào adventure_works

- [ ] Workflow `ci.yml`: lint → slim CI, chạy trên mọi PR vào `main`
- [ ] Workflow deploy trên `main` publish `manifest.json` (cùng docs ở 3.3)
- [ ] Schema riêng mỗi PR + workflow dọn schema khi PR đóng
- [ ] Secrets trong GitHub, không có mật khẩu trong repo
- [ ] Bật branch protection: bắt buộc CI xanh mới merge
- [ ] Mở 1 PR demo sửa 1 model staging, chụp log CI chỉ build model đó + downstream → đưa vào README

## Câu hỏi tự kiểm tra

1. `manifest.json` chứa gì? Sinh ra khi nào?
2. `state:modified` so sánh với cái gì?
3. Vì sao dùng `state:modified+` chứ không phải `state:modified`?
4. `--defer` giải quyết lỗi gì?
5. Làm sao để 2 PR chạy CI cùng lúc không đè dữ liệu của nhau?

## Tài liệu

- https://docs.getdbt.com/reference/node-selection/syntax#state-selection
- https://docs.getdbt.com/reference/node-selection/defer
- https://docs.getdbt.com/reference/artifacts/manifest-json
- https://docs.github.com/en/actions
