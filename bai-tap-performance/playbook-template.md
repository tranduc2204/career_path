# Performance & cost playbook — <tên project>

> Copy file này vào `docs/performance-playbook.md` của repo (thelook cho phần BigQuery, adventure_works cho phần Snowflake, hoặc 1 file chung). Thay mọi `<...>` bằng số đo thật. Hướng dẫn viết: [lý thuyết 7.6](../GD2-ly-thuyet/tuan-7/06-viet-performance-playbook.md).

Cập nhật lần cuối: <ngày> · Người viết: <tên>

## 0. Tóm tắt 1 trang

**5 quy tắc vàng** (rút từ thí nghiệm ở mục 6, không chép từ internet):

1. <vd: Lọc trực tiếp trên cột partition/sắp xếp, không bọc hàm — Q3 của B1 quét gấp N lần>
2. <...>
3. <...>
4. <...>
5. <...>

**Rào chắn đang bật**

| Nền tảng | Rào chắn | Giá trị |
|---|---|---|
| Snowflake | Resource monitor `<tên>` | <N> credit / tháng, suspend ở 90% |
| Snowflake | `AUTO_SUSPEND` warehouse dbt | 60 giây |
| BigQuery | `maximum_bytes_billed` | dev <..>, ci <..>, prod <..> |
| BigQuery | Quota query / ngày | <..> |
| BigQuery | Budget alert | <..> USD |

## 1. Mô hình chi phí

| | Snowflake | BigQuery on-demand |
|---|---|---|
| Trả tiền cho | credit = cỡ warehouse × thời gian chạy (tính theo giây, tối thiểu 60 giây mỗi lần bật) | byte quét |
| Giá đang áp dụng | <giá 1 credit theo edition/region của bạn> | <giá / TiB>, 1 TiB miễn phí / tháng |
| Đòn bẩy chính | thời gian, cỡ warehouse, tắt khi rảnh | byte quét: cột, partition, cluster |

## 2. Đo ở đâu (query copy được)

- Snowflake: `bai-tap-performance/snowflake/04-theo-doi-chi-phi.sql` (credit theo warehouse, theo `query_tag`, top query)
- BigQuery: `bai-tap-performance/bigquery/03-do-chi-phi-jobs.sql` (theo ngày, người dùng, model dbt, lần chạy dbt, cache, lưu trữ)
- dbt: `target/run_results.json` → `execution_time`, `adapter_response.bytes_billed`

## 3. Cây quyết định: model chậm / đắt

<Dán cây quyết định của lý thuyết 7.6, sửa theo kinh nghiệm thí nghiệm của bạn>

## 4. Cấu hình mặc định

```yaml
# dán phần cấu hình đã đưa vào dbt_project.yml (partition/cluster mặc định cho fact, snowflake_warehouse, query_tag, labels...)
```

Lý do chọn từng mục: <...>

## 5. Checklist review PR

- [ ] <...>

## 6. Nhật ký thí nghiệm

| # | Nền tảng | Câu hỏi | Thay đổi (1 thứ) | Trước | Sau | Kết luận |
|---|---|---|---|---|---|---|
| S1 | Snowflake | Sắp xếp dữ liệu giúp pruning? | `order by random()` → `order by o_orderdate` | <scanned/total, giây> | <...> | <...> |
| S1b | Snowflake | Bọc cột lọc trong hàm có mất pruning? | `to_char(o_orderdate)` | | | |
| S2a | Snowflake | Exploding join trông thế nào? | join theo ngày thay vì khoá | <dòng vào → ra> | | |
| S2b | Snowflake | Spill khi nào? | XS → M | <GB spill, giây> | | |
| S3 | Snowflake | Cỡ warehouse cho query nặng | XS / S / M / L | <bảng giây + credit> | | |
| B1 | BigQuery | Partition tiết kiệm bao nhiêu? | plain → part | <MB billed> | | |
| B1b | BigQuery | Cluster có thêm lợi ích? | part → part+cluster | dry run <..>, thực tế <..> | | |
| B1c | BigQuery | `select *` tốn gấp mấy lần? | `*` → 2 cột | | | |
| B2 | BigQuery | Incremental nào rẻ nhất cho fct_events? | merge / merge+predicates / insert_overwrite | | | |
| <...> | | | | | | |

## 7. Runbook: chi phí tăng đột biến

1. Xác nhận ngày bắt đầu tăng: <query>
2. Khoanh vùng (warehouse / user / tag / label): <query>
3. Tìm thủ phạm: <query top N>
4. Cầm máu: <lệnh suspend warehouse / tắt schedule / hạ maximum_bytes_billed>
5. Sửa gốc theo mục 3
6. Phòng ngừa + postmortem (mẫu GĐ1)
