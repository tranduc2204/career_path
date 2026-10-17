# Lab: từ staging tới vận hành sự cố (dbt + DuckDB)

Bộ bài tập **từ cơ bản đến nâng cao**, chạy hoàn toàn trên máy bằng DuckDB:

1. **Xây dựng (ngày 0–5):** tự dựng staging từ dữ liệu thô → mart đầu tiên → Jinja → incremental → snapshot/SCD2.
2. **Vận hành (ngày 6–11):** hệ thống đã ổn định thì nguồn bắt đầu gây sự cố giống ngoài thực tế (dữ liệu trùng, đổi tên cột, trạng thái mới, sửa ngầm số liệu cũ, sự kiện lỗi, soft delete). Bạn điều tra, sửa, viết runbook và postmortem.

Dữ liệu nguồn **thay đổi theo từng "ngày"** do một script giả lập. Có **script tự chấm** so kết quả của bạn với dữ liệu nguồn.

## Cấu trúc

```
bai-tap-incremental-scd2-jinja/
├── README.md
├── pyproject.toml            ← uv project: dbt-core 1.x + dbt-duckdb 1.x
├── bai-tap/                  ← ĐỀ BÀI
│   ├── 00-setup.md           ← cài đặt, dữ liệu, dòng thời gian 12 ngày, quy trình
│   ├── 01-co-ban.md          ← B1–B8: raw → staging → test → mart đầu tiên
│   ├── 02-jinja.md           ← J1–J10
│   ├── 03-incremental.md     ← I1–I9
│   ├── 04-snapshot-scd2.md   ← S1–S8
│   ├── 05-su-co-thuc-te.md   ← P1–P6: sự cố production ngày 6–11
│   └── 06-thu-thach-cuoi.md  ← tổng hợp, thử thách mở, câu hỏi phỏng vấn
├── lab/                      ← dbt project BẠN LÀM BÀI Ở ĐÂY (trống, tự xây từ staging)
│   └── scripts/
│       ├── simulate.py       ← cho thời gian trôi: reset / next / status [--reveal] / goto
│       ├── check.py          ← tự chấm 38 bài
│       ├── replay.sh         ← làm lại từ ngày 0 tới ngày N, build + runbook mỗi ngày, rồi chấm
│       └── hooks/            ← (bạn tạo) runbook after_day_<N>.sh cho giai đoạn sự cố
└── dap-an/                   ← ĐÁP ÁN, đã kiểm chứng: 38/38 PASS sau replay tới ngày 11. Đừng mở trước!
```

## Bắt đầu nhanh

```bash
cd ~/Desktop/target_ae/bai-tap-incremental-scd2-jinja
uv sync && source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.

dbt deps
python scripts/simulate.py reset
python scripts/check.py            # 38 bài, lúc này tất cả SKIP
```

Rồi mở [bai-tap/00-setup.md](bai-tap/00-setup.md) và [bai-tap/01-co-ban.md](bai-tap/01-co-ban.md).

## Danh sách bài

⭐ cơ bản · ⭐⭐ trung bình · ⭐⭐⭐ khá · ⭐⭐⭐⭐ nâng cao

### Giai đoạn xây dựng (ngày 0–5)

| ID | Cấp | Chủ đề | Bài học chính |
|---|---|---|---|
| B1 | ⭐ | Khám phá dữ liệu nguồn | Xem dữ liệu trước khi viết model (không chấm) |
| B2 | ⭐ | Khai báo sources | `source()`, nơi duy nhất nhắc tới bảng thô |
| B3 | ⭐ | `stg_orders` | Rename, đổi đơn vị, mẫu CTE, view |
| B4 | ⭐ | Staging còn lại | Làm sạch chuỗi, staging là "hợp đồng" |
| B5 | ⭐⭐ | Test cơ bản | unique/not_null/accepted_values/relationships, test đỏ lần đầu, severity |
| B6 | ⭐⭐ | `dim_products`, `fct_order_lines` | Grain, bẫy fan-out khi join |
| B7 | ⭐⭐ | `customer_lifetime` + `int_orders` | Quy tắc nghiệp vụ đặt một chỗ |
| B8 | ⭐ | View vs table, chọn model | `+`, `dbt build` vs `run` vs `test` (không chấm) |
| J1–J10 | ⭐→⭐⭐⭐⭐ | Jinja | Macro, vòng lặp, `run_query`, generic test, `generate_schema_name`, `graph`, `dispatch` |
| I1–I9 | ⭐⭐→⭐⭐⭐⭐ | Incremental | append/merge/delete+insert, đến muộn, lookback, `on_schema_change`, microbatch, đối soát |
| S1–S8 | ⭐⭐→⭐⭐⭐⭐ | Snapshot & SCD2 | timestamp/check, bẫy `updated_at`, hard delete, point-in-time, SCD2 tự viết, CDC |

### Giai đoạn vận hành (ngày 6–11)

| ID | Ngày | Cấp | Triệu chứng ban đầu |
|---|---|---|---|
| P1 | 6 | ⭐⭐ | Test staging đỏ, dashboard đứng yên |
| P2 | 7 | ⭐⭐⭐ | Job sáng lỗi, 20 model bị SKIP |
| P3 | 8 | ⭐⭐⭐ | Kế toán báo doanh thu sai + yêu cầu quy tắc mới |
| P4 | 9 | ⭐⭐⭐⭐ | Mọi thứ xanh (trừ test đối soát nếu có), nhưng số lệch sổ sách |
| P5 | 10 | ⭐⭐⭐⭐ | Marketing báo thiếu event so với Mixpanel |
| P6 | 11 | ⭐⭐⭐⭐ | Không có gì đỏ, QA báo đơn test vẫn tính doanh thu |

Nguyên nhân từng sự cố bị giấu — đó là phần phải tự điều tra.

## Lộ trình gợi ý (buổi chiều 4h)

| Buổi | Làm gì |
|---|---|
| 1 | Setup, B1–B8 |
| 2 | J1–J6 |
| 3 | I1, I2, I3, I5 ở ngày 0 → `next` tới ngày 2 → gặp lỗi → I4, sửa I5 |
| 4 | J7 + I6, I7 (tới ngày 4), I8, I9, J8, J9 |
| 5 | S1–S4 (dùng `replay.sh`), S5, S6 |
| 6 | S7, J10 + S8 → `replay.sh 5` xanh toàn bộ = hệ thống "ổn định" |
| 7–8 | P1–P6, mỗi sự cố viết postmortem; cuối cùng `replay.sh 11` xanh 38/38 |

## Quy tắc dùng đáp án

1. Tự làm, chạy `check.py`, đọc thông báo lỗi, sửa. Thông báo được viết để gợi hướng.
2. Bí quá 30 phút thì mở phần **Gợi ý** (thu gọn) trong đề.
3. Chỉ mở `dap-an/` sau khi đã PASS (để so cách làm), hoặc khi đã thử hết gợi ý.

Chạy thử toàn bộ đáp án: copy `lab/` sang chỗ khác, chép đè `dap-an/*` lên, rồi `./scripts/replay.sh 11`. Build ở ngày 9 và 10 sẽ báo lỗi **trước khi** runbook chạy — đó là các test đối soát đang bắt sự cố, runbook backfill ngay sau đó làm lành dữ liệu.
