# Lab GĐ2: Kimball nâng cao + Data Vault 2.0 (dbt + DuckDB)

Bộ bài tập cho **tuần 4** (Kimball chuyên sâu) và **tuần 6** (Data Vault 2.0 với `automate_dv`) của GĐ2. Chạy hoàn toàn trên máy bằng DuckDB, giống lab GĐ1.

Bạn làm việc cho **Mây Shop**: một shop bán thời trang, đồ điện tử và đồ gia dụng qua website, app và 2 cửa hàng. Dữ liệu đến từ **5 hệ thống** (CRM, website, máy bán hàng tại cửa hàng, kho vận, ERP), mỗi hệ thống nạp dữ liệu theo một kiểu khác nhau. Một script giả lập cho thời gian trôi qua **7 ngày**, mỗi ngày gài một tình huống mà mô hình dữ liệu phải chịu được.

1. **Tuần 4 (K1–K14):** dựng kho dữ liệu kiểu Kimball. Gồm bus matrix, dimension dùng chung, 4 loại fact (transaction, accumulating snapshot, periodic snapshot, factless), 2 kiểu bridge table, dữ liệu đến muộn và drill-across.
2. **Tuần 6 (V1–V8):** dựng lại **cùng dữ liệu đó** bằng Data Vault 2.0 (hub, link, satellite, PIT), rồi dựng star schema từ vault. Kết quả phải **giống hệt** bản Kimball. Sau đó viết ADR so sánh hai cách.

Có **script tự chấm** tính đáp án chuẩn trực tiếp từ dữ liệu nguồn.

## Cấu trúc

```
bai-tap-kimball-data-vault/
├── README.md
├── pyproject.toml            ← uv project: dbt-core 1.x + dbt-duckdb 1.x
├── bai-tap/                  ← ĐỀ BÀI
│   ├── 00-setup.md           ← cài đặt, 5 hệ thống nguồn, dòng thời gian 7 ngày, quy trình
│   ├── 01-kimball-thiet-ke-va-dimension.md   ← K1–K4
│   ├── 02-kimball-fact.md                    ← K5–K9
│   ├── 03-kimball-nang-cao.md                ← K10–K14
│   ├── 04-data-vault-raw-vault.md            ← V1–V6
│   ├── 05-data-vault-business-vault-va-mart.md ← V7–V8 + ADR
│   └── 06-thu-thach-cuoi.md                  ← tổng hợp, thử thách mở, câu hỏi phỏng vấn
├── lab/                      ← dbt project BẠN LÀM BÀI Ở ĐÂY (đã có sẵn staging)
│   ├── models/staging/       ← 14 model staging dựng sẵn (bạn đã luyện tầng này ở GĐ1)
│   ├── macros/               ← business_date(), shim automate_dv cho DuckDB
│   └── scripts/
│       ├── simulate.py       ← cho thời gian trôi: reset / next / status / goto
│       ├── check.py          ← tự chấm 21 bài
│       └── replay.sh         ← làm lại từ ngày 0 tới ngày N, build mỗi ngày, rồi chấm
└── dap-an/                   ← ĐÁP ÁN đã kiểm chứng: 21/21 PASS ở mọi ngày từ 2 tới 6. Đừng mở trước!
```

## Bắt đầu nhanh

```bash
cd ~/Desktop/target_ae/bai-tap-kimball-data-vault
uv sync && source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.

dbt deps                           # dbt_utils + automate_dv
python scripts/simulate.py reset   # tạo lab.duckdb, nạp ngày 0
dbt build                          # 14 view staging + 28 test, tất cả xanh
python scripts/check.py            # 21 bài, lúc này tất cả SKIP
```

Rồi mở [bai-tap/00-setup.md](bai-tap/00-setup.md).

## Danh sách bài

⭐ cơ bản · ⭐⭐ trung bình · ⭐⭐⭐ khá · ⭐⭐⭐⭐ nâng cao

### Tuần 4: Kimball (K)

| ID | Cấp | Chủ đề | Bài học chính |
|---|---|---|---|
| K1 | ⭐ | Khảo sát nguồn, thiết kế 4 bước | Quy trình nghiệp vụ, grain, nháp bus matrix (không chấm) |
| K2 | ⭐⭐ | `dim_date`, `dim_month` | Role-playing, dòng "chưa xảy ra", shrunken dimension conformed |
| K3 | ⭐⭐ | `dim_product` + các dimension nhỏ | SCD Type 1, thành viên `-1` / `-2`, cây danh mục |
| K4 | ⭐⭐⭐ | `dim_customer` SCD2 | Dựng SCD2 từ file full hằng ngày, cột Type 1 trong dim Type 2, khoá ổn định |
| K5 | ⭐⭐⭐ | `fct_sales` + junk dimension | Grain, gộp 2 nguồn, degenerate dimension, phân bổ đầu đơn xuống dòng |
| K6 | ⭐⭐⭐ | Late-arriving dimension | Inferred member: fact tới trước dimension |
| K7 | ⭐⭐⭐ | Late-arriving fact | POS về trễ vẫn nhận đúng phiên bản dimension |
| K8 | ⭐⭐⭐⭐ | Accumulating snapshot | `fct_order_fulfillment`: mốc, độ trễ, sự kiện về sai thứ tự |
| K9 | ⭐⭐⭐ | Periodic snapshot | `fct_inventory_daily`: dày đặc, semi-additive, điều chỉnh lùi ngày |
| K10 | ⭐⭐ | Factless fact | Coverage khuyến mãi, câu hỏi "cái gì KHÔNG xảy ra" |
| K11 | ⭐⭐⭐ | Bridge nhiều giá trị | Đơn – voucher, trọng số, báo cáo weighted vs impact |
| K12 | ⭐⭐⭐⭐ | Bridge phân cấp | Cây danh mục không đều, closure table |
| K13 | ⭐⭐⭐ | Drill-across | Chỉ tiêu (tháng × danh mục) vs thực tế (dòng đơn) |
| K14 | ⭐⭐ | Bus matrix | `bus_matrix.yml` khớp với model thật, được chấm tự động |

### Tuần 6: Data Vault 2.0 (V)

| ID | Cấp | Chủ đề | Bài học chính |
|---|---|---|---|
| V1 | ⭐⭐ | Stage | Hash key, hashdiff, record source, load datetime, zero key |
| V2 | ⭐⭐ | Hub | Gom business key từ nhiều nguồn |
| V3 | ⭐⭐⭐ | Link, non-historized link | Quan hệ, giao dịch bất biến, `automate_dv` chỉ nhận 1 nguồn cho nh_link |
| V4 | ⭐⭐⭐⭐ | Satellite | Tách theo tốc độ đổi, **bẫy stage chứa nhiều lần nạp** |
| V5 | ⭐⭐⭐ | Effectivity satellite | Link nào đang hiệu lực, driving key |
| V6 | ⭐⭐⭐ | Multi-active satellite | Nhiều số điện thoại cùng lúc |
| V7 | ⭐⭐⭐ | PIT | Trạng thái "kho biết gì" tại mỗi lần nạp |
| V8 | ⭐⭐⭐⭐ | Information mart | Star schema từ vault = bản Kimball, từng dòng một |

## Lộ trình gợi ý (buổi chiều 4h)

| Tuần | Buổi | Làm gì |
|---|---|---|
| 4 | 1 | Setup, K1 (thiết kế trên giấy), K2, K3 |
| 4 | 2 | K4, K5 |
| 4 | 3 | `next` tới ngày 2–3: K6, K7. Sau đó K8 |
| 4 | 4 | K9, K10, K11 |
| 4 | 5 | K12, K13, K14 → `replay.sh` xanh 14/14 phần K |
| 6 | 1 | V1, V2, V3 |
| 6 | 2 | V4 (gặp bẫy, sửa, replay), V5, V6 |
| 6 | 3 | V7, V8 → `replay.sh` xanh 21/21 |
| 6 | 4 | Đo đạc 2 cách, viết ADR (đề ở file 05) |

Mỗi buổi chiều còn lại của tuần 4 và tuần 6: áp dụng sang `adventure_works` theo checklist trong lý thuyết [GĐ2](../GD2-ly-thuyet/README.md).

## Quy tắc dùng đáp án

1. Tự làm, chạy `check.py`, đọc thông báo lỗi, sửa. Thông báo được viết để gợi hướng.
2. Bí quá 30 phút thì mở phần **Gợi ý** (thu gọn) trong đề.
3. Chỉ mở `dap-an/` sau khi đã PASS (để so cách làm), hoặc khi đã thử hết gợi ý.

Chạy thử toàn bộ đáp án: copy `lab/` sang chỗ khác, chép đè `dap-an/*` lên, rồi `./scripts/replay.sh`.
