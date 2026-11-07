# 9.1 Khung data quality: test cái gì, ở đâu, phản ứng thế nào

## Từ "có test" đến "có framework"

Junior viết test: `unique`, `not_null` cho mọi khoá. Mid thiết kế **framework**: biết mỗi loại lỗi được bắt ở tầng nào, bằng loại kiểm tra nào, ai được báo, pipeline phản ứng ra sao, và đo được độ tin cậy theo thời gian.

Một framework DQ trả lời 5 câu:

1. **Cái gì có thể hỏng?** (chiều chất lượng)
2. **Bắt ở đâu?** (source, staging, mart, semantic, BI)
3. **Bằng gì?** (test luật, anomaly, contract, freshness, đối soát)
4. **Phản ứng ra sao?** (chặn / cảnh báo / ghi nhận) và **ai xử lý**
5. **Đo thế nào?** (SLA, số sự cố, thời gian phát hiện / khắc phục)

## Các chiều chất lượng

| Chiều | Câu hỏi | Ví dụ sự cố trong lab | Kiểm tra điển hình |
|---|---|---|---|
| **Freshness** (độ tươi) | Dữ liệu có kịp giờ không? | Connector mkt chết 3 ngày | `dbt source freshness`, `freshness_anomalies` |
| **Volume** (khối lượng) | Có đủ dòng không? | Chỉ về 30% đơn | `volume_anomalies`, so với nguồn |
| **Completeness** (đầy đủ) | Cột có bị trống bất thường? | 90% phiên mất customer_id | `not_null` (cột bắt buộc), anomaly `null_percent` (cột được phép NULL) |
| **Validity** (hợp lệ) | Giá trị có đúng miền? | `bnpl` xuất hiện, giá 299đ | `accepted_values`, `accepted_range`, regex |
| **Uniqueness** | Có trùng không? | (GĐ1: sự kiện gửi lại) | `unique`, `unique_combination_of_columns` |
| **Consistency / integrity** | Các bảng có khớp nhau? | dòng hàng không có đơn cha | `relationships`, đối soát tổng |
| **Schema** | Cấu trúc có đổi? | `phone` → `phone_number` | `schema_changes`, contract |
| **Accuracy** (chính xác) | Số có đúng với thực tế? | giá theo nghìn đồng | đối soát với hệ thống nguồn / Finance, luật nghiệp vụ |

## Kiểm tra đặt ở đâu

```
source ──────▶ staging ──────▶ intermediate ──▶ marts ──────▶ semantic / BI
freshness       hard rules:      logic join        contract,      metric "neo"
volume          unique, not_null  fan-out           test nghiệp vụ  đối soát số
schema change   accepted_values   (row count trước  relationships  với Finance
anomaly         range, regex       / sau join)
```

Nguyên tắc:

- **Bắt càng sớm càng rẻ**: lỗi bắt ở source chưa kịp lan ra 20 model.
- **Test ở nơi bạn hiểu ngữ nghĩa**: "giá ≥ 1.000đ" là luật nghiệp vụ, đặt ở staging của bảng dòng hàng. "Doanh thu ngày lệch Finance < 0,5%" đặt ở mart / semantic.
- **Đừng test lặp lại**: `unique` ở staging đã đủ, mart chỉ cần lại nếu join có thể nhân dòng.
- **Model public**: contract + test khoá + test nghiệp vụ quan trọng nhất. Đây là cam kết với người dùng.

## Test luật vs anomaly detection

| | Test luật (`accepted_range`, `not_null`...) | Anomaly (Elementary...) |
|---|---|---|
| Biết trước điều kiện đúng? | Có | Không, học từ lịch sử |
| Kết quả | Đúng/sai chắc chắn | Xác suất, có thể báo nhầm |
| Cần lịch sử | Không | Có (vài tuần) |
| Bắt được | Vi phạm luật | "Lạ so với thường ngày": thiếu dòng, NULL tăng vọt, phân phối lệch |
| Dễ giải thích | Rất dễ | Phải đọc ngưỡng, trung bình, độ lệch |

Lab có đủ hai phía: giá 299đ là vi phạm luật (Q6), còn 30% đơn và 90% NULL chỉ "lạ" chứ không vi phạm luật nào (Q2, Q3).

## Phản ứng: severity là quyết định nghiệp vụ

`dbt build` chạy theo DAG: test **error** trên một node làm **skip mọi node phía sau**. Test **warn** chỉ ghi nhận.

| Tình huống | Severity | Lý do |
|---|---|---|
| Số sai sẽ lên dashboard ban giám đốc (giá sai đơn vị, trùng đơn) | `error` | Thà số hôm qua còn hơn số sai |
| Thay đổi nghiệp vụ hợp lệ (phương thức thanh toán mới) | `warn` | Cần người cập nhật, không được chặn |
| Anomaly (thống kê) | thường `warn` | Báo nhầm thì không được chặn cả công ty |
| Test trên source | cân nhắc kỹ | Error ở source chặn **toàn bộ** nhánh phía sau |

Công cụ tinh chỉnh: `warn_if` / `error_if` (`">10"`, `">0"`), `where` (chỉ kiểm dữ liệu mới), `store_failures` (lưu dòng lỗi để điều tra), `limit`, `tags` (chọn nhóm test để chạy / bỏ qua).

```yaml
      - name: unit_price
        data_tests:
          - dbt_utils.accepted_range:
              arguments: {min_value: 1000}
              config:
                severity: error
                error_if: ">0"
                warn_if: ">0"
                store_failures: true
                where: "_loaded_at >= current_date - 3"
```

## Báo động giả là kẻ thù

Một bộ test báo đỏ 3 ngày/tuần sẽ bị tắt thông báo. Khi sự cố thật đến, không ai nhìn. Vì vậy lab **chấm cả ngày sạch** (Q7). Mỗi cảnh báo phải:

- **actionable**: người nhận biết phải làm gì (có runbook),
- **có chủ**: đến đúng người (owner của group / source),
- **hiếm**: nếu một test báo nhầm 2 lần, sửa ngưỡng hoặc bỏ nó đi.

## Đo độ tin cậy

- **Số sự cố / tháng** theo chiều chất lượng và theo nguồn.
- **TTD** (time to detect): từ lúc dữ liệu hỏng tới lúc có cảnh báo. **TTR** (time to resolve).
- **% sự cố do người dùng phát hiện trước** (càng thấp càng tốt). Đây là chỉ số đáng đưa vào CV nhất.
- **Độ phủ**: % model public có contract + test khoá + freshness của nguồn.

## Câu hỏi tự kiểm tra

1. Với mỗi chiều chất lượng, kể 1 sự cố bạn từng gặp (BRAVO, Estuary...) và test nào lẽ ra bắt được.
2. Vì sao "thà số hôm qua còn hơn số sai" không phải lúc nào cũng đúng? Ví dụ ngược lại.
3. Thiết kế chính sách severity cho `thelook` trong 5 dòng.
