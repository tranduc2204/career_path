# 8.4 Vận hành semantic layer: truy vấn, CI, phục vụ người dùng

## Truy vấn

| Cách | Có ở | Dùng cho |
|---|---|---|
| `mf query` (dbt-metricflow) | dbt Core | Phát triển, kiểm thử, CI. Đọc `target/semantic_manifest.json`, chạy SQL qua adapter của profile |
| `dbt sl query` | dbt platform (Cloud CLI) | Như trên, chạy trên hạ tầng của dbt |
| JDBC / ADBC (Arrow Flight SQL) | dbt platform | BI kết nối như một database: `select * from {{ semantic_layer.query(metrics=['revenue'], group_by=['metric_time__month']) }}` |
| GraphQL API | dbt platform | Ứng dụng, notebook, AI agent |
| Tích hợp BI có sẵn | dbt platform | Tableau, Power BI, Google Sheets, Hex, Mode... |
| dbt MCP server | Core + platform | Trợ lý AI liệt kê metric, truy vấn metric (tuần 14) |

**Điểm mấu chốt cho phỏng vấn:** MetricFlow mã nguồn mở và chạy được với dbt Core, còn **phần "phục vụ"** (API, kết nối BI, cache) nằm ở dbt platform. Công ty chỉ dùng Core thì có các lựa chọn: (1) dùng `mf` sinh SQL / `exports` thành bảng cho BI đọc, (2) dùng Cube hoặc semantic layer của BI, (3) tự viết dịch vụ nhỏ gọi MetricFlow (Python API).

## Lệnh hay dùng

```bash
mf list metrics                                    # metric + dimension dùng được
mf list dimension-values --metrics revenue --dimension sales_order__channel
mf query --metrics revenue,aov --group-by metric_time__week,sales_order__channel \
         --where "{{ Dimension('product__category') }} = 'Điện tử'" \
         --order -metric_time__week --limit 8
mf query --metrics revenue --group-by metric_time__month --explain    # xem SQL
mf query --metrics revenue --group-by metric_time__day --csv out.csv  # xuất file
mf query --saved-query daily_kpis
mf validate-configs                                # ngữ nghĩa + chạy thử trên warehouse
```

## Kiểm thử metric

Semantic layer là code, nên cần test như code:

1. **Hợp lệ ngữ nghĩa:** `dbt parse` + `mf validate-configs --skip-dw` trong CI cho mọi PR.
2. **Chạy được trên warehouse:** `mf validate-configs` (có chạm warehouse) trong CI với target CI.
3. **Đúng số:** chọn vài "điểm neo" đã khoá sổ (doanh thu tháng 10 = 9.634.555.000) và so `mf query` với giá trị đó. Đây chính là cách `check.py` của lab làm: SQL viết tay thẳng trên mart vs kết quả MetricFlow.
4. **Không đổi ngoài ý muốn:** khi sửa định nghĩa, so kết quả trước/sau trên cùng dữ liệu (`--csv` hai bản rồi diff). Thay đổi số phải đi kèm thông báo cho người dùng.

Ví dụ một bước CI:

```yaml
- name: Semantic layer
  run: |
    dbt parse --target ci
    mf validate-configs --skip-dw
    mf query --metrics revenue --group-by metric_time__month \
      --start-time 2026-10-01 --end-time 2026-10-31 --csv rev_oct.csv
    python scripts/assert_metric.py rev_oct.csv revenue 9634555000
```

## Quản trị metric

- **Chủ sở hữu:** mỗi metric thuộc một group (bài G1). Đặt `config: {group: commerce}` trên metric hoặc để semantic model kế thừa group của model.
- **Mô tả:** `label` (tên hiển thị) và `description` (định nghĩa nghiệp vụ, có ví dụ). Người dùng BI chỉ thấy 2 thứ này.
- **Thay đổi định nghĩa:** đổi định nghĩa mà giữ tên là thay đổi phá vỡ. Cách an toàn: metric mới (`revenue_v2` hoặc tên rõ nghĩa hơn), song song một thời gian, ghi deprecation trong `description`.
- **Ít mà chất:** 15–30 metric "chính thức" được review kỹ tốt hơn 300 metric không ai dám dùng. Metric thử nghiệm đặt `hidden: true` hoặc ở folder riêng.

## Hiệu năng và chi phí

- MetricFlow sinh SQL chạy trực tiếp trên warehouse. Mart có partition/cluster đúng (GĐ2 tuần 7) thì truy vấn nhanh.
- Lọc thời gian (`--start-time/--end-time`, `where` trên `metric_time`) được đẩy xuống từng bảng: kiểm tra bằng `--explain`.
- Dashboard truy vấn liên tục thì dùng cache (dbt platform), `exports` thành bảng, hoặc pre-aggregation của Cube.

## Câu hỏi tự kiểm tra

1. Công ty chỉ dùng dbt Core và Metabase. Bạn đưa metric từ MetricFlow tới Metabase thế nào?
2. Viết checklist review một PR thêm metric mới (ít nhất 6 mục).
3. Finance yêu cầu đổi `revenue` để trừ voucher. Bạn triển khai thay đổi này ra sao để không làm hỏng dashboard đang dùng?

## Tài liệu

- dbt docs: *MetricFlow commands*, *dbt Semantic Layer APIs* (JDBC, GraphQL), *Available integrations*, *dbt MCP server*
