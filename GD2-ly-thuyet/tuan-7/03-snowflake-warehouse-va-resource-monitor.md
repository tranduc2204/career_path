# 7.3 Snowflake: chọn cỡ warehouse, theo dõi chi phí, resource monitor

## Warehouse tính tiền thế nào

| Cỡ | Credit / giờ |
|---|---|
| X-Small | 1 |
| Small | 2 |
| Medium | 4 |
| Large | 8 |
| X-Large | 16 |
| 2X-Large … 6X-Large | 32 … 512 (mỗi cấp gấp đôi) |

(Bảng của warehouse tiêu chuẩn thế hệ 1, Gen1. Giá 1 credit tuỳ edition và khu vực.)

- Tính **theo giây**, nhưng **tối thiểu 60 giây mỗi lần warehouse bật lên** (resume).
- Warehouse chỉ tốn tiền khi **đang chạy**: `AUTO_SUSPEND` (giây rảnh trước khi tự tắt), `AUTO_RESUME` (tự bật khi có query). Cả hai mặc định bật.
- Cloud services (biên dịch query, metadata) cũng tính credit, nhưng chỉ phần vượt 10% credit compute trong ngày mới bị tính.

## Scale up hay scale out

| | Scale up (cỡ lớn hơn) | Scale out (multi-cluster) |
|---|---|---|
| Giúp gì | **Một query** chạy nhanh hơn (nhiều CPU/RAM hơn, ít spill hơn) | **Nhiều query đồng thời** không phải xếp hàng |
| Dùng khi | Model dbt nặng, query BI phức tạp, có spilling | Giờ cao điểm của dashboard, nhiều người dùng |
| Lưu ý | Gấp đôi cỡ = gấp đôi giá mỗi giây. Query nhỏ không nhanh hơn | Cần bản Enterprise trở lên |

### Cách chọn cỡ bằng thí nghiệm

Chạy **cùng** một model (hoặc cùng `dbt build` một nhóm model) trên XS, S, M, L. Ghi lại:

| Cỡ | Thời gian | Credit = credit/giờ × giờ | Spill? |
|---|---|---|---|
| XS | 16 phút | 1 × 0,267 = 0,27 | có remote spill |
| S | 7 phút | 2 × 0,117 = 0,23 | local spill |
| M | 3,5 phút | 4 × 0,058 = 0,23 | không |
| L | 3 phút | 8 × 0,05 = 0,40 | không |

(Số minh hoạ — bạn sẽ đo số thật ở bài thực hành.)

Đọc bảng: XS → S thời gian giảm **hơn** một nửa (hết remote spill) → vừa nhanh hơn vừa **rẻ hơn**. S → M giảm đúng một nửa → nhanh gấp đôi với **cùng** chi phí. M → L gần như không nhanh thêm → chỉ tốn gấp đôi. Cỡ "đúng" là cấp cuối cùng mà thời gian còn giảm khoảng một nửa khi tăng cấp.

Với dbt: phần lớn model nhỏ chạy tốt trên XS/S; chỉ vài model nặng cần cỡ lớn → dùng `snowflake_warehouse` theo model thay vì tăng cỡ cho cả project.

```yaml
# dbt_project.yml
models:
  adventure_works:
    +snowflake_warehouse: TRANSFORM_XS
    marts:
      finance:
        +snowflake_warehouse: TRANSFORM_M     # vài model nặng
```

### Tách warehouse theo khối việc

| Warehouse | Ai dùng | Cấu hình |
|---|---|---|
| `TRANSFORM_WH` | dbt (job hằng ngày) | XS/S, `AUTO_SUSPEND = 60` |
| `CI_WH` | GitHub Actions | XS, `AUTO_SUSPEND = 60`, resource monitor riêng |
| `BI_WH` | Dashboard | S + multi-cluster nếu cần, `AUTO_SUSPEND` dài hơn (giữ cache) |
| `ADHOC_WH` | Analyst query tay | XS, timeout ngắn |

Lợi ích: không giành tài nguyên nhau, và **biết rõ khối nào tốn bao nhiêu** (credit tính theo warehouse).

## Theo dõi chi phí

| Nguồn | Độ trễ | Dùng cho |
|---|---|---|
| `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` | tới 3 giờ | Credit theo warehouse theo giờ |
| `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` | tới 45 phút | Thời gian, byte quét, partition, spill, `query_tag` của từng query (giữ 365 ngày) |
| `SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY` | tới 8 giờ | Credit **gán cho từng query** (không gồm thời gian rảnh, bỏ qua query ≤ ~100 ms) |
| `INFORMATION_SCHEMA.QUERY_HISTORY()` (table function) | Không trễ | Theo dõi gần thời gian thực, giữ ngắn hạn |

Đọc `ACCOUNT_USAGE` cần quyền trên database `SNOWFLAKE` (vd role `ACCOUNTADMIN`, hoặc được cấp `IMPORTED PRIVILEGES`).

Credit theo model dbt (gắn `query_tag` trước):

```sql
-- dbt_project.yml: models: +query_tag: "dbt_{{ target.name }}"   hoặc gắn theo từng folder/model
select query_tag, sum(credits_attributed_compute) as credits
from snowflake.account_usage.query_attribution_history
where start_time >= dateadd('day', -7, current_timestamp())
group by 1
order by 2 desc;
```

Credit theo warehouse theo ngày:

```sql
select warehouse_name, to_date(start_time) as day, sum(credits_used) as credits
from snowflake.account_usage.warehouse_metering_history
where start_time >= dateadd('day', -30, current_timestamp())
group by 1, 2
order by 2 desc, 3 desc;
```

## Resource monitor: rào chắn bắt buộc

Resource monitor đếm credit của warehouse trong một chu kỳ và **hành động** khi chạm ngưỡng.

```sql
use role accountadmin;                         -- chỉ ACCOUNTADMIN tạo được resource monitor

create or replace resource monitor rm_monthly with
    credit_quota = 20                          -- credit cho mỗi chu kỳ
    frequency = monthly                        -- daily | weekly | monthly | yearly | never
    start_timestamp = immediately
    triggers
        on 50 percent do notify
        on 80 percent do notify
        on 90 percent do suspend               -- chờ query đang chạy xong rồi tắt
        on 100 percent do suspend_immediate;   -- huỷ query đang chạy, tắt ngay

alter warehouse transform_wh set resource_monitor = rm_monthly;
-- hoặc cho cả tài khoản:
-- alter account set resource_monitor = rm_monthly;
```

| Hành động | Tác dụng | Số lượng tối đa / monitor |
|---|---|---|
| `NOTIFY` | Chỉ gửi thông báo | 5 |
| `SUSPEND` | Tắt warehouse sau khi query đang chạy xong | 1 |
| `SUSPEND_IMMEDIATE` | Huỷ query đang chạy và tắt | 1 |

Giới hạn cần biết:
- Chỉ giám sát **warehouse**. Không chặn được chi phí của tính năng **serverless** (Automatic Clustering, Snowpipe, Search Optimization...) hay AI.
- Không tính phần điều chỉnh 10% của cloud services.
- Warehouse có thể chạy thêm một chút sau khi chạm ngưỡng → đặt ngưỡng `SUSPEND` dưới 100% (vd 90%).
- Muốn nhận email: tài khoản (user) phải bật nhận thông báo trong Snowsight.

## Cấu hình warehouse cho dbt

```sql
create warehouse transform_wh with
    warehouse_size = 'XSMALL'
    auto_suspend = 60              -- 60 giây; dbt chạy theo đợt, không cần cache lâu
    auto_resume = true
    initially_suspended = true
    statement_timeout_in_seconds = 3600;   -- chặn query treo
```

## Lỗi hay gặp

- `AUTO_SUSPEND = 600` (hoặc tắt hẳn) cho warehouse của dbt → trả tiền cho 10 phút rảnh sau mỗi lần chạy.
- Tăng cỡ warehouse cho cả project vì 1 model chậm.
- Dùng multi-cluster để làm 1 query nhanh hơn (sai công cụ).
- Không có resource monitor → một vòng lặp lỗi đốt hết credit tháng.
- Tưởng resource monitor chặn được chi phí Automatic Clustering.
- Đo thời gian chạy khi result cache bật.

## Áp dụng vào adventure_works

Bài thực hành chi tiết: [bai-tap-performance/snowflake](../../bai-tap-performance/snowflake/).

- [ ] Tạo resource monitor cho tài khoản (trial cũng nên có), ngưỡng 50/80/90/100%
- [ ] Tách `TRANSFORM_WH` và `CI_WH`, cả hai `AUTO_SUSPEND = 60`
- [ ] Gắn `query_tag` cho dbt, viết query "credit theo model 7 ngày gần nhất"
- [ ] Thí nghiệm XS/S/M trên `dbt build` của adventure_works và trên 1 query TPC-H nặng → bảng cỡ / thời gian / credit trong playbook

## Câu hỏi tự kiểm tra

1. Snowflake tính tiền warehouse thế nào? Quy tắc 60 giây là gì?
2. Scale up và scale out khác nhau thế nào? Mỗi cái giải quyết vấn đề gì?
3. Mô tả thí nghiệm chọn cỡ warehouse. Khi nào tăng cỡ vừa nhanh hơn vừa rẻ hơn?
4. Vì sao tách warehouse theo khối việc?
5. Resource monitor có những hành động nào? Giới hạn của nó?
6. Lấy credit theo từng model dbt bằng cách nào?

## Tài liệu

- Overview of warehouses: https://docs.snowflake.com/en/user-guide/warehouses-overview
- Working with resource monitors: https://docs.snowflake.com/en/user-guide/resource-monitors
- QUERY_ATTRIBUTION_HISTORY: https://docs.snowflake.com/en/sql-reference/account-usage/query_attribution_history
- WAREHOUSE_METERING_HISTORY: https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history
