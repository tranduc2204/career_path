# Lab GĐ3 tuần 11: Viết pytest cho pipeline dlt (chấm bằng mutation testing)

Mây Shop kéo đơn hàng từ API của nhà cung cấp bằng **dlt** vào DuckDB. Pipeline đã chạy được (`pipeline/mayshop_api.py`), nhưng **chưa có test nào**. Tuần trước có người sửa một dòng và đơn hàng bị nhân đôi suốt 3 ngày mà không ai biết.

Việc của bạn: viết bộ test `pytest` sao cho **mọi lỗi hay gặp đều bị bắt**. Bộ chấm không đếm số test, nó dùng **mutation testing**: tạo 8 bản pipeline, mỗi bản cài đúng một lỗi thật ("mutant"), rồi chạy test của bạn. Test của bạn phải **xanh trên bản gốc** và **đỏ trên từng mutant**.

Lý thuyết: [GD3-ly-thuyet/tuan-11/05-pytest-cho-pipeline-dlt.md](../GD3-ly-thuyet/tuan-11/05-pytest-cho-pipeline-dlt.md). Đã kiểm chứng 07/11/2026 với dlt 1.32.0, DuckDB 1.5.6, pytest 9.2.0: bộ test trong `dap-an/` giết 8/8 mutant (~40 giây).

## Cấu trúc

```
bai-tap-dlt-pytest/
├── fake_api/server.py       ← API giả lập (đừng sửa): phân trang, updated_since, 429, dữ liệu "ngày 0" và "ngày 1"
├── pipeline/mayshop_api.py  ← pipeline dlt "production": ĐỌC KỸ, đây là thứ bạn test
├── tests/
│   ├── conftest.py          ← fixture có sẵn: api (server cổng ngẫu nhiên), workdir (thư mục tạm)
│   └── test_pipeline.py     ← BẠN VIẾT Ở ĐÂY
├── scripts/mutate.py        ← bộ chấm mutation testing
└── dap-an/tests/            ← đáp án. Đừng mở trước!
```

## Bắt đầu

```bash
cd ~/Desktop/target_ae/bai-tap-dlt-pytest
uv sync && source .venv/bin/activate

python -m pipeline.mayshop_api /tmp/thu-dlt     # chạy pipeline 1 lần vào /tmp/thu-dlt/mayshop.duckdb
pytest -q                                        # test của bạn
python scripts/mutate.py                         # chấm: bao nhiêu mutant bị giết?
python scripts/mutate.py P3 P5                   # chấm vài mutant
```

## API giả lập

| | |
|---|---|
| `GET /v1/orders?updated_since=<ISO, có múi giờ>&page=<n>&page_size=<k>` | Đơn có `updated_at >= updated_since`, sắp theo `(updated_at, order_id)`. Trả `{"data": [...], "page": n, "next_page": n+1 hoặc null}` |
| `GET /v1/customers?page=&page_size=` | 40 khách |
| Dữ liệu | **Ngày 0**: 120 đơn `placed`. **Ngày 1** (`api.set_day(1)`): 6 đơn cũ chuyển `shipped` (updated_at mới) + 8 đơn mới |
| Định dạng | `updated_at` kiểu `2026-12-01T08:07:00+07:00`. `amount` là **chuỗi** `"1.290.000"`. Mỗi đơn có mảng `items` |
| `api.flaky = True` | Lần gọi đầu tiên của mỗi endpoint trả **429** (`Retry-After: 0`) |
| `api.requests` | Danh sách `(path, query_dict)` mọi request đã nhận: dùng để kiểm tra pipeline **hỏi API cái gì** |

Fixture `api` tạo một server mới cho **mỗi test** (ngày 0, không flaky). Fixture `workdir` là thư mục tạm riêng, chứa `mayshop.duckdb` và state của dlt, nên các test không ảnh hưởng nhau. `run(api.base_url, workdir)` chạy pipeline một lần và trả `(pipeline, load_info)`.

## Yêu cầu: 8 hành vi phải được bảo vệ

Bạn không biết mutant cài lỗi gì cụ thể (đừng đọc `scripts/mutate.py` trước khi viết xong lượt đầu). Bạn chỉ biết **hành vi đúng** của pipeline:

| # | Hành vi | Gợi ý cách kiểm |
|---|---|---|
| P1 | Lấy **đủ mọi trang** của API | Ngày 0 có 120 đơn, `page_size=50` → 3 trang |
| P2 | Lần chạy thứ 2 **chỉ hỏi API phần thay đổi** (gửi `updated_since` = mốc lần trước) | `api.requests`. Đếm dòng trong DB không đủ: dlt tự lọc cursor ở phía client |
| P3 | Đơn đổi trạng thái được **cập nhật**, không thêm dòng mới | Chạy ngày 0 → `set_day(1)` → chạy lại: 128 đơn, distinct 128, đơn 5004 là `shipped` |
| P4 | Gộp theo **đúng khoá** `order_id` | (cùng test với P3 thường giết được cả hai) |
| P5 | `updated_at` giữ **đúng múi giờ** | `2026-12-01T08:07:00+07:00` phải bằng `01:07 UTC` |
| P6 | `amount` `"1.290.000"` → **1290000** | Unit test cho `parse_vnd` + kiểm tổng tiền sau khi nạp |
| P7 | **Tự retry** khi API trả 429 | `api.flaky = True` rồi chạy: vẫn đủ 120 đơn |
| P8 | `items` vào **bảng con** `orders__items`, nối được về đơn cha | Đếm dòng con, join `_dlt_parent_id = _dlt_id` |

Chuẩn viết test (bộ chấm không kiểm, nhưng reviewer sẽ kiểm):

- Tên test là một câu mô tả hành vi: `test_second_run_merges_updates_without_duplicates`
- Mỗi test kiểm **một** hành vi; dùng `@pytest.mark.parametrize` cho nhiều đầu vào của cùng hành vi
- Không `time.sleep`, không phụ thuộc thứ tự chạy, không dùng mạng thật
- Tách **unit test** (hàm thuần như `parse_vnd`, không cần API) và **integration test** (API giả → DuckDB thật)

## Mốc hoàn thành

```
Điểm: 8/8 mutant bị giết
```

Sau đó áp dụng sang pipeline dlt thật của bạn (GĐ1 hoặc project portfolio): ít nhất 1 unit test + 3 integration test với fixture API giả, chạy trong GitHub Actions.

## Câu hỏi tự kiểm tra

1. Vì sao test "chạy pipeline xong, bảng có > 0 dòng" gần như vô dụng? Mutant nào sống sót qua test đó?
2. Mutant P2 sống sót qua test đếm dòng. Vì sao? Ngoài đời, lỗi đó gây hại gì (gợi ý: chi phí API, rate limit, thời gian chạy)?
3. Mocking `requests` bằng `unittest.mock` so với chạy một HTTP server giả thật: mỗi cách bắt được loại lỗi nào?
4. Mutation testing đo cái gì mà code coverage không đo được?
