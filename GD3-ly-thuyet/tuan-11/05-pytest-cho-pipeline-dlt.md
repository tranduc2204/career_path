# 11.5 Viết pytest cho pipeline dlt

> Lab: [bai-tap-dlt-pytest](../../bai-tap-dlt-pytest/README.md) (dlt 1.32 + DuckDB + pytest 9, chấm bằng mutation testing 8 mutant).

## Vì sao AE cần test Python

dbt test kiểm **dữ liệu sau khi đã vào kho**. Lỗi ở tầng ingest (phân trang, cursor, khoá merge, múi giờ, parse số) làm dữ liệu sai **trước khi** dbt nhìn thấy, và nhiều lỗi trông "hợp lệ" với mọi test dbt (đơn trùng có khoá khác nhau, giờ lệch 7 tiếng). Ở mức Mid, roadmap yêu cầu biết *testing frameworks* cho Python: pytest là chuẩn.

## Kim tự tháp test cho pipeline

```
          ▲  ít, chậm, đắt
         ╱ ╲   end-to-end: API thật (sandbox) → warehouse thật, chạy theo lịch / trước release
        ╱───╲
       ╱     ╲  integration: API GIẢ (HTTP server cục bộ) → DuckDB thật, chạy mỗi PR  ← trọng tâm lab
      ╱───────╲
     ╱         ╲ unit: hàm thuần (parse_vnd, chuẩn hoá, ánh xạ trạng thái), mili-giây
    ╱───────────╲  nhiều, nhanh, rẻ
```

- **Unit**: `parse_vnd("1.290.000") == 1290000`. Không cần mạng, không cần DB. Dùng `@pytest.mark.parametrize` cho nhiều trường hợp biên.
- **Integration**: chạy **pipeline thật** (dlt thật, DuckDB thật) với **nguồn giả** điều khiển được: dữ liệu biết trước, có thể đổi "ngày", có thể bật lỗi 429. Đây là nơi bắt phần lớn lỗi thật.
- **End-to-end**: ít, chỉ để chắc cấu hình thật (credential, mạng) hoạt động.

## pytest cần nắm

```python
import pytest

@pytest.fixture
def api():                       # fixture: chuẩn bị + dọn dẹp, mỗi test một bản mới (scope="function")
    server = FakeApi().start()
    yield server                 # phần sau yield = teardown
    server.stop()

@pytest.fixture
def workdir(tmp_path):           # tmp_path: fixture có sẵn, thư mục tạm riêng mỗi test
    return tmp_path

@pytest.mark.parametrize("raw, expected", [("1.290.000", 1290000), ("0", 0)])
def test_parse_vnd_reads_dot_as_thousands_separator(raw, expected):
    assert parse_vnd(raw) == expected

def test_second_run_merges_updates_without_duplicates(api, workdir):
    run(api.base_url, workdir)
    api.set_day(1)
    run(api.base_url, workdir)
    assert q(workdir, "select count(*), count(distinct order_id) from raw_api.orders") == [(128, 128)]
```

| Công cụ | Dùng khi |
|---|---|
| `conftest.py` | Fixture dùng chung cho cả thư mục test |
| `scope="session"` / `"module"` | Fixture đắt (khởi động container) dùng chung. Cẩn thận: test phụ thuộc nhau |
| `tmp_path`, `monkeypatch` (đặt biến môi trường), `caplog` (kiểm log) | Có sẵn |
| `pytest.raises(HTTPError)` | Kiểm hành vi lỗi |
| `-k tên`, `-x`, `-q`, `--lf` (chạy lại test lỗi lần trước) | Chạy nhanh khi đang sửa |
| `pyproject.toml` → `[tool.pytest.ini_options]` | `testpaths`, `pythonpath = ["."]`, `filterwarnings` |

## Nguồn giả: mock hay server thật?

| | `unittest.mock` / `responses` (giả lập thư viện requests) | HTTP server cục bộ (lab) |
|---|---|---|
| Tốc độ | Rất nhanh | Nhanh (vài ms/request) |
| Bắt lỗi đổi thư viện HTTP (P7: `requests` thường thay `dlt.sources.helpers.requests`) | ❌ mock có thể vẫn "chạy" | ✅ 429 thật, không retry là lỗi thật |
| Kiểm tham số gửi đi | Qua mock assertions | Ghi `api.requests` |
| Độ giống thật | Thấp hơn | Cao hơn (header, mã lỗi, phân trang) |

Quy tắc: mock ở **ranh giới hẹp** (một hàm gọi API), dùng server giả cho **hành vi giao thức** (phân trang, retry, cursor).

## Những gì phải test ở một pipeline incremental

Đây cũng là 8 mutant của lab:

1. **Đủ trang** (pagination dừng đúng lúc).
2. **Cursor**: lần 2 gửi `updated_since` = giá trị lớn nhất lần 1. Kiểm **request gửi đi**, vì dlt `incremental` còn lọc lại ở client, đếm dòng trong DB không đủ để phát hiện.
3. **Merge**: bản ghi cập nhật thay bản cũ, không nhân đôi (`write_disposition="merge"`).
4. **Khoá merge đúng** (`primary_key`): khoá sai (thêm `updated_at`) cũng tạo bản trùng.
5. **Múi giờ**: `+07:00` → UTC đúng. So với một giá trị cụ thể, không chỉ "không NULL".
6. **Parse số theo locale**: `"1.290.000"` không phải 1,29.
7. **Retry** khi 429 / 5xx.
8. **Dữ liệu lồng**: bảng con (`orders__items`) đủ dòng và nối được về cha (`_dlt_parent_id` = `_dlt_id`).

Một test tốt **kiểm giá trị cụ thể đã biết trước** (120 đơn, đơn 5004 là `shipped`, 01:07 UTC). Test kiểu "bảng có > 0 dòng" gần như không giết được mutant nào.

## Mutation testing

**Code coverage** cho biết dòng code nào đã chạy qua khi test. **Mutation testing** cho biết test có **phát hiện** được khi dòng đó sai hay không:

1. Tạo "mutant": bản code cài đúng một lỗi nhỏ (đổi `merge` → `append`, bỏ một tham số...).
2. Chạy bộ test. Đỏ = mutant **bị giết** (tốt). Xanh = mutant **sống sót** (test chưa bảo vệ hành vi đó).
3. Điểm = % mutant bị giết.

Công cụ tự động cho Python: `mutmut`, `cosmic-ray` (sinh mutant theo luật cú pháp). Lab dùng **mutant viết tay** theo các lỗi hay gặp ngoài đời, nên ít mà có ý nghĩa hơn.

## dlt: những điểm cần biết khi test

- `pipeline.run(source)` trả `LoadInfo`. `pipeline.last_trace.last_normalize_info.row_counts` cho số dòng **lần chạy này** theo bảng.
- State của dlt (cursor `incremental`, schema) nằm ở `pipelines_dir` **và** trong bảng `_dlt_pipeline_state` ở đích. Test phải dùng thư mục tạm riêng (`pipelines_dir=tmp_path/...`), nếu không lần chạy test sau sẽ "nhớ" cursor của lần trước.
- Bảng hệ thống: `_dlt_loads`, `_dlt_version`, `_dlt_pipeline_state`. Cột `_dlt_id`, `_dlt_load_id` trên mọi dòng, `_dlt_parent_id` trên bảng con.
- `dlt.sources.helpers.requests`: `requests` có sẵn retry (429, 5xx, lỗi kết nối) và tôn trọng `Retry-After`.
- `max_table_nesting`: độ sâu lồng được tách thành bảng con; `0` = giữ JSON trong một cột.

## Đưa vào CI

```yaml
- uses: astral-sh/setup-uv@v6               # kiểm tra bản mới nhất trên Marketplace
- run: uv sync --frozen
- run: uv run pytest -q
- run: uv run python scripts/mutate.py      # tuỳ chọn: chạy hằng đêm vì chậm hơn
```

## Câu hỏi tự kiểm tra

1. Vì sao mutant P2 (quên gửi `updated_since`) sống sót qua test đếm dòng? Lỗi đó gây hại gì ngoài đời?
2. Fixture `api` có `scope="function"`. Đổi thành `"session"` thì test nào có thể hỏng, và vì sao?
3. Viết test cho tình huống API trả 500 hai lần rồi mới thành công.
4. Coverage 100% mà mutation score 40% nghĩa là gì?

## Tài liệu

- pytest docs: *How to use fixtures*, *Parametrizing tests*, *tmp_path*, *monkeypatch*
- dlt docs: *Incremental loading*, *Merge loading*, *Requests helper*, *Nested tables (max_table_nesting)*, *Pipeline state*
