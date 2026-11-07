# 9.5 Xử lý sự cố dữ liệu và incident runbook

## Vòng đời một sự cố

```
phát hiện → phân loại (SEV) → thông báo → khoanh vùng → khắc phục tạm → sửa gốc → backfill / restate → đóng → postmortem
```

| Bước | Câu hỏi | Ví dụ lab: ngày 6, giá app theo nghìn đồng |
|---|---|---|
| Phát hiện | Ai / cái gì thấy trước? | `accepted_range` trên `stg_shop__order_items.unit_price` fail lúc 06:31 |
| Phân loại | Ảnh hưởng ai, bao nhiêu? | Doanh thu ngày 06/12 sai, dashboard ban giám đốc → **SEV2** |
| Thông báo | Ai cần biết, qua đâu? | #data-incidents + #finance: "số 06/12 chưa có, đang xử lý" |
| Khoanh vùng | Bảng nào, khoảng thời gian nào, nguyên nhân? | Chỉ đơn `channel = 'app'` ngày 06/12, bản phát hành app 06/12 |
| Khắc phục tạm | Giữ người dùng an toàn | `fct_order_items` đã bị skip, dashboard giữ số 05/12 |
| Sửa gốc | Ai sửa, ở đâu? | Đội app sửa và restate dữ liệu ngày 06/12 |
| Backfill | Cần build lại gì? | Ngày 7 dữ liệu đúng về, `dbt build` bình thường. Kiểm tra lại doanh thu 06/12 |
| Postmortem | Làm gì để không lặp lại? | Đề xuất data contract với đội app: test giá trong CI của app |

## Mức độ nghiêm trọng

| SEV | Định nghĩa | Phản hồi | Ví dụ |
|---|---|---|---|
| **SEV1** | Số sai đã lên tay người ra quyết định / khách hàng, hoặc mất dữ liệu không lấy lại được | Ngay lập tức, cả giờ ngoài làm việc | Báo cáo sai đã gửi ngân hàng / đối tác |
| **SEV2** | Dashboard quan trọng sai hoặc trễ quá SLA | Trong giờ làm việc, trước SLA kế tiếp | Doanh thu ngày bị chặn, connector chết > 24h |
| **SEV3** | Ảnh hưởng nhỏ, có cách tạm | Trong tuần | Phương thức thanh toán mới chưa có trong danh sách |

## Mẫu runbook cho một loại cảnh báo

```markdown
## RB-03: Volume anomaly trên shop.orders

**Tín hiệu:** elementary volume_anomalies (drop) trên source shop.orders · severity warn
**Chủ:** Commerce Analytics (commerce-data@mayshop.vn) · trực: xem lịch on-call
**Mức mặc định:** SEV2 nếu giảm > 50%, SEV3 nếu 20–50%

### Chẩn đoán (≤ 15 phút)
1. Elementary: test_results_description → giá trị vs trung bình
2. Nhật ký connector: select * from ingest.sync_log where table_name = 'shop.orders' order by synced_at desc limit 5;
3. So với nguồn: số đơn trong admin của website cùng ngày
4. Phân theo chiều: select channel, count(*) ... group by 1 (app hay web, hay cả hai?)

### Nguyên nhân thường gặp → xử lý
| Nguyên nhân | Xử lý |
|---|---|
| Connector timeout / nạp dở | Chạy lại sync (resync) → dbt build lại phần bị ảnh hưởng |
| Website lỗi thật (doanh số thật giảm) | Không phải lỗi dữ liệu → báo đội sản phẩm, đóng sự cố |
| Ngày lễ / khuyến mãi kết thúc | Ghi chú, cân nhắc seasonality / loại trừ ngày đặc biệt |

### Thông báo người dùng
"Số đơn ngày dd/mm trên dashboard [X] đang thiếu khoảng N%, nguyên nhân [..], dự kiến đủ lúc [..]."

### Sau sự cố
- [ ] Có cần backfill incremental model nào không? (`dbt build -s fct_orders+ --full-refresh` hay chỉ chạy lại ngày đó)
- [ ] Cập nhật runbook nếu gặp nguyên nhân mới
```

## Postmortem không đổ lỗi (blameless)

Mẫu ngắn:

1. **Tóm tắt** (3 câu): chuyện gì, ảnh hưởng ai, bao lâu.
2. **Dòng thời gian**: lúc lỗi xảy ra, lúc phát hiện, lúc thông báo, lúc khắc phục. Đo TTD, TTR.
3. **Nguyên nhân gốc**: hỏi "vì sao" 5 lần. Dừng ở **quy trình / hệ thống**, không dừng ở "bạn A quên".
4. **Điều gì đã chạy tốt** (test đã chặn đúng chỗ).
5. **Hành động**: mỗi việc có chủ và hạn chót.

## Từ lab tới CV

Sau tuần 9, bạn có thể viết trong CV/portfolio những dòng **có số** như:

- "Thiết kế DQ framework: SLA freshness cho 7 nguồn, anomaly detection (Elementary) cho 3 bảng chính, data contract cho 8 model public. Mô phỏng 6 loại sự cố production, framework bắt 6/6 đúng ngày, 0 báo động giả ở ngày sạch."
- "Viết incident runbook cho 6 loại cảnh báo, mỗi loại có các bước chẩn đoán, xử lý và mẫu thông báo cho người dùng."

## Câu hỏi tự kiểm tra

1. Sự cố Q1 (connector mkt chết 3 ngày) nên là SEV mấy? Metric nào bị ảnh hưởng, và báo cho ai?
2. Viết postmortem 1 trang cho sự cố Q5 (CRM đổi tên cột).
3. Vì sao postmortem "đổ lỗi" làm hệ thống kém an toàn hơn?
