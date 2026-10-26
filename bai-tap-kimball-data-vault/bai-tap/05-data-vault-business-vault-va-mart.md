# 05 — Data Vault: business vault, information mart và ADR (V7–V8)

> Lý thuyết: [6.4 business vault, PIT, bridge](../../GD2-ly-thuyet/tuan-6/04-business-vault-pit-bridge.md) · [6.5 information mart](../../GD2-ly-thuyet/tuan-6/05-information-mart-tu-vault.md) · [6.6 ADR, Data Vault vs Kimball](../../GD2-ly-thuyet/tuan-6/06-adr-data-vault-vs-kimball.md)

**Tình huống:** raw vault đã giữ đủ lịch sử. Nhưng BI không thể viết SQL join 10 bảng hub/link/satellite. Nhiệm vụ: (1) tăng tốc truy vấn lịch sử bằng PIT, (2) dựng lại star schema cho BI **từ vault**, (3) viết ADR đề xuất có nên dùng Data Vault cho `adventure_works` hay không.

---

## V7 ⭐⭐⭐ PIT: "sau lần nạp X, kho biết gì về khách?"

**Yêu cầu:**

`models/business_vault/as_of_date.sql`: các mốc as-of = **mỗi lần kho nạp** (06:00 hằng ngày). Một cột `AS_OF_DATE` (timestamp).

```sql
select distinct _loaded_at as AS_OF_DATE from {{ ref('stg_crm__customers') }}
```

`models/business_vault/pit_customer.sql`:

```sql
{{ config(materialized='pit_incremental') }}

{{ automate_dv.pit(src_pk='CUSTOMER_HK',
                   as_of_dates_table='as_of_date',
                   satellites={
                       'sat_customer_crm_profile': {'pk': {'PK': 'CUSTOMER_HK'}, 'ldts': {'LDTS': 'LOAD_DATETIME'}},
                       'sat_customer_crm_status':  {'pk': {'PK': 'CUSTOMER_HK'}, 'ldts': {'LDTS': 'LOAD_DATETIME'}}
                   },
                   stage_tables_ldts={'v_stg_crm__customers': 'LOAD_DATETIME'},
                   src_ldts='LOAD_DATETIME',
                   source_model='hub_customer') }}
```

Tên satellite trong `satellites` và `stage_tables_ldts` là tên **model** (viết thường), vì automate_dv dùng chúng trong `ref()`.

Xem PIT trông thế nào:

```bash
dbt show --inline "select * from {{ ref('pit_customer') }}" --limit 10
```

Mỗi dòng: 1 khách × 1 mốc, kèm cặp con trỏ `<satellite>_PK`, `<satellite>_LDTS` tới dòng satellite đang hiệu lực. Chưa có dòng nào → con trỏ trỏ vào **ghost record** (hash toàn số 0, ngày 1900-01-01).

`models/information_marts/customer_status_as_of.sql`: dùng PIT, **chỉ equi-join**, cột `customer_code, as_of_date, full_name, email, city, loyalty_tier`. Bỏ dòng của zero key `-2`.

```sql
from {{ ref('pit_customer') }} p
join {{ ref('hub_customer') }} h on h.CUSTOMER_HK = p.CUSTOMER_HK
left join {{ ref('sat_customer_crm_status') }} st
       on st.CUSTOMER_HK = p.sat_customer_crm_status_PK
      and st.LOAD_DATETIME = p.sat_customer_crm_status_LDTS
...
```

**Kiểm tra:** `./scripts/replay.sh` → `check.py V7`.

**Câu hỏi suy ngẫm**
1. Không có PIT, muốn có `customer_status_as_of` bạn phải join thế nào? Với 6 satellite thì sao?
2. PIT tính theo `LOAD_DATETIME` (giờ kho nạp). Khách đổi thành phố ngày 02/03 nhưng kho chỉ biết lúc 06:00 ngày 03/03. Báo cáo kiểm toán "kho biết gì lúc nào" dùng mốc nào? Báo cáo doanh thu theo thành phố lúc mua dùng mốc nào?
3. Vì sao C013 có dòng PIT ở mốc 02/03 dù khi đó vault chưa biết C013?

---

## V8 ⭐⭐⭐⭐ Information mart: dựng lại star schema từ vault

**Yêu cầu:** 2 model trong `models/information_marts/`, **chỉ đọc từ vault** (hub, link, satellite; được dùng lại macro và `dbt_utils`):

`dim_customer_dv`: **cùng cột, cùng quy tắc** với `dim_customer` (K4 + K6):
- Phiên bản theo **thời gian nghiệp vụ** `EFFECTIVE_FROM` của `sat_customer_crm_status` (không phải `LOAD_DATETIME`).
- Type 1 lấy từ dòng mới nhất của `sat_customer_crm_profile`.
- Inferred member = khách có trong `hub_customer` (trừ `-2`) mà satellite CRM chưa có dòng nào.
- Unknown member `'-1'`.

`fct_sales_dv`: **cùng cột, cùng quy tắc** với `fct_sales` (K5):
- Dòng đơn từ `nh_link_order_line` + `hub_order` + `hub_product`.
- Đầu đơn: dòng **mới nhất** của `sat_order_shop` (online) hoặc `sat_order_pos` (POS). Bỏ đơn có `order_status = 'cancelled'`.
- Khách: `link_order_customer` → `hub_customer`. Zero key `-2` = khách vãng lai.
- Giảm giá: tổng `discount_amount` của `nh_link_order_voucher`.
- Khoá: tính bằng **cùng công thức** `generate_surrogate_key` như các dimension Kimball.

**Kiểm tra:** `./scripts/replay.sh` → `check.py V8`. Thông báo PASS cho biết bản vault có **giống hệt** bản Kimball không (so bằng `except` từng dòng).

Tự so:

```bash
dbt show --inline "select * from {{ ref('fct_sales') }} except select * from {{ ref('fct_sales_dv') }}"
```

**Câu hỏi suy ngẫm**
1. Đếm số `join` trong `fct_sales_dv` và trong `fct_sales` + `int_sales__lines`. Chênh bao nhiêu?
2. Vì sao dùng `EFFECTIVE_FROM` mà không dùng `LOAD_DATETIME` cho `valid_from`? Dùng `LOAD_DATETIME` thì HN-0003 (K7) sẽ mang thành phố nào?
3. Inferred member ở đây "tự có" từ hub. So với cách bạn làm ở K6, cách nào ít lỗi hơn?
4. Information mart nên là `view` hay `table`? Trả lời cho 2 trường hợp: 50 nghìn dòng và 500 triệu dòng.

---

## ADR ⭐⭐⭐ Data Vault hay Kimball cho `adventure_works`? (không chấm, quan trọng nhất)

Mục tiêu: một **Architecture Decision Record** có số liệu thật, đặt ở `adventure_works/docs/adr/0001-data-vault-vs-kimball.md`. Mẫu và cách viết ở [lý thuyết 6.6](../../GD2-ly-thuyet/tuan-6/06-adr-data-vault-vs-kimball.md).

### Bước 1: đo trên lab (ghi kết quả vào bảng)

```bash
# số model mỗi cách
dbt ls -s marts intermediate --resource-type model --quiet | wc -l
dbt ls -s raw_vault business_vault information_marts --resource-type model --quiet | wc -l

# số dòng SQL
cat models/marts/sales/fct_sales.sql models/intermediate/int_sales__lines.sql | wc -l
cat models/information_marts/fct_sales_dv.sql | wc -l

# thời gian build (DuckDB rất nhanh, chỉ để so tương đối)
dbt build -s marts intermediate && python -c "import json;r=json.load(open('target/run_results.json'));print(round(sum(x['execution_time'] for x in r['results']),2),'s')"
dbt build -s raw_vault business_vault information_marts && python -c "import json;r=json.load(open('target/run_results.json'));print(round(sum(x['execution_time'] for x in r['results']),2),'s')"
```

### Bước 2: thí nghiệm "dựng lại từ đầu"

```bash
python scripts/simulate.py goto 6     # nhảy thẳng tới ngày 6, bỏ qua các ngày giữa
dbt build
python scripts/check.py
```

Bài K nào còn PASS? Bài V nào FAIL? Vì sao? (gợi ý: nguồn nào ghi đè?) Chạy lại `./scripts/replay.sh` để về trạng thái đúng.

<details><summary>Kết quả mong đợi</summary>

- **Mọi bài K vẫn PASS**: mọi model Kimball là `table` dựng lại từ nguồn mỗi lần chạy.
- **V2–V6 FAIL**: hub/link ghi nhận sai thời điểm "thấy lần đầu", satellite của đơn hàng và sản phẩm mất các trạng thái trung gian, link SKU07–DT_PK cũ không còn, tập số điện thoại cũ mất. Đó là các nguồn **ghi đè** (shop, ERP) hoặc stage chỉ đọc file mới nhất.
- **V7, V8 vẫn PASS**: phiên bản khách đến từ CRM, nguồn **giữ lịch sử**, và `apply_source_filter` xử lý được nhiều file một lúc. Còn `fct_sales_dv` chỉ cần trạng thái mới nhất của đơn.

Bài học cho ADR: khả năng "dựng lại" không phụ thuộc Kimball hay Data Vault, mà phụ thuộc **nguồn có giữ lịch sử không**. Vault giá trị nhất đúng ở chỗ nó chụp lại lịch sử của các nguồn ghi đè, với điều kiện chạy đều đặn.
</details>

### Bước 3: thí nghiệm "kiểm toán"

Kế toán hỏi: *"Đơn W0013 từng ở những trạng thái nào, kho biết lúc nào?"* Trả lời bằng 1 câu SQL trên vault. Kimball (`fct_order_fulfillment`) trả lời được tới đâu?

### Bước 4: thí nghiệm tư duy "thêm nguồn"

Công ty mua sàn TMĐT, khách có mã riêng (`TIKI_xxx`), đơn có trạng thái riêng. Liệt kê những model phải **sửa** và phải **thêm** ở mỗi cách.

### Bước 5: viết ADR

| Mục | Nội dung |
|---|---|
| Bối cảnh | adventure_works có bao nhiêu nguồn, team mấy người, yêu cầu kiểm toán thế nào |
| Các phương án | Kimball thuần · Data Vault + information mart · Lai: vault cho vài thực thể lõi |
| Bảng so sánh | dùng số đo bước 1–4 |
| Quyết định | 1 câu |
| Hệ quả | được gì, mất gì, khi nào xem lại quyết định |

**Ngoài thực tế:** phỏng vấn Mid/Senior rất hay hỏi *"Bạn chọn Data Vault hay Kimball, vì sao?"*. Câu trả lời mạnh nhất không phải "cái A tốt hơn", mà là "tôi đã đo cả hai trên cùng dữ liệu, với bối cảnh X thì tôi chọn Y vì số liệu Z, và tôi sẽ xem lại khi W xảy ra".

---

✅ Xong V7–V8 + ADR: `./scripts/replay.sh` → **21/21 PASS**. Sang [06-thu-thach-cuoi.md](06-thu-thach-cuoi.md).
