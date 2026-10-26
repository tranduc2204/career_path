# Câu hỏi ôn tập GĐ2 (mức Mid AE)

> Trả lời miệng hoặc viết ra **không nhìn tài liệu**, tối đa 2 phút mỗi câu. Đáp án nằm trong file lý thuyết tương ứng (cột "Xem"). Câu có ⭐ là câu phỏng vấn Mid hay gặp.

## Kimball (tuần 4)

| # | Câu hỏi | Xem |
|---|---|---|
| 1 | ⭐ Trình bày quy trình thiết kế 4 bước của Kimball bằng một ví dụ của bạn. | 4.1 |
| 2 | ⭐ "Grain" là gì? Vì sao phải khai báo grain trước khi chọn dimension và fact? | 4.1 |
| 3 | Atomic grain là gì? Vì sao không chọn grain đã tổng hợp sẵn? | 4.1 |
| 4 | ⭐ So sánh transaction, periodic snapshot, accumulating snapshot. Mỗi loại 1 ví dụ. | 4.1, 4.6 |
| 5 | Measure additive, semi-additive, non-additive khác nhau thế nào? "Tồn kho tháng 3" tính ra sao? | 4.1, 4.6 |
| 6 | Phí ship nằm ở đầu đơn, fact ở grain dòng đơn: xử lý thế nào để tổng vẫn đúng từng đồng? | 4.1 |
| 7 | ⭐ Conformed dimension là gì? Shrunken dimension là gì? | 4.2 |
| 8 | ⭐ Bus matrix dùng để làm gì trong một dự án thật? | 4.2 |
| 9 | Drill-across là gì? Vì sao không join 2 fact với nhau trực tiếp? | 4.2 |
| 10 | Surrogate key, natural key, durable key khác nhau thế nào? | 4.3 |
| 11 | Thành viên `-1` và `-2` để làm gì? Vì sao khoá ngoại của fact không nên null? | 4.3 |
| 12 | Role-playing, junk, degenerate dimension: định nghĩa + ví dụ. | 4.3 |
| 13 | ⭐ Kể các loại SCD từ 0 tới 7. Type 6 giải quyết bài toán gì? | 4.3 |
| 14 | Mini-dimension giải quyết vấn đề gì? | 4.3 |
| 15 | ⭐ Bridge table dùng khi nào? Weighting factor là gì? Weighted và impact khác nhau thế nào? | 4.4 |
| 16 | Closure table cho cây không đều lưu gì? Vì sao không được cộng doanh thu ở mọi nút? | 4.4 |
| 17 | Factless fact là gì? Câu hỏi kinh doanh nào chỉ factless trả lời được? | 4.5 |
| 18 | Accumulating snapshot xử lý sự kiện về sai thứ tự thế nào? Viết incremental cho nó cần lưu ý gì? | 4.6 |
| 19 | ⭐ Fact tới trước dimension: kể 3 cách xử lý, bạn chọn cách nào, vì sao? | 4.7 |
| 20 | Inferred member: vì sao ghi đè là Type 1? Thiết kế khoá để fact không phải đổi khoá thế nào? | 4.7 |

## BigQuery, môi trường, CD (tuần 5)

| # | Câu hỏi | Xem |
|---|---|---|
| 21 | Project, dataset, location của BigQuery tương ứng với gì ở dbt và Snowflake? | 5.1 |
| 22 | Vì sao BigQuery sandbox không chạy được model incremental của dbt? | 5.1 |
| 23 | `maximum_bytes_billed` hoạt động thế nào? | 5.1 |
| 24 | ⭐ Mô tả 3 môi trường dev / staging(CI) / prod của bạn: ai chạy, ghi vào đâu, xác thực thế nào. | 5.3 |
| 25 | 1 GCP project hay nhiều project? Bạn chọn gì, vì sao? | 5.3 |
| 26 | Viết `generate_schema_name` để prod có dataset gọn còn dev/CI có tiền tố. | 5.3 |
| 27 | ⭐ Vòng đời một thay đổi: PR → CI → merge → CD → cleanup. Manifest prod nằm ở đâu, ai ghi, khi nào? | 5.4 |
| 28 | Workload Identity Federation là gì? Vì sao an toàn hơn key JSON? | 5.4 |
| 29 | Làm sao đảm bảo một nhánh feature không thể ghi vào prod, kể cả khi sửa workflow? | 5.4 |
| 30 | Deploy làm sai số liệu: bạn rollback thế nào trên BigQuery? | 5.4 |

## Data Vault (tuần 6)

| # | Câu hỏi | Xem |
|---|---|---|
| 31 | ⭐ Data Vault giải quyết những vấn đề gì mà star schema xử lý vất vả? | 6.1 |
| 32 | Kiến trúc 4 tầng của Data Vault. Hard rule và soft rule khác nhau thế nào? | 6.1 |
| 33 | ⭐ Hub, link, satellite chứa gì, không chứa gì? | 6.1, 6.2 |
| 34 | Hash key hơn sequence key ở điểm nào? Vì sao phải chuẩn hoá business key trước khi băm? | 6.2 |
| 35 | Hashdiff hoạt động thế nào? Vì sao A → B → A sinh 3 dòng satellite? | 6.2 |
| 36 | Tách satellite theo những tiêu chí nào? | 6.2 |
| 37 | Effectivity satellite, multi-active satellite, non-historized link: khi nào dùng? | 6.2 |
| 38 | ⭐ Load date và effective date khác nhau thế nào? Báo cáo nào dùng cái nào? | 6.2, 6.5 |
| 39 | `apply_source_filter` của automate_dv giải quyết lỗi gì? Giải thích cơ chế gây ra dòng trùng. | 6.3 |
| 40 | PIT table giải quyết vấn đề gì? Ghost record trong PIT để làm gì? | 6.4 |
| 41 | Bridge của Data Vault khác bridge của Kimball thế nào? | 6.4 |
| 42 | Dựng dimension SCD2 từ vault: danh sách thực thể, Type 1, Type 2, inferred member lấy từ đâu? | 6.5 |
| 43 | ⭐ Data Vault hay Kimball? (trả lời bằng ADR của bạn, có số đo) | 6.6 |
| 44 | ADR gồm những phần nào? Quyết định đổi thì xử lý ADR cũ thế nào? | 6.6 |

## Performance và chi phí (tuần 7)

| # | Câu hỏi | Xem |
|---|---|---|
| 45 | ⭐ Snowflake và BigQuery on-demand tính tiền theo gì? Hệ quả cho việc tối ưu? | 7.1 |
| 46 | Kể phương pháp tối ưu 6 bước. Vì sao chỉ đổi 1 thứ mỗi lần? | 7.1 |
| 47 | Micro-partition là gì? Pruning hoạt động thế nào? Dấu hiệu pruning kém trong Query Profile? | 7.2 |
| 48 | ⭐ Khi nào đáng đặt clustering key trên Snowflake? Chi phí ẩn của nó? | 7.2 |
| 49 | Spilling là gì? Xử lý thế nào? | 7.2, 7.3 |
| 50 | ⭐ Scale up và scale out khác nhau thế nào? Chọn cỡ warehouse bằng thí nghiệm ra sao? | 7.3 |
| 51 | Resource monitor có những hành động nào? Giới hạn của nó? | 7.3 |
| 52 | Điều kiện nào làm mất partition pruning trên BigQuery? | 7.4 |
| 53 | ⭐ Partition hay cluster? Khi nào chỉ cluster? | 7.4 |
| 54 | `merge` vs `insert_overwrite` trên BigQuery: chi phí khác nhau thế nào? `_dbt_max_partition` là gì? | 7.4 |
| 55 | Làm sao biết model dbt nào tốn tiền nhất trên BigQuery? Trên Snowflake? | 7.3, 7.5 |
| 56 | Vì sao loại `statement_type = 'SCRIPT'` khi cộng chi phí từ `INFORMATION_SCHEMA.JOBS`? | 7.5 |

## Câu hỏi tình huống (dạng phỏng vấn)

1. **Sếp muốn "một bảng doanh thu để làm dashboard".** Bạn bắt đầu từ đâu? (gợi ý: quy trình nghiệp vụ, grain nguyên tử, conformed dimension, không làm bảng theo báo cáo)
2. **Doanh thu theo voucher trên dashboard cộng lại lớn hơn tổng doanh thu 15%.** Chuyện gì xảy ra? Sửa thế nào? (gợi ý: bridge, impact vs weighted)
3. **Kế toán: "doanh thu tháng 2 của ngành Điện tử tự nhiên giảm sau khi IT đổi danh mục sản phẩm".** Giải thích và đề xuất. (gợi ý: SCD Type 1 trên danh mục, cân nhắc Type 2 hoặc Type 6)
4. **Báo cáo "đơn mất bao nhiêu ngày để giao" cho kết quả quá đẹp.** Bạn kiểm tra gì? (gợi ý: lag = 0 cho đơn chưa giao, mốc null, sự kiện về trễ)
5. **Đơn hàng về trước thông tin khách 1 ngày, doanh thu theo khu vực của hôm qua có một khoản "Không xác định".** Bạn thiết kế lại thế nào? (gợi ý: inferred member, khoá ổn định)
6. **Công ty sắp mua thêm 2 chuỗi cửa hàng, mỗi chuỗi một phần mềm, mã khách khác nhau.** Kimball hay Data Vault cho tầng tích hợp? (gợi ý: same-as link, hub đa nguồn, ADR)
7. **Một PR sửa model staging, CI chạy 40 phút và build lại cả project.** Bạn kiểm tra gì? (gợi ý: manifest prod có tải được không, quyền bucket, `state:modified+`, `--defer`)
8. **Hoá đơn BigQuery tháng này gấp 3 tháng trước.** 30 phút đầu bạn làm gì? (gợi ý: JOBS theo ngày → theo user → theo label → top query → cầm máu → sửa gốc → rào chắn)
9. **Model dbt chạy 25 phút trên Snowflake Medium. Đồng nghiệp đề xuất lên X-Large.** Bạn trả lời thế nào? (gợi ý: Query Profile trước: spill? exploding join? pruning? rồi mới thí nghiệm cỡ)
10. **Nhà tuyển dụng hỏi: "kho của bạn có dựng lại được từ đầu không?"** (gợi ý: phụ thuộc nguồn có giữ lịch sử không; snapshot/vault chụp nguồn ghi đè; thí nghiệm `goto 6` của lab)

## Câu tự giới thiệu (luyện nói 60 giây mỗi đoạn)

**adventure_works (sau GĐ2):** bus matrix và các quy trình; 1 accumulating snapshot, 1 bridge, 1 factless và lý do; raw vault cho vài thực thể lõi bằng automate_dv; ADR chọn kiến trúc lai, có số đo; performance playbook phần Snowflake (một kết quả cụ thể, ví dụ "sắp xếp dữ liệu giảm partitions scanned từ X% xuống Y%").

**thelook (project 2):** 3 môi trường, vòng đời PR → CI → CD → cleanup, WIF không key, prod chỉ cho nhánh main; chi phí cả tháng và rào chắn; một kết quả cụ thể từ playbook phần BigQuery (ví dụ "`insert_overwrite` giảm byte tính tiền của fct_events từ X xuống Y mỗi lần chạy").

Kết thúc bằng **một quyết định khó** bạn đã đưa ra và bảo vệ được bằng số liệu.
