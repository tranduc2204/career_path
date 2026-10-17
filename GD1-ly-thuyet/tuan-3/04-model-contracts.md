# 3.4 Model contracts

## Khái niệm

**Contract** = cam kết về **hình dạng** (shape) của model: tên cột, kiểu dữ liệu, và (tuỳ warehouse) ràng buộc. Nếu SQL trả về khác với contract → dbt **dừng build trước khi tạo bảng**.

Giống "interface" trong lập trình: người dùng downstream (BI, team khác) yên tâm cột `order_date` luôn là `date`, không tự nhiên biến mất.

## Contract khác test thế nào

| | Contract | Data test |
|---|---|---|
| Kiểm tra | **Shape**: tên cột, kiểu, ràng buộc | **Nội dung** dữ liệu |
| Thời điểm | **Trước/khi** build (preflight + DDL) | **Sau** khi build |
| Khi sai | Bảng **không** được tạo/thay thế | Bảng đã tạo, test báo fail |
| Ví dụ | `order_date` phải là `date` | `order_date` không null, không ở tương lai |

Hai thứ bổ sung nhau, không thay nhau.

## Cú pháp

```yaml
models:
  - name: fct_sales
    config:
      contract:
        enforced: true
    columns:
      - name: sales_key
        data_type: varchar
        constraints:
          - type: not_null
          - type: primary_key
      - name: order_id
        data_type: int
        constraints:
          - type: not_null
      - name: order_date
        data_type: date
      - name: line_total_amount
        data_type: number(38, 4)
        constraints:
          - type: check
            expression: "line_total_amount >= 0"
```

Khi bật contract:
- **Mọi cột** model trả về phải được khai báo, kèm `data_type`. Thừa hoặc thiếu cột → lỗi.
- Kiểu dữ liệu phải khớp (dbt so kiểu trước khi build).

## Constraints — được enforce đến đâu?

| Constraint | Postgres | Snowflake | BigQuery |
|---|---|---|---|
| `not_null` | ✅ enforce | ✅ enforce | ✅ enforce |
| `primary_key` / `unique` / `foreign_key` | ✅ enforce | ⚠️ chỉ metadata, không chặn | ⚠️ chỉ metadata |
| `check` | ✅ | ❌ | ❌ |

→ Trên Snowflake/BigQuery vẫn cần **data test** `unique` cho khoá chính. Kiểm tra bảng hỗ trợ chính xác của adapter trong docs vì có thể thay đổi theo phiên bản.

## Giới hạn

- Hỗ trợ materialization `table`, `view` (chỉ kiểm tên/kiểu, không constraint), `incremental`. **Không** hỗ trợ `ephemeral`.
- Incremental + contract: nên đặt `on_schema_change: append_new_columns` hoặc `fail`.
- Python model không hỗ trợ.

## Contract + versioning (biết trước, học sâu ở tuần 10/12)

Khi buộc phải đổi contract (đổi kiểu, xoá cột) → đó là **breaking change**. dbt cho phép **model versions** (`v1`, `v2`) để người dùng có thời gian chuyển. Slim CI còn phát hiện được breaking change trên model có contract khi so state.

## Nên đặt contract ở đâu

- Marts được BI/exposure dùng → **có**.
- Model "public" cho team khác (dbt Mesh, tuần 12) → **bắt buộc**.
- Staging/intermediate → thường **không** cần (tăng chi phí bảo trì).

## Lỗi hay gặp

- Bật contract nhưng YAML thiếu 1 cột → build lỗi, tưởng SQL sai.
- Khai báo kiểu chung chung khác kiểu thật (`numeric` vs `number(38,4)`) → tuỳ adapter có thể báo không khớp.
- Tin rằng `primary_key` trên Snowflake sẽ chặn trùng → không chặn.
- Đặt contract cho mọi model → mỗi lần đổi nhỏ phải sửa YAML khắp nơi.

## Áp dụng vào adventure_works

- [ ] Contract cho `fct_sales`, `dim_customers`, `dim_products`
- [ ] Dùng `codegen.generate_model_yaml` để sinh sẵn `data_type`
- [ ] Thử phá contract (đổi kiểu 1 cột) → chụp lỗi đưa vào README
- [ ] Giữ data test `unique` cho khoá nếu warehouse không enforce

## Câu hỏi tự kiểm tra

1. Contract và data test khác nhau ở điểm nào?
2. Trên Snowflake, `primary_key` constraint có chặn trùng không?
3. Vì sao không bật contract cho staging?
4. Contract không dùng được với materialization nào?

## Tài liệu

- https://docs.getdbt.com/docs/mesh/govern/model-contracts
- https://docs.getdbt.com/reference/resource-properties/constraints
- https://docs.getdbt.com/docs/mesh/govern/model-versions
