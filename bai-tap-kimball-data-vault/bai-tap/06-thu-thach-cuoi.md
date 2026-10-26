# 06 — Thử thách cuối

## 1. Chạy trọn bộ

```bash
./scripts/replay.sh
```

Mục tiêu: **21/21 PASS** (K2–K14, V1–V8), `dbt build` của mọi ngày xanh, không thao tác tay nào ngoài `replay.sh`.

## 2. Viết lại bằng lời (quan trọng nhất)

Trong `lab/NOTES.md`, trả lời ngắn gọn. Đây là thứ bạn sẽ nói trong phỏng vấn:

1. **Bus matrix** của Mây Shop (bảng) + 1 câu grain cho mỗi fact.
2. Bảng "fact – loại – vì sao chọn loại này – cái giá phải trả" cho 5 fact.
3. 3 cách xử lý **late-arriving dimension**, cách bạn chọn và vì sao khoá phải ổn định.
4. Khác nhau giữa `weighted` và `impact` ở báo cáo voucher, kèm số liệu thật của lab.
5. 3 "cái bẫy" của Data Vault bạn đã gặp (V3, V4, V6), mỗi bẫy: triệu chứng → nguyên nhân → cách sửa → cách phát hiện sớm.
6. Bảng so sánh Kimball vs Data Vault bằng **số đo của chính bạn** (file 05, bước 1–4).

## 3. Thử thách mở (không có trong check.py)

| # | Cấp | Thử thách |
|---|---|---|
| C1 | ⭐⭐⭐⭐ | Đổi `fct_sales` sang **incremental** (`merge` theo `order_number, line_no`, watermark `_loaded_at`). Phải xử lý: đơn bị huỷ sau khi đã nạp (W0013), POS về trễ, và **khoá khách inferred**. Kiểm chứng: `replay.sh` vẫn PASS K5–K7. |
| C2 | ⭐⭐⭐⭐ | Đổi `fct_order_fulfillment` sang **incremental merge**. Mỗi lần chạy chỉ xử lý đơn có đầu đơn đổi hoặc có sự kiện kho mới. W0006 (sự kiện về sai thứ tự) phải đúng. |
| C3 | ⭐⭐⭐ | `fct_inventory_daily` incremental: chỉ tính lại từ ngày biến động **sớm nhất** trong các dòng mới nạp (điều chỉnh lùi ngày ở ngày 3). |
| C4 | ⭐⭐⭐ | **Mini-dimension**: tách `loyalty_tier` (đổi thường xuyên) khỏi `dim_customer` thành `dim_customer_tier`, fact mang cả 2 khoá. So số dòng `dim_customer` trước/sau. |
| C5 | ⭐⭐⭐ | **SCD Type 6** (1 + 2 + 3): thêm cột `current_city` vào `dim_customer` (mọi phiên bản mang thành phố hiện tại). Viết báo cáo doanh thu theo thành phố lúc mua và theo thành phố hiện tại trong 1 query. |
| C6 | ⭐⭐⭐ | **Hierarchical link** `link_category_hierarchy` (danh mục ↔ danh mục cha) thay cho cột `parent_code` trong satellite. Dựng lại closure table của K12 **từ vault**. |
| C7 | ⭐⭐⭐⭐ | **Same-as link**: thêm nguồn giả lập "sàn TMĐT" có mã khách riêng (tự tạo seed `marketplace_customer_map.csv`: `TIKI_xxx → Cxxx`). Hub giữ cả 2 mã, `sat_link` ánh xạ, information mart gộp doanh thu về 1 khách. |
| C8 | ⭐⭐⭐ | **Computed satellite** trong business vault: `bsat_customer_value` tính tổng chi tiêu và phân hạng giá trị (A/B/C) từ vault. Vì sao đặt ở business vault chứ không phải raw vault? |
| C9 | ⭐⭐⭐ | **DV bridge** (`automate_dv.bridge`) đi từ `hub_product` qua `link_product_category` + `eff_sat_product_category`, theo `as_of_date`. So với bridge phân cấp của Kimball (K12). |
| C10 | ⭐⭐ | Viết `dbt docs` description cho mọi fact theo mẫu: grain, loại fact, measure cộng được theo chiều nào, dimension đóng vai gì. |

## 4. Áp dụng sang `adventure_works`

Checklist chi tiết nằm ở cuối từng file lý thuyết tuần 4 và tuần 6. Tối thiểu:

- [ ] Bus matrix của adventure_works (đặt trong README + `bus_matrix.yml` như K14)
- [ ] Accumulating snapshot cho đơn hàng (`OrderDate`, `ShipDate`, `DueDate`) hoặc `Production.WorkOrder`
- [ ] Bridge `SalesOrderHeaderSalesReason` (1 đơn nhiều lý do mua)
- [ ] Factless coverage từ `SpecialOfferProduct`
- [ ] Drill-across `SalesPersonQuotaHistory` (chỉ tiêu theo quý) vs doanh thu thực tế
- [ ] Raw vault cho 3–4 thực thể lõi (customer, product, sales order, person) bằng `automate_dv` trên Snowflake
- [ ] ADR 0001 có số liệu đo được

## 5. Câu hỏi phỏng vấn tự luyện

Trả lời miệng, mỗi câu ≤ 2 phút, có ví dụ từ lab:

1. Trình bày quy trình thiết kế 4 bước của Kimball bằng một ví dụ.
2. "Grain" là gì? Kể một lần bạn thấy grain bị trộn và hậu quả.
3. Ba loại fact table chính khác nhau thế nào? Khi nào dùng accumulating snapshot?
4. Measure semi-additive là gì? Cho ví dụ và cách cộng đúng.
5. Bridge table dùng khi nào? Weighting factor để làm gì? Rủi ro lớn nhất khi dùng bridge?
6. Factless fact là gì? Câu hỏi kinh doanh nào chỉ factless trả lời được?
7. Fact tới trước dimension thì bạn làm gì? Còn fact tới muộn mấy ngày?
8. Conformed dimension là gì? Drill-across là gì? Vì sao không join 2 fact trực tiếp?
9. Bus matrix dùng để làm gì trong một dự án thật?
10. Data Vault có 3 loại bảng nào? Vì sao hub không có thuộc tính?
11. Hash key thay cho surrogate key tự tăng: được gì, mất gì?
12. Satellite tách theo tiêu chí nào? Khi nào dùng multi-active satellite, effectivity satellite?
13. PIT table giải quyết vấn đề gì?
14. Load date và effective date khác nhau thế nào? Báo cáo nào dùng cái nào?
15. Data Vault hay Kimball? (dùng ADR của bạn)
16. Vault có "dựng lại được từ đầu" không? Phụ thuộc vào cái gì?
