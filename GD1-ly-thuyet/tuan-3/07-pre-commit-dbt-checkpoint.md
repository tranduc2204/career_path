# 3.7 pre-commit + dbt-checkpoint

## Khái niệm

**Git hook** = script Git tự chạy ở một thời điểm (trước commit, trước push...).
**pre-commit** = framework quản lý hook bằng 1 file YAML. Mỗi `git commit`, các hook chạy trên **file đang staged**; hook fail → commit bị chặn.

**dbt-checkpoint** = bộ hook dành riêng cho dbt, kiểm tra **quy chuẩn project**: model có description chưa, có test chưa, có hard-code tên bảng không...

## Vị trí trong chuỗi bảo vệ chất lượng

```
viết code ──▶ pre-commit (máy bạn, vài giây) ──▶ push ──▶ CI (GitHub, vài phút) ──▶ review ──▶ merge
              sqlfluff, dbt-checkpoint                   sqlfluff, slim CI build+test
```

Pre-commit bắt lỗi **sớm nhất, rẻ nhất**. CI vẫn cần vì ai đó có thể bỏ qua hook (`git commit --no-verify`).

## Cài đặt

```bash
pip install pre-commit
pre-commit install          # gắn hook vào .git/hooks
pre-commit run --all-files  # chạy thử trên toàn repo
```

## Cấu hình mẫu

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.2.0
    hooks:
      - id: sqlfluff-lint
        additional_dependencies: ['dbt-snowflake', 'sqlfluff-templater-dbt']

  - repo: https://github.com/dbt-checkpoint/dbt-checkpoint
    rev: v2.0.6
    hooks:
      - id: dbt-parse                          # sinh manifest.json cho các hook sau
      - id: check-script-has-no-table-name     # cấm hard-code tên bảng, bắt buộc ref/source
      - id: check-model-has-description
      - id: check-model-columns-have-desc
        files: ^models/marts/
      - id: check-model-has-tests
        args: ["--test-cnt", "1", "--"]
      - id: check-model-has-properties-file
      - id: check-source-has-freshness
        args: ["--freshness", "error_after", "warn_after", "--"]
      - id: check-model-name-contract
        args: ["--pattern", "(stg_|int_|fct_|dim_).*", "--"]
```

> `rev` ở trên là ví dụ — chạy `pre-commit autoupdate` để lấy bản mới nhất.

## Hook dbt-checkpoint đáng dùng

| Hook | Kiểm tra |
|---|---|
| `dbt-parse` / `dbt-compile` | Cập nhật `manifest.json` (các hook khác đọc file này) |
| `check-script-has-no-table-name` | SQL không có tên bảng cứng, phải qua `ref`/`source` |
| `check-model-has-description` | Model có description |
| `check-model-columns-have-desc` | Mọi cột có description |
| `check-model-has-tests` | Model có ≥ N test |
| `check-model-has-tests-by-name` | Có test cụ thể (vd `unique`, `not_null`) |
| `check-model-name-contract` | Tên model theo regex quy ước |
| `check-source-has-freshness` | Source có cấu hình freshness |
| `check-model-has-contract` | Model có contract enforced |

## Lưu ý quan trọng

- Đa số hook dbt-checkpoint **đọc `manifest.json`** → phải có `target/manifest.json` mới (hook `dbt-parse` đứng đầu lo việc này). `dbt parse` cần `profiles.yml` hợp lệ.
- Áp dụng theo folder bằng `files:` (vd chỉ bắt mô tả cột ở marts) để không quá gắt.
- Có thể chạy pre-commit **trong CI** (`pre-commit run --all-files` hoặc action `pre-commit/action`) để chặn người bỏ qua hook local.

## Lỗi hay gặp

- Chưa `pre-commit install` → file config có nhưng hook không bao giờ chạy.
- Manifest cũ → hook báo sai.
- Bật quá nhiều hook gắt trên project đang dang dở → mỗi commit bị chặn, nản và bỏ.
- Dùng `--no-verify` thành thói quen.

## Áp dụng vào adventure_works

- [ ] `.pre-commit-config.yaml` với nhóm hook chung + sqlfluff + dbt-checkpoint
- [ ] `pre-commit run --all-files` sạch
- [ ] Thêm bước pre-commit vào CI
- [ ] README: mục "Contributing" hướng dẫn cài pre-commit

## Câu hỏi tự kiểm tra

1. Vì sao đã có CI mà vẫn cần pre-commit (và ngược lại)?
2. Vì sao hook `dbt-parse` thường đứng đầu?
3. `check-script-has-no-table-name` ngăn lỗi gì?

## Tài liệu

- https://pre-commit.com/
- https://github.com/dbt-checkpoint/dbt-checkpoint
- https://docs.sqlfluff.com/en/stable/production/pre_commit.html
