# 16.10 Đề 8: Dashboard "gần thời gian thực"

> Đề hay gặp ở công ty TMĐT, ví điện tử, logistics. Bẫy chính: **real-time cho mọi thứ**. Bạn có kinh nghiệm Estuary (CDC / streaming): dùng làm dẫn chứng.

## Đề

> *"Trong flash sale 11/11, đội vận hành muốn xem doanh thu, số đơn, tỉ lệ thanh toán thất bại theo phút. Hiện dbt chạy mỗi giờ trên BigQuery. Thiết kế giúp chúng tôi."*

## Bước 1: Làm rõ (quan trọng nhất của đề này)

| Câu hỏi | Vì sao |
|---|---|
| "Theo phút" là độ trễ bao nhiêu thì chấp nhận được: 10 giây, 1 phút, 5 phút? | Mỗi bậc là một kiến trúc khác nhau, chi phí khác nhau 10 lần |
| Ai xem, làm gì khi thấy số? | Vận hành bật/tắt khuyến mãi, gọi đội thanh toán → cần **cảnh báo**, không chỉ dashboard |
| Số này có phải số chính thức không? | Không → được phép "tạm tính", đối soát lại với số batch hôm sau |
| Bao nhiêu metric, bao nhiêu chiều? | 5–10 metric, vài chiều (kênh, cổng thanh toán) → mô hình nhỏ |
| Quy mô đỉnh? | 50.000 đơn/phút lúc 0 giờ |
| Kéo dài bao lâu? | Vài ngày sale/năm hay thường xuyên? |

Giả định chốt: trễ **≤ 1–2 phút**, 6 metric, không phải số chính thức, dùng trong sự kiện + vận hành hằng ngày.

## Các phương án

| Phương án | Trễ | Độ phức tạp | Chi phí | Khi nào |
|---|---|---|---|---|
| A. dbt incremental chạy mỗi 5–15 phút | 5–20 phút | Thấp (đã có dbt) | Trung bình (mỗi lần chạy có chi phí khởi động) | Trễ 15 phút là đủ |
| B. **Warehouse tự làm mới**: BigQuery materialized view / continuous queries, Snowflake dynamic tables (target lag) | ~1 phút–vài phút | Thấp–trung bình | Theo tải | Đa số trường hợp "theo phút" |
| C. Stream processing (Flink, Spark Structured Streaming, Kafka Streams) → bảng tổng hợp / OLAP real-time (ClickHouse, Druid, Pinot) | giây | Cao (đội DE vận hành) | Cao | Cần giây, tải rất lớn, hoặc phát hiện gian lận |
| D. Metric tính ngay ở ứng dụng (đếm trong Redis / Prometheus) | giây | Trung bình | Thấp | Metric vận hành kỹ thuật (tỉ lệ lỗi cổng thanh toán) |

## Thiết kế đề xuất (cho giả định trên)

```
app / payment ──events──▶ Pub/Sub ──▶ BigQuery (streaming insert / Storage Write API)   raw_events (partition theo giờ)
                                              │
                         ┌────────────────────┴─────────────────────┐
                LUỒNG NHANH (tạm tính)                         LUỒNG CHÍNH THỨC (batch, dbt)
         materialized view / bảng tổng hợp theo phút           dbt hằng giờ / hằng ngày → marts → semantic layer
         chỉ 6 metric, 3 chiều, 48 giờ gần nhất                 số chính thức, đã khử trùng, đối soát
                         │                                              │
           dashboard vận hành (refresh 1 phút) + cảnh báo         dashboard quản trị
           ghi rõ "số tạm tính"                                   
                         └──────── đối soát hằng ngày: tổng luồng nhanh vs luồng chính (lệch < 0,5%) ────────┘
```

Điểm phải nói:

- **Hai luồng, một định nghĩa:** định nghĩa metric viết một lần (tài liệu / semantic layer), luồng nhanh là bản đơn giản hoá có ghi chú khác biệt (vd chưa trừ đơn huỷ sau 30 phút).
- **Sự kiện trễ và trùng:** cửa sổ theo **thời gian sự kiện**, chấp nhận cập nhật lại 5–10 phút gần nhất; khử trùng theo `event_id`.
- **Không bắt dbt làm việc của streaming:** dbt mạnh ở batch / micro-batch. Chạy dbt mỗi phút tốn kém và dễ chồng lấn job.
- **Cảnh báo quan trọng hơn dashboard:** tỉ lệ thanh toán thất bại > ngưỡng trong 3 phút → báo đội thanh toán. Không ai ngồi nhìn dashboard cả đêm.
- **Chi phí:** giới hạn dữ liệu nóng 48 giờ, partition theo giờ, dashboard đọc bảng tổng hợp nhỏ (không đọc raw).

## Câu hỏi đào sâu

1. **"Sao không dùng Kafka + Flink cho chắc?"** → Có thể, nếu cần giây hoặc đã có đội DE vận hành. Với trễ 1–2 phút, tính năng làm mới của warehouse rẻ và đơn giản hơn nhiều. Chọn công cụ theo yêu cầu độ trễ, không theo xu hướng.
2. **"Số nhanh và số chính thức lệch nhau thì sao?"** → Bình thường. Ghi rõ "tạm tính", đối soát hằng ngày, theo dõi tỉ lệ lệch. Lệch vượt ngưỡng là sự cố.
3. **"Lambda vs kappa?"** → Lambda: hai luồng như trên (nhanh + batch). Kappa: một luồng streaming, tính lại bằng phát lại log. Với AE, lambda "nhẹ" (streaming ingest + batch dbt) là thực tế nhất.

## Kể bằng kinh nghiệm của bạn

> *"Ở Estuary em làm với [CDC / streaming connector...]. Bài học là độ tươi tính bằng giây có giá: trùng, sai thứ tự, schema đổi giữa chừng. Nên với mỗi yêu cầu 'real-time' em hỏi lại độ trễ thật sự cần và ai hành động dựa trên số đó."* (Điền chi tiết thật. Người phỏng vấn sẽ hỏi.)
