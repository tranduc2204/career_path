# 3.1 SQLFluff — linter cho SQL

## Khái niệm

**Linter** = công cụ đọc code và báo vi phạm quy tắc style/lỗi tiềm ẩn, không chạy code. SQLFluff là linter SQL phổ biến nhất, hiểu được Jinja và dbt.

- `sqlfluff lint` → báo lỗi.
- `sqlfluff fix` → tự sửa những gì sửa được.

## Tại sao cần

- Code review tập trung vào **logic**, không cãi nhau về dấu phẩy đầu dòng hay viết hoa keyword.
- Cả team viết SQL cùng một kiểu → dễ đọc code người khác.
- Bắt một số lỗi thật: `select *` ở marts, alias mơ hồ, cột không rõ bảng khi join.

## Templater: dbt vs jinja

SQLFluff cần render Jinja ra SQL thuần trước khi lint.

| Templater | Cách render | Ưu | Nhược |
|---|---|---|---|
| `dbt` | Gọi dbt thật để compile | Chính xác 100% (`ref`, macro, package) | Chậm, **cần kết nối warehouse** và `profiles.yml` |
| `jinja` | Render Jinja đơn giản, giả lập `ref`/`source` | Nhanh, không cần warehouse → dễ dùng trong CI | Macro phức tạp có thể render sai |

Với CI của portfolio: `jinja` templater đơn giản hơn; nếu project dùng nhiều macro thì dùng `dbt` templater kèm profile CI.

## Cấu hình

```ini
# .sqlfluff
[sqlfluff]
templater = dbt
dialect = snowflake            # postgres / bigquery / ... theo warehouse của bạn
max_line_length = 120
exclude_rules = ST06           # ví dụ: bỏ qua rule nào không hợp team

[sqlfluff:templater:dbt]
project_dir = .
profiles_dir = .
profile = adventure_works
target = dev

[sqlfluff:indentation]
tab_space_size = 4

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = lower

[sqlfluff:rules:layout.commas]
line_position = trailing
```

```
# .sqlfluffignore
target/
dbt_packages/
macros/
```

Cài đặt (dùng templater dbt):

```bash
pip install sqlfluff sqlfluff-templater-dbt
sqlfluff lint models/
sqlfluff fix models/staging/
```

## Nhóm rule đáng biết

| Mã | Nhóm | Ví dụ |
|---|---|---|
| `LT` | Layout | thụt lề, độ dài dòng, vị trí dấu phẩy |
| `CP` | Capitalisation | keyword viết thường/hoa thống nhất |
| `AL` | Aliasing | bắt buộc `as` khi đặt alias |
| `AM` | Ambiguous | `union` không rõ `all`/`distinct`, `order by` mơ hồ |
| `RF` | References | cột không rõ thuộc bảng nào khi join |
| `ST` | Structure | CTE không dùng, `case` thừa |

## Lint chỉ file thay đổi (trong CI)

Lint cả project mỗi PR là chậm và báo cả lỗi cũ. Chỉ lint file đổi:

```bash
git diff --name-only --diff-filter=d origin/main... -- 'models/**/*.sql' \
  | xargs -r sqlfluff lint
```

(Hoặc dùng `diff-quality` của gói `diff_cover` để chỉ báo lỗi trên **dòng** thay đổi.)

## Lỗi hay gặp

- Sai `dialect` → hàng loạt lỗi parse vô lý.
- Bật rule quá gắt ngay từ đầu trên project cũ → hàng trăm lỗi, bỏ cuộc. Hãy `fix` 1 lần, rồi mới bật CI.
- Lint cả `target/` và `dbt_packages/`.
- Templater `dbt` trong CI nhưng quên cấu hình profile → lỗi kết nối.

## Áp dụng vào adventure_works

- [ ] `.sqlfluff` + `.sqlfluffignore` ở root
- [ ] Chạy `sqlfluff fix` toàn project 1 lần, commit riêng ("style: apply sqlfluff")
- [ ] CI chạy `sqlfluff lint` trên file thay đổi
- [ ] README: mục "SQL style" giải thích các quy ước chính

## Câu hỏi tự kiểm tra

1. Vì sao SQLFluff cần templater?
2. Ưu/nhược của `dbt` templater so với `jinja` templater?
3. Vì sao nên lint chỉ file thay đổi trong CI?

## Tài liệu

- https://docs.sqlfluff.com/en/stable/
- https://docs.sqlfluff.com/en/stable/reference/rules.html
- https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql
