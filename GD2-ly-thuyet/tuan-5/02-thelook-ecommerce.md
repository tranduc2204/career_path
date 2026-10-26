# 5.2 Dataset `thelook_ecommerce` và thiết kế project 2

## Giới thiệu

`bigquery-public-data.thelook_ecommerce` là dữ liệu **giả lập** của một shop thời trang online (do team Looker tạo), có sẵn trên BigQuery, **miễn phí lưu trữ** (bạn chỉ trả tiền byte quét khi query). Nhiều nguồn ghi nhận dataset được **cập nhật liên tục** (dữ liệu mới mỗi ngày), nên số liệu bạn thấy hôm nay khác hôm qua — tốt cho việc luyện incremental, nhưng phải nhớ khi viết test cố định con số.

Vị trí: dataset nằm ở **multi-region `US`**. BigQuery **không cho join dữ liệu khác location** → mọi dataset của project bạn (dev, staging, prod) phải tạo ở `US`.

## Các bảng

Đây là cấu trúc phổ biến được nhiều tài liệu mô tả. **Ngày đầu tiên, kiểm chứng lại bằng query bên dưới** trước khi viết `sources.yml` (dataset có thể thêm cột).

| Bảng | Grain | Cột chính |
|---|---|---|
| `users` | 1 khách | `id`, `first_name`, `last_name`, `email`, `age`, `gender`, `state`, `city`, `country`, `traffic_source`, `created_at` |
| `orders` | 1 đơn | `order_id`, `user_id`, `status`, `gender`, `created_at`, `shipped_at`, `delivered_at`, `returned_at`, `num_of_item` |
| `order_items` | 1 món hàng trong đơn | `id`, `order_id`, `user_id`, `product_id`, `inventory_item_id`, `status`, `created_at`, `shipped_at`, `delivered_at`, `returned_at`, `sale_price` |
| `products` | 1 sản phẩm | `id`, `name`, `brand`, `category`, `department`, `sku`, `retail_price`, `cost`, `distribution_center_id` |
| `inventory_items` | 1 đơn vị hàng trong kho | `id`, `product_id`, `created_at` (nhập kho), `sold_at`, `cost`, các cột `product_*` (bản sao thông tin sản phẩm) |
| `distribution_centers` | 1 trung tâm phân phối | `id`, `name`, `latitude`, `longitude` |
| `events` | 1 sự kiện web | `id`, `user_id` (null nếu chưa đăng nhập), `session_id`, `sequence_number`, `created_at`, `event_type`, `uri`, `traffic_source`, `browser`, `city`, `state` |

Trạng thái đơn / món hàng thường gặp: `Processing`, `Shipped`, `Complete`, `Cancelled`, `Returned` (kiểm chứng bằng `select distinct status`).

Kiểm chứng schema và kích thước (query metadata, rất rẻ):

```sql
-- cột của mọi bảng
select table_name, column_name, data_type
from `bigquery-public-data.thelook_ecommerce.INFORMATION_SCHEMA.COLUMNS`
order by table_name, ordinal_position;

-- số dòng và dung lượng (dùng __TABLES__ của dataset)
select table_id, row_count, round(size_bytes / pow(1024, 2), 1) as size_mb
from `bigquery-public-data.thelook_ecommerce.__TABLES__`
order by size_bytes desc;

-- dữ liệu tới ngày nào? có dòng ở tương lai không?
select max(created_at), current_timestamp() from `bigquery-public-data.thelook_ecommerce.orders`;
```

Ghi kết quả vào README của project (ngày kiểm tra, số dòng, dung lượng). `events` thường là bảng lớn nhất → bảng để luyện partition/cluster ở tuần 7.

## Quan hệ

```
users 1──n orders 1──n order_items n──1 products n──1 distribution_centers
  │                        │
  │                        └──1 inventory_items n──1 products
  └──1──n events (user_id có thể null: khách chưa đăng nhập)
```

## Áp dụng Kimball (tuần 4) cho thelook

Đây là lúc dùng lại toàn bộ tuần 4 trên dữ liệu thật. Bus matrix gợi ý:

| Quy trình | Fact | Loại | Grain | date | customer | product | distribution_center | traffic_source |
|---|---|---|---|---|---|---|---|---|
| Bán hàng | `fct_order_items` | transaction | 1 món hàng trong đơn | X | X | X | X | X |
| Thực hiện đơn | `fct_order_fulfillment` | accumulating snapshot | 1 đơn (hoặc 1 món): tạo → gửi → giao → trả | X (×4 vai) | X | | X | |
| Hành vi web | `fct_events` | transaction (event) | 1 sự kiện | X | X | | | X |
| Phiên truy cập | `fct_sessions` | transaction (tổng hợp từ events) | 1 phiên | X | X | | | X |
| Tồn kho | `fct_inventory_daily` | periodic snapshot | sản phẩm × trung tâm × ngày | X | | X | X | |

Điểm thú vị của thelook:
- `orders` và `order_items` đều có `status` và các mốc thời gian → chọn grain cho accumulating snapshot là **đơn** hay **món hàng**? (một đơn có thể giao một phần, trả một phần)
- `inventory_items` có `created_at` (nhập kho) và `sold_at` → tính tồn kho tại một ngày = đã nhập trước ngày đó và chưa bán (hoặc bán sau ngày đó).
- `events` có `session_id`, `sequence_number` → dựng `fct_sessions` (độ dài phiên, phễu xem → giỏ hàng → mua).
- `users.traffic_source` vs `events.traffic_source` → một conformed dimension `dim_traffic_source`.

## Cấu trúc project gợi ý

```
thelook/                              (repo GitHub riêng: project 2 của portfolio)
├── .github/workflows/                ci.yml, cd.yml, cleanup.yml   (5.4)
├── models/
│   ├── staging/thelook/              _thelook__sources.yml, stg_thelook__*.sql
│   ├── intermediate/
│   └── marts/
│       ├── core/                     dim_date, dim_customer, dim_product, dim_distribution_center
│       ├── sales/                    fct_order_items, fct_order_fulfillment
│       ├── web/                      fct_events, fct_sessions
│       └── inventory/                fct_inventory_daily
├── macros/                           generate_schema_name.sql (5.3), ...
├── docs/adr/                         0002-moi-truong-va-cd.md
├── profiles.yml                      đọc biến môi trường, KHÔNG chứa bí mật (5.3)
└── README.md                         kiến trúc, bus matrix, cách chạy, chi phí
```

Hướng dẫn từng bước dựng project: [bai-tap-bigquery-thelook](../../bai-tap-bigquery-thelook/README.md).

## Chi phí thực tế của project

Dataset thelook nhỏ (vài trăm MB tới vài GB tuỳ thời điểm). Với on-demand (1 TiB miễn phí / tháng), cả tháng phát triển thường nằm trong free tier **nếu**:
- Không `select *` từ `events` nhiều lần không cần thiết.
- Bật `maximum_bytes_billed` trong profile (5.1).
- Staging là `view`: mỗi lần build mart, BigQuery đọc lại nguồn public — chấp nhận được với dữ liệu nhỏ; nếu muốn tiết kiệm, cho staging của `events` thành `table`.

## Lỗi hay gặp

- Tạo dataset ở `asia-southeast1` → *Not found: Dataset ... was not found in location asia-southeast1* khi join với dữ liệu public ở `US`.
- Viết test với con số cố định (đúng 100.000 đơn) → dataset cập nhật, test đỏ.
- Dùng `id` làm tên cột ở mọi bảng mà không đổi tên ở staging → mart đầy `id` mơ hồ.
- Không ghi lại ngày kiểm tra dữ liệu → không giải thích được vì sao số liệu README khác số liệu dashboard.

## Câu hỏi tự kiểm tra

1. Vì sao mọi dataset của project phải ở location `US`?
2. Grain của `orders` và `order_items` khác nhau thế nào? Doanh thu nên lấy từ bảng nào?
3. Accumulating snapshot nên ở grain đơn hay món hàng? Lập luận.
4. Tính tồn kho tại một ngày từ `inventory_items` thế nào?
5. Dataset cập nhật liên tục ảnh hưởng gì tới test và tới incremental?

## Tài liệu

- Dataset trên Google Cloud Marketplace: tìm "theLook eCommerce" trong BigQuery console → Add data → Public datasets
- BigQuery — Dataset locations: https://docs.cloud.google.com/bigquery/docs/locations
- Tuần 4: [4.2 bus matrix](../tuan-4/02-bus-matrix-va-conformed-dimension.md), [4.6 snapshot](../tuan-4/06-accumulating-va-periodic-snapshot.md)
