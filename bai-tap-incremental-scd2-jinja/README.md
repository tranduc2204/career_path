# Lab: Incremental · Snapshot · SCD2 · Jinja (dbt + DuckDB)

Bộ bài tập từ **trung bình đến nâng cao**, chạy hoàn toàn trên máy bằng DuckDB, không cần cloud.

Điểm khác với bài tập thông thường: dữ liệu nguồn **thay đổi theo từng "ngày"**. Một script giả lập lần lượt tạo ra: đơn đổi trạng thái, đơn đến muộn, sự kiện bị gửi trùng, khách đổi địa chỉ, khách bị xoá, nguồn thêm cột mới... Bạn build model, cho thời gian trôi, rồi xem model có còn đúng không. Có **script tự chấm** so kết quả của bạn với dữ liệu nguồn.

## Cấu trúc

```
bai-tap-incremental-scd2-jinja/
├── README.md                ← file này
├── requirements.txt
├── .venv/                   ← môi trường Python đã cài sẵn dbt-core 1.12 + dbt-duckdb 1.11
├── bai-tap/                 ← ĐỀ BÀI
│   ├── 00-setup.md          ← cài đặt, mô hình dữ liệu, kịch bản 6 ngày, quy trình làm bài
│   ├── 01-jinja.md          ← J1–J10
│   ├── 02-incremental.md    ← I1–I9
│   ├── 03-snapshot-scd2.md  ← S1–S8
│   └── 04-thu-thach-cuoi.md ← tổng hợp, thử thách mở, câu hỏi phỏng vấn
├── lab/                     ← dbt project BẠN LÀM BÀI Ở ĐÂY
│   ├── models/staging/      ← cho sẵn
│   ├── models/marts/        ← trống, bạn viết
│   ├── macros/ snapshots/ tests/
│   └── scripts/
│       ├── simulate.py      ← cho thời gian trôi: reset / next / status / goto
│       ├── check.py         ← tự chấm
│       └── replay.sh        ← làm lại từ ngày 0 tới ngày N, build mỗi ngày, rồi chấm
└── dap-an/                  ← ĐÁP ÁN (đã kiểm chứng: 26/26 pass ở cả 6 ngày). Đừng mở trước khi tự làm!
```

## Bắt đầu nhanh

```bash
cd ~/Desktop/target_ae/bai-tap-incremental-scd2-jinja
source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.          # profiles.yml nằm ngay trong lab/

dbt deps                           # cài dbt_utils
python scripts/simulate.py reset   # tạo lab.duckdb, nạp dữ liệu ngày 0
dbt build                          # build staging cho sẵn
python scripts/check.py            # 26 bài, lúc này tất cả SKIP
```

Chi tiết đầy đủ: [bai-tap/00-setup.md](bai-tap/00-setup.md).

## Danh sách bài

⭐⭐ trung bình · ⭐⭐⭐ khá · ⭐⭐⭐⭐ nâng cao

| ID | Cấp | Chủ đề | Bài học chính | Lỗi lộ ra ở ngày |
|---|---|---|---|---|
| J1 | ⭐⭐ | Macro `cents_to_dollars` | Macro có tham số mặc định | – |
| J2 | ⭐⭐ | Macro `clean_string` | Ghép chuỗi trong Jinja, whitespace control | – |
| J3 | ⭐⭐ | Pivot bằng `for` + `var` | `loop.last`, sinh cột bằng vòng lặp | – |
| J4 | ⭐⭐⭐ | Pivot động bằng `run_query` | `execute`, `depends_on`, schema thay đổi theo dữ liệu | 4 |
| J5 | ⭐⭐⭐ | Custom generic test | Test có tham số, `arguments:` | – |
| J6 | ⭐⭐⭐ | `generate_schema_name` | Tách schema dev/prod | – |
| J7 | ⭐⭐⭐ | Macro `get_incremental_filter` | `is_incremental()` trong macro, `dbt.dateadd` | 3 |
| J8 | ⭐⭐⭐⭐ | Audit bằng `graph` | Đọc metadata project, `run-operation`, raise lỗi | – |
| J9 | ⭐⭐⭐⭐ | `adapter.dispatch` | Viết macro chạy được nhiều warehouse | – |
| J10 | ⭐⭐⭐⭐ | Macro `scd2_from_changelog` | Macro sinh cả một model | – |
| I1 | ⭐⭐ | `append` | Append không chống trùng | 2 |
| I2 | ⭐⭐ | Chống trùng sự kiện | `unique_key` + dedupe trong batch | 2 |
| I3/I4 | ⭐⭐/⭐⭐⭐ | `merge` + đơn đến muộn | Watermark sai cột → mất dữ liệu vĩnh viễn | 2, 5 |
| I5 | ⭐⭐⭐ | `delete+insert` theo ngày | Phải tính lại **cả ngày** bị ảnh hưởng | 2, 4, 5 |
| I6 | ⭐⭐⭐ | Lookback theo event time | Chọn độ dài lookback | 3 |
| I7 | ⭐⭐⭐ | `on_schema_change` | Nguồn thêm cột, introspection bằng Jinja | 4 |
| I8 | ⭐⭐⭐⭐ | `microbatch` | `event_time`, backfill theo khoảng ngày | – |
| I9 | ⭐⭐⭐⭐ | Bảo vệ & đối soát | `full_refresh=false`, test incremental = full refresh, backfill bằng vars | – |
| S1 | ⭐⭐ | Snapshot `timestamp` | SCD2 cơ bản | 1, 4 |
| S2 | ⭐⭐ | Snapshot `check` | Nguồn không có `updated_at` | 1, 3, 5 |
| S3 | ⭐⭐⭐ | Bẫy `updated_at` | Khi nào `timestamp` bỏ sót thay đổi | 3 |
| S4 | ⭐⭐⭐ | Hard deletes | `invalidate` vs `new_record` | 3 |
| S5 | ⭐⭐⭐ | `dim_customers` SCD2 | Surrogate key, unknown member, test khoảng hiệu lực | 3 |
| S6 | ⭐⭐⭐⭐ | Point-in-time join | Thuộc tính tại thời điểm đặt đơn, late-arriving dimension | 1, 2, 3 |
| S7 | ⭐⭐⭐⭐ | SCD2 tự viết bằng incremental | Hiểu snapshot làm gì bên trong | 3 |
| S8 | ⭐⭐⭐⭐ | SCD2 từ CDC log | Dựng lại lịch sử bất cứ lúc nào | – |

## Lộ trình gợi ý (5 buổi chiều × 4h)

| Buổi | Làm gì |
|---|---|
| 1 | Setup, J1–J6 (ở ngày 0) |
| 2 | I1, I2, I3, I5 ở ngày 0 → `next` tới ngày 2 → gặp lỗi → làm I4, sửa I5 |
| 3 | J7 + I6, I7 (tới ngày 4), I8, I9, J8, J9 |
| 4 | S1–S4 (dùng `replay.sh`, vì snapshot phải chạy từ ngày 0), S5, S6 |
| 5 | S7, J10 + S8, thử thách cuối |

## Quy tắc dùng đáp án

1. Tự làm, chạy `check.py`, đọc thông báo lỗi, sửa. Thông báo lỗi được viết để gợi hướng.
2. Bí quá 30 phút thì mở phần **Gợi ý** trong đề (dạng thu gọn).
3. Chỉ mở `dap-an/` sau khi đã PASS, để so cách làm. Hoặc khi đã thử hết gợi ý.

Muốn chạy thử toàn bộ đáp án: copy `lab/` sang chỗ khác, chép đè `dap-an/*` lên, rồi chạy `./scripts/replay.sh`.
