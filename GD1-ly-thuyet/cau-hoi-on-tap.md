# Câu hỏi ôn tập GĐ1 (mức Junior AE)

> Trả lời miệng hoặc viết ra **không nhìn tài liệu**, tối đa 2 phút mỗi câu. Đáp án nằm trong file lý thuyết tương ứng (cột "Xem").

## Cấu trúc project

| # | Câu hỏi | Xem |
|---|---|---|
| 1 | Trình bày 3 tầng staging / intermediate / marts: trách nhiệm, materialization, quy ước tên. | 1.1 |
| 2 | Vì sao marts không được đọc thẳng từ `source()`? | 1.1 |
| 3 | `ephemeral` là gì, nhược điểm? | 1.1 |
| 4 | Bạn đã dùng những macro nào của dbt-utils? Vì sao? | 1.2 |
| 5 | Surrogate key là gì, tạo bằng cách nào trong dbt? | 1.2 |
| 6 | Kể 5 macro bạn tự viết và vấn đề mỗi macro giải quyết. | 1.3 |
| 7 | Mặc định dbt đặt tên custom schema thế nào, bạn đã đổi ra sao? | 1.3 |

## Dữ liệu theo thời gian

| # | Câu hỏi | Xem |
|---|---|---|
| 8 | Khi nào **không** nên dùng incremental? | 2.1 |
| 9 | So sánh append, merge, delete+insert. Mỗi loại bạn dùng cho model nào? | 2.1 |
| 10 | Làm sao kiểm chứng model incremental đúng bằng full refresh? | 2.1 |
| 11 | Late-arriving data là gì, bạn xử lý thế nào? | 2.2 |
| 12 | Kể 3 cách backfill trong dbt. | 2.2 |
| 13 | SCD Type 2 là gì? Snapshot timestamp khác check thế nào? | 2.3 |
| 14 | Vì sao snapshot nên đặt gần nguồn? | 2.3 |
| 15 | Join fact với dimension SCD2 thế nào để không nhân dòng? | 2.3 |
| 16 | Một test dbt pass khi nào? Viết 1 custom generic test bạn đã làm. | 2.4 |

## Chất lượng & CI/CD

| # | Câu hỏi | Xem |
|---|---|---|
| 17 | Mô tả pipeline CI của bạn từ lúc mở PR đến lúc merge. | 3.2 |
| 18 | `state:modified+` và `--defer` hoạt động thế nào? | 3.2 |
| 19 | Manifest prod của bạn được lưu ở đâu và cập nhật khi nào? | 3.2, 3.3 |
| 20 | `manifest.json` vs `catalog.json`? | 3.3 |
| 21 | Contract khác data test thế nào? Snowflake có enforce `primary_key` không? | 3.4 |
| 22 | Exposure dùng để làm gì trong thực tế? | 3.5 |
| 23 | Freshness bắt lỗi gì? Chọn `loaded_at_field` ra sao? | 3.6 |
| 24 | pre-commit và CI khác nhau thế nào, tại sao cần cả hai? | 3.7 |

## Câu hỏi tình huống (dạng phỏng vấn)

1. **Dashboard doanh thu tháng trước bỗng thấp hơn hôm qua 5%.** Bạn điều tra theo thứ tự nào? (gợi ý: freshness → test → lineage/exposure → so incremental vs full refresh → late-arriving data)
2. **Model `fct_sales` incremental build 40 phút, tăng dần mỗi tuần.** Bạn xem xét những gì? (chiến lược, `incremental_predicates`, lookback quá dài, clustering/partition)
3. **Team BI phàn nàn cột `customer_name` trong dim bị đổi tên làm vỡ dashboard.** Lẽ ra cơ chế nào ngăn được? (contract + exposure + slim CI, model versions)
4. **Đồng nghiệp hỏi: "sao không build cả project trong CI cho chắc?"** Bạn trả lời thế nào? (chi phí, thời gian, `state:modified+` đã bao downstream)
5. **Kế toán cần biết giá sản phẩm tại ngày bán, không phải giá hiện tại.** Bạn thiết kế thế nào? (snapshot check trên giá → dim SCD2 → join theo khoảng hiệu lực)

## Câu tự giới thiệu project (luyện nói 60 giây)

Chuẩn bị 1 đoạn mô tả `adventure_works` gồm: kiến trúc 3 tầng, số model/test, 3 chiến lược incremental và lý do, snapshot SCD2, CI/CD (lint + slim CI + docs tự deploy), contracts/exposures/freshness. Kết thúc bằng 1 vấn đề khó bạn đã giải quyết (ví dụ: dữ liệu trễ bị mất khi chưa có lookback).
