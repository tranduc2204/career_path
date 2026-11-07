# 16.11 Ngân hàng đề luyện thêm (14 đề)

> Mỗi đề có: bối cảnh, **3 câu phải hỏi**, **quyết định then chốt**, **bẫy**, và mẫu nào trong [16.2](02-thu-vien-mau-thiet-ke.md) dùng được. Không có lời giải đầy đủ: tự làm 30–45 phút, chấm bằng [16.12](12-phieu-tu-cham.md).
> `python tools/drill.py` rút ngẫu nhiên các đề này (cùng đề 1–8) và chạy đồng hồ.

---

### D1. Customer 360 cho chuỗi bán lẻ omnichannel
Website, app, 300 cửa hàng (POS), CRM, chương trình khách hàng thân thiết. Muốn "một khách một hồ sơ".
- **Hỏi:** khoá nhận diện nào có ở mỗi nguồn (SĐT, email, thẻ thành viên)? Khách vãng lai ở POS chiếm bao nhiêu? Ai dùng hồ sơ (marketing, CSKH)?
- **Quyết định:** identity resolution (deterministic theo SĐT chuẩn hoá trước, probabilistic sau), bảng `customer_identity_map` có lịch sử, master key ổn định; hồ sơ = dimension SCD + bảng đặc trưng (RFM, LTV).
- **Bẫy:** gộp nhầm 2 người dùng chung SĐT; tách nhầm khi đổi SĐT; PII và đồng ý tiếp thị (consent).
- **Mẫu:** C (SCD, bridge), H (PII), D (late-arriving dimension).

### D2. Hệ thống tính hoa hồng cho đội sale
Hoa hồng theo bậc doanh số, đổi chính sách theo quý, có hoàn đơn sau khi chi trả.
- **Hỏi:** chính sách đổi thế nào, có áp hồi tố không? Hoàn đơn sau chi trả thì thu hồi ra sao? Ai duyệt bảng hoa hồng?
- **Quyết định:** chính sách là dữ liệu có hiệu lực theo thời gian (seed/bảng SCD2), không hard-code; tính theo kỳ, **khoá kỳ** sau khi duyệt; điều chỉnh kỳ sau cho hoàn đơn; lưu as-reported.
- **Bẫy:** tính lại kỳ đã trả; làm tròn; nhân viên đổi team giữa kỳ.

### D3. Báo cáo marketing đa kênh (Google, Meta, TikTok) và attribution
- **Hỏi:** mô hình attribution nào (last-click, đa chạm)? Tiền tệ, múi giờ của từng nền tảng? Dữ liệu nền tảng có bị sửa lại sau vài ngày không?
- **Quyết định:** chuẩn hoá chi phí về một grain (ngày × chiến dịch × nền tảng), conformed `dim_campaign`, lookback 7–28 ngày vì nền tảng cập nhật lại số, attribution là model riêng có thể đổi.
- **Bẫy:** cộng conversion của các nền tảng (mỗi nền tảng tự nhận công) → vượt số đơn thật.

### D4. Kho dữ liệu cho SaaS B2B (subscription, MRR, churn)
- **Hỏi:** nâng/hạ gói giữa kỳ tính thế nào? Ghi nhận doanh thu theo kế toán hay theo hoá đơn? Định nghĩa churn (khách hay doanh thu)?
- **Quyết định:** `fct_subscription_daily` (periodic snapshot), sự kiện MRR (new, expansion, contraction, churn, reactivation), metric NRR/GRR ở semantic layer.
- **Bẫy:** MRR là semi-additive; hoá đơn năm ≠ MRR × 12; múi giờ khách.

### D5. Tối ưu chi phí warehouse đang tăng 30%/tháng
- **Hỏi:** chi phí nằm ở đâu (dbt, BI, ad-hoc)? Có gắn nhãn theo người/đội không? Cam kết hợp đồng?
- **Quyết định:** đo trước (query tag / job label, INFORMATION_SCHEMA), top 20 truy vấn, rồi mới tối ưu: incremental, partition/cluster, tách warehouse, auto-suspend, aggregate cho BI, giới hạn byte, chargeback theo đội.
- **Bẫy:** tối ưu dbt trong khi 70% chi phí là dashboard. (GĐ2 tuần 7.)

### D6. Nền tảng dữ liệu cho chuỗi phòng khám (dữ liệu nhạy cảm)
- **Hỏi:** quy định về dữ liệu sức khoẻ? Ai được xem cấp bệnh nhân? Dữ liệu được ra khỏi bệnh viện không?
- **Quyết định:** phân loại dữ liệu nhạy cảm, khoá ẩn danh (pseudonymization) ngay từ staging, mart phân tích chỉ có dữ liệu đã ẩn danh / tổng hợp, quyền theo mục đích, audit truy cập.
- **Bẫy:** tái nhận diện từ tổ hợp (ngày sinh + phường + giới tính).

### D7. Data contract giữa đội app và đội dữ liệu cho event tracking
- **Hỏi:** ai định nghĩa sự kiện? Có schema registry chưa? Bao nhiêu sự kiện, đổi thường xuyên không?
- **Quyết định:** tracking plan dạng code (JSON Schema / YAML) review cùng PR của app, kiểm tra ở CI của app, schema registry chặn sự kiện sai; phía dữ liệu có `schema_changes` + quarantine bảng cho sự kiện không khớp.
- **Bẫy:** chỉ kiểm ở phía dữ liệu, sau khi sự kiện sai đã vào.

### D8. Chuyển từ Redshift sang Snowflake / BigQuery (200 model dbt)
- **Hỏi:** lý do chuyển? Dừng hệ thống cũ được bao lâu? SQL đặc thù Redshift nhiều không?
- **Quyết định:** chuyển ingest song song, dbt đa adapter qua `dispatch`/cross-db macro, đối chiếu tự động từng model (như đề 4), cắt chuyển theo domain.
- **Bẫy:** khác biệt kiểu số/collation/timestamp, hành vi `NULL` trong sort, chi phí chạy song song.

### D9. Báo cáo tồn kho đa kho, nhiều đơn vị tính
- **Hỏi:** sự kiện kho có về trễ không? Điều chỉnh kiểm kê có lùi ngày không? Quy đổi đơn vị (thùng/hộp/cái)?
- **Quyết định:** fact biến động + periodic snapshot tồn cuối ngày dày đặc, quy đổi về đơn vị cơ sở, tính lại từ ngày bị ảnh hưởng. (Lab GĐ2 K9.)
- **Bẫy:** cộng tồn kho theo ngày; snapshot thưa.

### D10. Self-serve analytics cho 300 nhân viên không biết SQL
- **Hỏi:** họ đang dùng gì (Excel)? Câu hỏi phổ biến? Ai hỗ trợ?
- **Quyết định:** semantic layer + BI có explore, bộ dataset certified có tài liệu, đào tạo, "data champion" ở mỗi phòng ban, chính sách: dataset không certified hiện cảnh báo.
- **Bẫy:** mở thẳng warehouse cho mọi người → chi phí + sai số.

### D11. Feature store / bảng đặc trưng cho đội ML (từ góc AE)
- **Hỏi:** cần đặc trưng tại thời điểm dự đoán (point-in-time) không? Online hay chỉ batch? Ai sở hữu định nghĩa đặc trưng?
- **Quyết định:** bảng đặc trưng theo thực thể × ngày, **point-in-time correct** (không rò rỉ tương lai), dùng chung định nghĩa với metric ở semantic layer khi có thể.
- **Bẫy:** join đặc trưng "hiện tại" vào dữ liệu huấn luyện quá khứ (data leakage).

### D12. Hệ thống báo cáo cho công ty mẹ với 5 công ty con (hợp nhất)
- **Hỏi:** mỗi công ty con dùng ERP khác nhau? Hệ thống tài khoản kế toán khác nhau? Giao dịch nội bộ giữa các công ty con?
- **Quyết định:** chart of accounts chuẩn + bảng ánh xạ theo từng công ty (có chủ, có lịch sử), loại trừ giao dịch nội bộ khi hợp nhất, tỷ giá hợp nhất, multi-repo hoặc Mesh theo công ty con.
- **Bẫy:** cộng thẳng doanh thu có giao dịch nội bộ.

### D13. Thiết kế lại một dbt project "bùng nổ" (900 model, không chuẩn tên, 40% không dùng)
- **Hỏi:** model nào có người dùng (exposure, query log)? CI hiện có gì? Ai làm owner?
- **Quyết định:** kiểm kê bằng manifest + query log, xoá model không dùng, chuẩn tên và tầng, groups/owner, contract cho giao diện, lộ trình refactor theo domain không dừng hệ thống.
- **Bẫy:** "viết lại từ đầu".

### D14. Lineage và tác động thay đổi xuyên công cụ (nguồn → dbt → BI)
- **Hỏi:** BI nào? Có catalog chưa? Câu hỏi thường gặp là gì ("đổi cột này ảnh hưởng dashboard nào")?
- **Quyết định:** catalog (OpenMetadata/DataHub) ingest dbt artifacts + metadata BI, lineage cấp cột nếu có, exposures cho dashboard quan trọng, comment tác động tự động lên PR.
- **Bẫy:** chỉ có lineage trong dbt, không thấy dashboard.

---

## Câu hỏi "Senior" ngắn (5–10 phút mỗi câu)

1. Khi nào bạn **không** dùng dbt?
2. Kimball có còn hợp thời khi warehouse đã rất nhanh và rẻ? (One Big Table vs star schema)
3. Data mesh: lợi ích thật và cái giá thật. Công ty 30 người dữ liệu có nên làm không?
4. Bạn thuyết phục ban giám đốc đầu tư vào chất lượng dữ liệu thế nào?
5. Một đội muốn dùng Python model cho logic phức tạp. Bạn đặt ranh giới SQL / Python ở đâu?
6. Làm sao giữ chuẩn code khi đội tăng từ 5 lên 25 người?
7. Đội bạn bị yêu cầu "real-time mọi thứ". Bạn đàm phán thế nào?
8. Kể một quyết định kiến trúc bạn từng sai và đã sửa ra sao.
