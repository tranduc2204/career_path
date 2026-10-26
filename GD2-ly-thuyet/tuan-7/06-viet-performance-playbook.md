# 7.6 Viết performance playbook

## Playbook là gì

Một tài liệu **thao tác được**: khi gặp query chậm / tốn tiền, người trong team mở ra và biết làm gì, theo thứ tự nào, đo bằng query nào. Khác bài blog ở chỗ nó có **cây quyết định, query đo đạc sẵn, cấu hình mặc định và số đo thật** của chính hệ thống bạn.

Đầu ra tuần 7: `docs/performance-playbook.md` (trong repo thelook hoặc adventure_works), một phần cho Snowflake, một phần cho BigQuery. Đây là một trong 3 tài liệu chính của portfolio (cùng ADR và architecture blueprint).

## Cấu trúc đề xuất

```markdown
# Performance & cost playbook

## 0. Tóm tắt 1 trang
   - 5 quy tắc vàng
   - Rào chắn đang bật (resource monitor, maximum_bytes_billed...)

## 1. Mô hình chi phí
   - Snowflake: credit theo cỡ × thời gian, 60 giây tối thiểu, warehouse đang dùng, giá 1 credit
   - BigQuery: byte quét, giá / TiB, free tier, tối thiểu 10 MB / bảng

## 2. Đo ở đâu (query có sẵn để copy)
   - Top 10 query đắt nhất 7 ngày
   - Chi phí theo model dbt (query_tag / labels)
   - Chi phí theo ngày, theo warehouse / theo người dùng
   - Tỷ lệ cache hit

## 3. Cây quyết định: "query / model này chậm hoặc đắt"
## 4. Cấu hình mặc định (dbt_project.yml)
## 5. Checklist review PR
## 6. Nhật ký thí nghiệm (số đo thật)
## 7. Runbook: chi phí tăng đột biến
```

## Cây quyết định mẫu

```
Model chậm / đắt
│
├─ 1. Có cần chạy model này thường xuyên vậy không?
│     └─ Không → giảm tần suất (tag theo lịch), hoặc view → table / table → incremental
│
├─ 2. Mở Query Profile / Execution details: bước nào chiếm nhiều thời gian nhất?
│     │
│     ├─ TableScan / đọc dữ liệu
│     │    ├─ Snowflake: Partitions scanned ≈ total?
│     │    │     → filter có bọc hàm? sắp xếp lại dữ liệu khi tạo bảng? (chỉ bảng TB mới tính clustering key)
│     │    └─ BigQuery: bytes processed lớn?
│     │          → bỏ select *, partition theo cột lọc, cluster theo cột lọc/join, filter dạng hằng số
│     │
│     ├─ Join: số dòng ra >> số dòng vào?
│     │    → exploding join: kiểm tra grain, test unique 2 phía, sửa điều kiện join
│     │
│     ├─ Aggregate / Sort / Window: có spill (Snowflake)?
│     │    → lọc sớm hơn, thu hẹp partition của window, bỏ order by thừa, rồi mới tăng cỡ warehouse
│     │
│     └─ Phần lớn thời gian là xếp hàng (queued)?
│          → Snowflake: warehouse đang quá tải → tách warehouse / multi-cluster
│
├─ 3. Incremental đã đúng chưa?
│     → filter incremental có prune được nguồn không? merge có quét cả bảng đích? thử insert_overwrite (BigQuery)
│
└─ 4. Đo lại, ghi kết quả vào mục 6 (kể cả khi không cải thiện)
```

## Cấu hình mặc định mẫu

```yaml
# BigQuery (thelook)
models:
  thelook:
    +labels: {team: analytics}
    staging:
      +materialized: view
    marts:
      +materialized: table
      fct_events:
        +materialized: incremental
        +incremental_strategy: insert_overwrite
        +partition_by: {field: created_date, data_type: date}
        +cluster_by: [user_id, event_type]
        +require_partition_filter: true
```

```yaml
# Snowflake (adventure_works)
models:
  adventure_works:
    +snowflake_warehouse: TRANSFORM_XS
    +query_tag: "dbt_{{ target.name }}"
    +transient: true
```

## Checklist review PR (dán vào PR template)

- [ ] Model mới có `materialized` hợp lý (không để `table` cho thứ chỉ dùng 1 lần)
- [ ] Không `select *` ở marts
- [ ] Fact lớn có partition/cluster (BigQuery) hoặc đã cân nhắc thứ tự dữ liệu (Snowflake)
- [ ] Filter incremental viết dạng prune được
- [ ] Test trên bảng lớn có `where` giới hạn phạm vi
- [ ] Đã xem byte xử lý / thời gian của model trong CI (`run_results.json`)

## Nhật ký thí nghiệm (phần giá trị nhất)

Mỗi thí nghiệm 1 dòng. **Số đo thật**, kể cả kết quả không như kỳ vọng.

| # | Nền tảng | Câu hỏi | Thay đổi (chỉ 1) | Trước | Sau | Kết luận |
|---|---|---|---|---|---|---|
| S1 | Snowflake | Sắp xếp dữ liệu có giúp pruning? | CTAS `order by o_orderdate` vs `order by random()` | 100% partition quét, X s | Y% partition quét, Z s | |
| S2 | Snowflake | Cỡ warehouse nào hợp cho query nặng? | XS → S → M → L | | | |
| B1 | BigQuery | Partition tiết kiệm bao nhiêu? | Bảng copy có partition theo ngày | X GB | Y MB | |
| B2 | BigQuery | Cluster giúp lọc theo user_id? | + `cluster_by user_id` | | | |
| B3 | BigQuery | `merge` vs `insert_overwrite` cho fct_events | đổi strategy | | | |

Các thí nghiệm này có hướng dẫn từng bước ở [bai-tap-performance](../../bai-tap-performance/README.md).

## Runbook: chi phí tăng đột biến

```
1. Xác nhận: query chi phí theo ngày (Snowflake WAREHOUSE_METERING_HISTORY / BigQuery JOBS) → tăng từ ngày nào?
2. Khoanh vùng: theo warehouse / người dùng / query_tag / label → khối nào tăng?
3. Tìm thủ phạm: top query đắt nhất trong khoảng đó → model nào, job nào, ai chạy?
4. Cầm máu: tắt schedule / suspend warehouse / hạ maximum_bytes_billed
5. Sửa gốc: theo cây quyết định
6. Phòng ngừa: thêm rào chắn, thêm mục vào checklist, viết postmortem ngắn (mẫu GĐ1)
```

## Lỗi hay gặp

- Playbook chỉ là danh sách mẹo chép từ internet, không có số đo của hệ thống mình.
- Không ghi thí nghiệm thất bại → người sau thử lại đúng thứ đó.
- Cấu hình mặc định không được đưa vào `dbt_project.yml` → playbook nói một đằng, code một nẻo.
- Không có runbook → khi chi phí bùng lên mới bắt đầu nghĩ.

## Câu hỏi tự kiểm tra

1. Playbook khác bài blog / tài liệu mẹo ở điểm nào?
2. Kể các mục chính của một performance playbook.
3. Trình bày cây quyết định khi gặp model chậm.
4. Vì sao phải ghi cả thí nghiệm không cải thiện được gì?
5. Chi phí BigQuery tháng này tăng gấp 3. Bạn làm gì trong 30 phút đầu?

## Tài liệu

- 7.1 → 7.5 của tuần này
- Bài thực hành: [bai-tap-performance](../../bai-tap-performance/README.md)
- Mẫu playbook để điền: [bai-tap-performance/playbook-template.md](../../bai-tap-performance/playbook-template.md)
