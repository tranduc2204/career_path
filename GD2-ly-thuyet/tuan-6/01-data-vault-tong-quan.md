# 6.1 Data Vault 2.0: tổng quan

## Data Vault sinh ra để giải bài toán gì

Kimball (tuần 4) tối ưu cho **người dùng đọc dữ liệu**: ít bảng, dễ hiểu, query nhanh. Nhưng ở doanh nghiệp lớn, tầng tích hợp gặp những vấn đề mà star schema xử lý vất vả:

| Vấn đề | Với mô hình sao (star) | Data Vault làm gì |
|---|---|---|
| **Nhiều nguồn** cùng nói về một thực thể (CRM, web, POS, sàn TMĐT) | Phải hợp nhất ngay khi nạp, quy tắc hợp nhất cài cứng vào dimension | Mỗi nguồn giữ satellite riêng; hợp nhất để sau, ở business vault |
| Nguồn **thay đổi cấu trúc** liên tục (thêm cột, thêm hệ thống) | Sửa dimension, sửa fact, dựng lại | Thêm satellite / link mới, **không sửa** bảng cũ |
| **Kiểm toán**: "con số này đến từ đâu, kho biết lúc nào" | Thường không trả lời được | Mọi dòng có `RECORD_SOURCE` và `LOAD_DATETIME`, không bao giờ sửa/xoá |
| Nạp **song song**, khối lượng lớn | Dimension phải xong trước fact (cần surrogate key) | Hash key tính được độc lập → hub, link, satellite nạp song song |
| Quy tắc nghiệp vụ **hay đổi** ("doanh thu" được định nghĩa lại) | Dữ liệu đã bị biến đổi khi nạp, khó tính lại | Raw vault giữ dữ liệu **thô**; quy tắc nằm ở tầng trên, đổi là tính lại được |

Data Vault do Dan Linstedt phát triển. **Data Vault 2.0** (khoảng 2013) bổ sung hash key thay cho sequence key, quy trình (methodology) và kiến trúc tham chiếu.

## Kiến trúc tham chiếu

```
Nguồn ──▶ Staging ──▶ RAW VAULT ──────────▶ BUSINESS VAULT ─────────▶ INFORMATION MART ──▶ BI
          (hard rules)  hub · link · satellite   computed satellite,        star schema, bảng phẳng
          hash key,     dữ liệu THÔ, chỉ thêm     PIT, bridge                (Kimball!)
          load date                               (soft rules)
```

| Tầng | Làm gì | Quy tắc |
|---|---|---|
| Staging | Đổi tên, ép kiểu, tính hash key, gắn nguồn và thời điểm nạp | Chỉ **hard rules**: kỹ thuật, không thay đổi ý nghĩa dữ liệu |
| Raw vault | Lưu toàn bộ dữ liệu nguồn theo 3 loại bảng | **Insert-only**, không sửa, không xoá, không lọc "dữ liệu xấu" |
| Business vault | Áp quy tắc nghiệp vụ, bảng hỗ trợ truy vấn | **Soft rules**: hợp nhất khách, tính hạng, định nghĩa doanh thu |
| Information mart | Dữ liệu cho người dùng | Thường là **star schema của Kimball** |

**Hard rule** vs **soft rule**:

| Hard rule (trước raw vault) | Soft rule (business vault trở lên) |
|---|---|
| Ép kiểu, đổi múi giờ, cắt khoảng trắng, chuẩn hoá chữ hoa cho business key | "Đơn trả hàng không tính doanh thu" |
| Không đổi ý nghĩa, không bỏ dòng | Đổi ý nghĩa, có thể đổi theo thời gian |

Tầng staging của lab (dựng sẵn) chỉ làm hard rule. Đó là lý do stage của vault đọc được từ nó.

## Ba loại bảng lõi

```
         ┌──────────────┐                                  ┌──────────────┐
         │ hub_customer │◀──── link_order_customer ───────▶│  hub_order   │
         │ customer_code│      (quan hệ, nhiều-nhiều)      │ order_number │
         └──────┬───────┘                                  └──────┬───────┘
                │                                                 │
   sat_customer_crm_status                                sat_order_shop
   (city, loyalty_tier theo thời gian)                    (trạng thái đơn theo thời gian)
```

| Loại | Chứa | Không chứa | Ví dụ |
|---|---|---|---|
| **Hub** | Danh sách **business key** duy nhất của một khái niệm kinh doanh | Thuộc tính, quan hệ | `hub_customer(CUSTOMER_HK, customer_code, LOAD_DATETIME, RECORD_SOURCE)` |
| **Link** | **Quan hệ** giữa các hub (sự kiện, giao dịch, liên kết) | Thuộc tính mô tả | `link_order_customer(LINK_HK, ORDER_HK, CUSTOMER_HK, ...)` |
| **Satellite** | **Thuộc tính mô tả** của hub hoặc link, theo thời gian | Business key, quan hệ | `sat_customer_crm_status(CUSTOMER_HK, city, loyalty_tier, HASHDIFF, LOAD_DATETIME, ...)` |

Cột kỹ thuật có mặt khắp nơi:

| Cột | Ý nghĩa |
|---|---|
| Hash key (`*_HK`) | Hash của business key (hub) hoặc tổ hợp business key (link). Thay surrogate key |
| `LOAD_DATETIME` (LDTS) | Thời điểm **kho** nhận bản ghi |
| `RECORD_SOURCE` (RSRC) | Bản ghi đến từ hệ thống/bảng nào |
| `HASHDIFF` (satellite) | Hash của toàn bộ payload, để phát hiện thay đổi nhanh |
| `EFFECTIVE_FROM` (tuỳ chọn) | Thời điểm **nghiệp vụ** thay đổi có hiệu lực |

Chi tiết từng loại: [6.2](02-hub-link-satellite.md).

## Nguyên tắc vận hành

1. **Insert-only**: không `update`, không `delete`. Thay đổi = dòng satellite mới. Xoá ở nguồn = ghi nhận bằng satellite trạng thái (status tracking) hoặc effectivity satellite.
2. **All the data, all the time**: nạp mọi thứ nguồn gửi, kể cả dữ liệu "xấu". Lọc là việc của business vault.
3. **Auditability**: từ một con số trên báo cáo lần ngược được về bản ghi nguồn, lúc kho nhận nó.
4. **Mô hình theo khái niệm kinh doanh** (customer, order, product), không theo bảng nguồn.

## Điểm yếu (phải nói được khi phỏng vấn)

| Điểm yếu | Hệ quả |
|---|---|
| **Rất nhiều bảng** | Lab: 22 model Kimball vs 32 model vault cho cùng dữ liệu |
| **Truy vấn khó** | Muốn 1 báo cáo phải join hub + link + nhiều satellite + lọc phiên bản. Bắt buộc có information mart |
| **Thêm một tầng** | Tốn thời gian xây dựng, compute, lưu trữ |
| **Cần kỷ luật & công cụ** | Đặt tên, hash, chuẩn hoá phải nhất quán; gần như không làm tay được → cần automate_dv / datavault4dbt |
| **Không tự động "dựng lại được"** | Phần lịch sử chụp từ nguồn ghi đè chỉ tồn tại nếu vault chạy đều đặn (lab ADR bước 2) |

## Khi nào Data Vault phù hợp

| Phù hợp | Không phù hợp |
|---|---|
| Nhiều hệ thống nguồn (5–10+), hay thêm/bỏ nguồn | 1–3 nguồn ổn định |
| Yêu cầu kiểm toán, truy vết (ngân hàng, bảo hiểm, y tế) | Startup cần dashboard nhanh |
| Nhiều team cùng nạp dữ liệu song song | Team AE 1–3 người |
| Định nghĩa nghiệp vụ hay đổi, cần tính lại | Quy tắc ổn định |

Thực tế phổ biến nhất là **lai**: Data Vault cho tầng tích hợp các thực thể lõi, Kimball cho tầng hiển thị (information mart). Bài viết ADR ở [6.6](06-adr-data-vault-vs-kimball.md).

## Data Vault trong hệ sinh thái dbt

| Package | Ghi chú |
|---|---|
| **automate_dv** (Datavault-UK, tên cũ dbtvault) | Phổ biến nhất, roadmap dùng package này. Hỗ trợ Snowflake, BigQuery, SQL Server, Databricks, Postgres. Lab dùng shim để chạy trên DuckDB |
| **datavault4dbt** (Scalefree) | Package lớn thứ hai, theo sát chuẩn của Scalefree (công ty đồng sáng lập với Dan Linstedt) |

## Câu hỏi tự kiểm tra

1. Data Vault giải quyết những vấn đề gì mà star schema xử lý vất vả?
2. Kể 4 tầng của kiến trúc Data Vault và việc của từng tầng.
3. Hard rule và soft rule khác nhau thế nào? Cho 2 ví dụ mỗi loại.
4. Hub, link, satellite chứa gì và **không** chứa gì?
5. `LOAD_DATETIME` khác `EFFECTIVE_FROM` thế nào?
6. Vì sao nói Data Vault "không thay thế" Kimball?
7. Kể 3 điểm yếu của Data Vault.

## Tài liệu

- Linstedt & Olschimke, *Building a Scalable Data Warehouse with Data Vault 2.0* — chương 1–4
- AutomateDV docs: https://automate-dv.readthedocs.io/en/latest/
- datavault4dbt: https://github.com/ScalefreeCOM/datavault4dbt
- Lab: [04-data-vault-raw-vault.md](../../bai-tap-kimball-data-vault/bai-tap/04-data-vault-raw-vault.md)
